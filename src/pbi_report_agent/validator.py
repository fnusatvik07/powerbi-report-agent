"""Validate a generated PBIP project with Microsoft's `powerbi-report-author` CLI.

The CLI runs on any platform with Node 20+ and needs no Power BI Desktop. It checks the
PBIR JSON against the official schema and returns structured diagnostics, which is what
makes the author -> validate -> fix loop deterministic.
"""

import json
import shutil
import subprocess


class ValidatorNotInstalled(RuntimeError):
    pass


def _cli() -> str:
    path = shutil.which("powerbi-report-author")
    if not path:
        raise ValidatorNotInstalled(
            "powerbi-report-author not found. Install with: "
            "npm install -g @microsoft/powerbi-report-authoring-cli@latest"
        )
    return path


def validate(pbip_path: str) -> dict:
    """Run validation and return {result, errorCount, warningCount, messages}.

    `result` is one of "succeeded", "succeededWithWarnings", "failed".
    """
    out = subprocess.run(
        [_cli(), "validate", pbip_path],
        capture_output=True,
        text=True,
    )
    try:
        data = json.loads(out.stdout)["data"]
    except (json.JSONDecodeError, KeyError):
        return {"result": "failed", "errorCount": -1, "warningCount": 0,
                "messages": [out.stdout or out.stderr]}
    messages = [
        item["message"]
        for diag in data.get("diagnostics", {}).values()
        for item in diag.get("items", [])
    ]
    return {
        "result": data.get("result"),
        "errorCount": data.get("errorCount", 0),
        "warningCount": data.get("warningCount", 0),
        "messages": messages,
    }
