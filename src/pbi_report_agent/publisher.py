"""Publish a validated PBIP project to the Power BI service via the Fabric CLI (`fab`).

Auth is delegated to `fab auth login` (interactive browser / device code), so no client
secret lives in this repo. The publish sequence, learned the hard way against the live
service:

1. Import the semantic model first (`fab import ... .SemanticModel`).
2. Read back the deployed model id.
3. Rewrite the report's definition.pbir to bind `byConnection` using that id. The service
   REJECTS a report whose binding is still `byPath`, and the byConnection block accepts
   ONLY a `connectionString` string ("semanticmodelid=<id>") - nothing else.
4. Import the report.
5. Trigger a dataset refresh so the inline sample data actually loads (an unrefreshed
   model renders an empty report - the single most common "it's blank" cause).
"""

import json
import os
import shutil
import subprocess


class FabNotInstalled(RuntimeError):
    pass


def _fab() -> str:
    path = shutil.which("fab")
    if not path:
        raise FabNotInstalled(
            "Fabric CLI not found. Install with: pip install ms-fabric-cli, "
            "then run: fab auth login"
        )
    return path


def _run(*args: str, body: str | None = None) -> subprocess.CompletedProcess:
    cmd = [_fab(), *args]
    if body is not None:
        cmd += ["-i", body]
    return subprocess.run(cmd, capture_output=True, text=True)


def is_logged_in() -> bool:
    out = _run("auth", "status")
    return "Logged In: True" in out.stdout


def _item_id(workspace: str, item: str) -> str:
    out = _run("get", f"/{workspace}/{item}", "-q", "id")
    return out.stdout.strip().strip('"').splitlines()[-1]


def _rebind_to_connection(report_dir: str, model_id: str) -> None:
    pbir = os.path.join(report_dir, "definition.pbir")
    json.dump(
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
            "version": "4.0",
            "datasetReference": {"byConnection": {"connectionString": f"semanticmodelid={model_id}"}},
        },
        open(pbir, "w"),
        indent=2,
    )


def publish(project_dir: str, project_name: str, workspace: str, refresh: bool = True) -> dict:
    """Publish `<project_dir>/<name>.SemanticModel` + `.Report` into `workspace`.

    `workspace` is a fab path segment such as "My workspace.Personal" or "Team X.Workspace".
    Returns {model_id, report_id} on success.
    """
    if not is_logged_in():
        raise RuntimeError("Not logged in. Run: fab auth login")

    sm_dir = os.path.join(project_dir, f"{project_name}.SemanticModel")
    rp_dir = os.path.join(project_dir, f"{project_name}.Report")

    m = _run("import", f"/{workspace}/{project_name}.SemanticModel", "-i", sm_dir, "-f")
    if "imported" not in m.stdout:
        raise RuntimeError(f"model import failed: {m.stdout or m.stderr}")

    model_id = _item_id(workspace, f"{project_name}.SemanticModel")
    _rebind_to_connection(rp_dir, model_id)

    r = _run("import", f"/{workspace}/{project_name}.Report", "-i", rp_dir, "-f")
    if "imported" not in r.stdout:
        raise RuntimeError(f"report import failed: {r.stdout or r.stderr}")

    report_id = _item_id(workspace, f"{project_name}.Report")

    if refresh:
        _run("api", "-A", "powerbi", "-X", "post",
             f"datasets/{model_id}/refreshes", body='{"notifyOption":"NoNotification"}')

    return {"model_id": model_id, "report_id": report_id,
            "url": f"https://app.powerbi.com/groups/me/reports/{report_id}"}
