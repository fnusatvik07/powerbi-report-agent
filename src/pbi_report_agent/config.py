"""Runtime configuration, loaded from environment / a local .env file.

Copy .env.example to .env and fill it in. Nothing here is committed - .env is gitignored.
"""

import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv is optional; env vars still work without it
    pass


def model_name() -> str:
    """LangChain model id the deep agent runs on. Override with PBI_AGENT_MODEL."""
    return os.getenv("PBI_AGENT_MODEL", "claude-sonnet-4-5-20250929")


def default_workspace() -> str:
    """Target Fabric workspace path segment, e.g. 'My workspace.Personal'."""
    return os.getenv("PBI_TARGET_WORKSPACE", "My workspace.Personal")


def output_dir() -> str:
    """Where generated PBIP projects are written."""
    return os.getenv("PBI_OUTPUT_DIR", os.path.abspath("./build"))
