"""Command line entrypoint.

  pbi-report-agent chat "Build a sales dashboard and publish it"   # natural-language agent
  pbi-report-agent build examples/cricket_spec.py                  # deterministic build+validate
  pbi-report-agent publish ./build/Cricket Cricket "My workspace.Personal"

The `chat` command needs a model API key in .env (see .env.example). `build` and `publish`
need only the Node/Fabric CLIs and, for publish, `fab auth login`.
"""

import argparse
import json
import sys

from . import config
from .publisher import publish
from .validator import validate


def _cmd_chat(args: argparse.Namespace) -> int:
    from .agent import build_agent

    agent = build_agent()
    cfg = {"configurable": {"thread_id": args.thread}}
    result = agent.invoke({"messages": [{"role": "user", "content": args.prompt}]}, config=cfg)
    print(result["messages"][-1].content)
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    res = validate(args.pbip)
    print(json.dumps(res, indent=2))
    return 0 if res["result"] in ("succeeded", "succeededWithWarnings") else 1


def _cmd_publish(args: argparse.Namespace) -> int:
    res = publish(args.project_dir, args.name, args.workspace or config.default_workspace())
    print(json.dumps(res, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pbi-report-agent")
    sub = parser.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("chat", help="natural-language agent (needs a model key)")
    c.add_argument("prompt")
    c.add_argument("--thread", default="cli-session")
    c.set_defaults(func=_cmd_chat)

    v = sub.add_parser("validate", help="validate a .pbip project")
    v.add_argument("pbip")
    v.set_defaults(func=_cmd_validate)

    p = sub.add_parser("publish", help="publish a project to the Power BI service")
    p.add_argument("project_dir")
    p.add_argument("name")
    p.add_argument("workspace", nargs="?", default="")
    p.set_defaults(func=_cmd_publish)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
