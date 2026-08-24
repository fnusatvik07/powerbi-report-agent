"""A Deep Agent that authors and publishes Power BI reports from natural language.

The agent is a `create_deep_agent` harness whose tools wrap the three deterministic steps
this package provides: generate PBIR/TMDL from a spec, validate it with the Microsoft CLI,
and publish it to the Power BI service with the Fabric CLI. The model plans the dashboard
(pages, visuals, sample data), calls generate, reads validation diagnostics, fixes its
spec, and publishes - the same author -> validate -> fix loop a human would run.
"""

import json
import os

from deepagents import create_deep_agent
from langchain.tools import tool

from . import config
from .generator import generate
from .models import Column, Measure, Model, Page, ReportSpec, Visual
from .publisher import publish
from .validator import validate


def _spec_from_dict(d: dict) -> ReportSpec:
    m = d["model"]
    model = Model(
        table=m["table"],
        columns=[Column(**c) for c in m["columns"]],
        rows=m["rows"],
        measures=[Measure(**mm) for mm in m.get("measures", [])],
    )
    pages = [
        Page(display_name=p["display_name"], visuals=[Visual(**v) for v in p["visuals"]])
        for p in d["pages"]
    ]
    return ReportSpec(name=d["name"], model=model, pages=pages,
                      base_theme=d.get("base_theme", "CY24SU10"))


@tool
def generate_report(spec_json: str) -> str:
    """Generate a PBIP project (PBIR report + TMDL semantic model) from a JSON spec.

    spec_json is a JSON string matching ReportSpec: {name, model:{table,columns,rows,measures},
    pages:[{display_name, visuals:[{vtype,x,y,width,height,roles,text,color,title}]}]}.
    Visual roles bind fields: a column is a string, a measure is {"measure":"<name>"}.
    Returns the path to the generated .pbip file.
    """
    spec = _spec_from_dict(json.loads(spec_json))
    out = os.path.join(config.output_dir(), spec.name)
    return generate(spec, out)


@tool
def validate_report(pbip_path: str) -> str:
    """Validate a generated .pbip with the Microsoft powerbi-report-author CLI.

    Returns a JSON string {result, errorCount, warningCount, messages}. Fix the spec and
    regenerate until result is 'succeeded' before publishing.
    """
    return json.dumps(validate(pbip_path))


@tool
def publish_report(project_dir: str, project_name: str, workspace: str = "") -> str:
    """Publish a validated project to the Power BI service (requires `fab auth login`).

    project_dir contains <project_name>.SemanticModel and .Report. workspace defaults to
    PBI_TARGET_WORKSPACE. Returns a JSON string {model_id, report_id, url}.
    """
    ws = workspace or config.default_workspace()
    return json.dumps(publish(project_dir, project_name, ws))


SYSTEM_PROMPT = """You are a Power BI report building agent. You turn a natural-language
request into a real, published Power BI dashboard.

Workflow for every request:
1. Design the dashboard: choose sample data, measures, pages, and a rich visual mix
   (title banner + textbox, several cardVisual KPIs, at least one slicer, a mix of
   clusteredBarChart / clusteredColumnChart / lineChart / donutChart, a pivotTable matrix,
   and a pageNavigator for multi-page reports).
2. Call generate_report with a complete JSON spec.
3. Call validate_report. If result is not 'succeeded', read the messages, fix the spec,
   and regenerate. Never publish an invalid report.
4. Only if the user asks to publish, call publish_report and return the report URL.

Keep layouts on a 1280x720 page and avoid overlapping visuals. Use real, plausible sample
data. Do not use em or en dashes in any text you write."""


def build_agent(model: str | None = None):
    """Create the report-building deep agent."""
    return create_deep_agent(
        name="powerbi-report-agent",
        model=model or config.model_name(),
        tools=[generate_report, validate_report, publish_report],
        system_prompt=SYSTEM_PROMPT,
    )
