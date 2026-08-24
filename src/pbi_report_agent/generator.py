"""Turn a `ReportSpec` into an on-disk PBIP project (PBIR report + TMDL semantic model).

The exact file shapes here were reverse-engineered and proven against the Microsoft
`powerbi-report-author validate` CLI and a live `fab import` to the Power BI service
(see docs/architecture.md). Every schema URL / version constant below is load-bearing.
"""

import json
import os
import secrets
import shutil
import uuid

from .models import Measure, Model, ReportSpec, Visual

_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
_VC_SCHEMA = f"{_SCHEMA}/visualContainer/2.9.0/schema.json"

# M data types for the inline #table type declaration, keyed by our column dtype.
_M_TYPE = {"text": "text", "int64": "Int64.Type", "double": "number"}


def _w(path: str, obj: object) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)


def _vid() -> str:
    return secrets.token_hex(10)


def _pid() -> str:
    return "ReportSection" + secrets.token_hex(12)


def _lit(v: str) -> dict:
    return {"expr": {"Literal": {"Value": v}}}


def _field(entity: str, ref: object) -> dict:
    """A column ref (str) or measure ref ({"measure": name}) -> PBIR field expression."""
    if isinstance(ref, dict) and "measure" in ref:
        prop = ref["measure"]
        return {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}, prop
    prop = str(ref)
    return {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}, prop


def _projection(entity: str, ref: object) -> dict:
    fld, prop = _field(entity, ref)
    return {"field": fld, "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop}


# ----------------------------- semantic model (TMDL) -----------------------------

def _write_model(sm_dir: str, model: Model) -> None:
    _w(
        os.path.join(sm_dir, ".platform"),
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": "SemanticModel", "displayName": model.table},
            "config": {"version": "2.0", "logicalId": str(uuid.uuid4())},
        },
    )
    _w(
        os.path.join(sm_dir, "definition.pbism"),
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
            "version": "4.2",
            "settings": {"qnaEnabled": True},
        },
    )
    defn = os.path.join(sm_dir, "definition")
    # database.tmdl MUST start with a `database <id>` declaration, not a bare property.
    _write_text(
        os.path.join(defn, "database.tmdl"),
        f"database {uuid.uuid4()}\n\tcompatibilityLevel: 1702\n\tcompatibilityMode: powerBI\n\tlanguage: 1033\n",
    )
    # powerBI_V3 is REQUIRED for import-mode, else the service rejects with "V3 models only".
    _write_text(
        os.path.join(defn, "model.tmdl"),
        "model Model\n\tculture: en-US\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
        f"\tsourceQueryCulture: en-US\n\nref table {model.table}\n",
    )
    _write_text(os.path.join(defn, "tables", f"{model.table}.tmdl"), _table_tmdl(model))


def _table_tmdl(model: Model) -> str:
    lines = [f"table {model.table}", ""]
    for m in model.measures:
        lines += [f"\tmeasure '{m.name}' = {m.dax}", f"\t\tformatString: {m.format_string}", ""]
    for c in model.columns:
        lines += [
            f"\tcolumn {c.name}",
            f"\t\tdataType: {c.dtype}",
            f"\t\tsummarizeBy: {c.summarize_by}",
            f"\t\tsourceColumn: {c.name}",
            "",
        ]
    type_decl = ", ".join(f"{c.name} = {_M_TYPE[c.dtype]}" for c in model.columns)
    row_lines = ",\n".join("\t\t\t\t\t\t{" + ", ".join(_m_value(v) for v in row) + "}" for row in model.rows)
    lines += [
        f"\tpartition {model.table} = m",
        "\t\tmode: import",
        "\t\tsource =",
        "\t\t\tlet",
        f"\t\t\t    Source = #table(",
        f"\t\t\t        type table [{type_decl}],",
        "\t\t\t        {",
        row_lines,
        "\t\t\t        }",
        "\t\t\t    )",
        "\t\t\tin",
        "\t\t\t    Source",
    ]
    return "\n".join(lines) + "\n"


def _m_value(v: object) -> str:
    if isinstance(v, str):
        return '"' + v.replace('"', '""') + '"'
    return str(v)


def _write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


# ----------------------------- report (PBIR) -----------------------------

def _visual_json(entity: str, v: Visual) -> dict:
    name = _vid()
    vis: dict = {"visualType": v.vtype}

    if v.vtype == "textbox":
        vis["objects"] = {
            "general": [
                {"properties": {"paragraphs": [
                    {"textRuns": [{"value": v.text, "textStyle": {
                        "fontSize": "20pt", "fontWeight": "bold",
                        "color": v.color or "'#FFFFFF'"}}]}]}}
            ]
        }
    elif v.vtype == "shape":
        vis["objects"] = {
            "shape": [{"properties": {"tileShape": _lit("'rectangle'")}}],
            "fill": [{"properties": {"show": _lit("true"),
                      "fillColor": {"solid": {"color": _lit(f"'{v.color or '#0B2545'}'")}}}}],
        }
    elif v.vtype == "pageNavigator":
        pass  # no query, no objects needed
    elif v.roles:
        qstate: dict = {}
        for role, refs in v.roles.items():
            qstate[role] = {"projections": [_projection(entity, r) for r in refs]}
        vis["query"] = {"queryState": qstate}
        if v.vtype == "slicer":
            vis["objects"] = {
                "data": [{"properties": {"mode": _lit("'Dropdown'")}}],
                "header": [{"properties": {"show": _lit("true"),
                            "text": _lit(f"'{v.title or role}'")}}],
            }
        if v.vtype == "cardVisual" and v.color:
            vis["objects"] = {"accentBar": [{"properties": {"show": _lit("true"),
                              "color": {"solid": {"color": _lit(f"'{v.color}'")}}},
                              "selector": {"id": "default"}}]}

    z = 0 if v.vtype == "shape" else 1
    return {
        "$schema": _VC_SCHEMA,
        "name": name,
        "position": {"x": v.x, "y": v.y, "z": z, "height": v.height, "width": v.width, "tabOrder": z},
        "visual": vis,
    }


def generate(spec: ReportSpec, out_dir: str) -> str:
    """Write the full PBIP project to `out_dir` and return the .pbip path."""
    root = os.path.join(out_dir, spec.name)
    sm_dir = f"{root}.SemanticModel"
    rp_dir = f"{root}.Report"
    if os.path.exists(out_dir):
        for d in (sm_dir, rp_dir):
            if os.path.isdir(d):
                shutil.rmtree(d)
    os.makedirs(out_dir, exist_ok=True)

    _write_model(sm_dir, spec.model)

    page_ids = []
    for page in spec.pages:
        pid = _pid()
        page_ids.append(pid)
        pdir = os.path.join(rp_dir, "definition", "pages", pid)
        for v in page.visuals:
            vj = _visual_json(spec.model.table, v)
            _w(os.path.join(pdir, "visuals", vj["name"], "visual.json"), vj)
        _w(os.path.join(pdir, "page.json"), {
            "$schema": f"{_SCHEMA}/page/2.1.0/schema.json",
            "name": pid, "displayName": page.display_name,
            "displayOption": "FitToPage", "height": 720, "width": 1280,
        })

    _w(os.path.join(rp_dir, "definition", "pages", "pages.json"), {
        "$schema": f"{_SCHEMA}/pagesMetadata/1.0.0/schema.json",
        "pageOrder": page_ids, "activePageName": page_ids[0],
    })
    _w(os.path.join(rp_dir, "definition", "report.json"), {
        "$schema": f"{_SCHEMA}/report/2.0.0/schema.json",
        "themeCollection": {"baseTheme": {
            "name": spec.base_theme, "type": "SharedResources", "reportVersionAtImport": "5.55"}},
    })
    _w(os.path.join(rp_dir, "definition", "version.json"), {
        "$schema": f"{_SCHEMA}/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})
    # byPath binding for local Desktop; the publisher rewrites this to byConnection on import.
    _w(os.path.join(rp_dir, "definition.pbir"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0",
        "datasetReference": {"byPath": {"path": f"../{spec.name}.SemanticModel"}},
    })
    _w(os.path.join(rp_dir, ".platform"), {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": spec.name},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid4())},
    })
    pbip = os.path.join(out_dir, f"{spec.name}.pbip")
    _w(pbip, {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/pbip/definitionProperties/1.0.0/schema.json",
        "version": "1.0",
        "artifacts": [{"report": {"path": f"{spec.name}.Report"}}],
        "settings": {"enableAutoRecovery": True},
    })
    return pbip
