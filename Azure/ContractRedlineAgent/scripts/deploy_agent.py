"""Idempotent registration of the Foundry agent.

Reads `.env`, uploads the three Python code files via the OpenAI-compatible
files API, then creates or updates the agent via the Foundry Agents API
(``AIProjectClient.agents``).

Usage::

    pip install -r requirements.txt
    az login
    python scripts/deploy_agent.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import jsonref
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("deploy_agent")

ROOT = Path(__file__).resolve().parent.parent
CODE_FILES_DIR = ROOT / "agent" / "code_files"
INSTRUCTIONS_PATH = ROOT / "agent" / "instructions.md"
TOOLS_DIR = ROOT / "tools"


def _load_env() -> dict[str, str]:
    load_dotenv(ROOT / ".env")
    required = ["AZURE_AI_PROJECT_ENDPOINT", "FOUNDRY_AGENT_NAME", "FOUNDRY_MODEL_DEPLOYMENT"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        sys.exit(f"Missing required env vars: {', '.join(missing)}")
    return {k: os.environ[k] for k in required} | {
        "DOWNLOAD_LOGIC_APP_URL": os.getenv("DOWNLOAD_LOGIC_APP_URL", ""),
        "UPLOAD_LOGIC_APP_URL": os.getenv("UPLOAD_LOGIC_APP_URL", ""),
    }


def main() -> None:
    env = _load_env()

    try:
        from azure.ai.projects import AIProjectClient
        from azure.ai.projects.models import (
            PromptAgentDefinition,
        )
        from azure.identity import DefaultAzureCredential
    except ImportError:
        sys.exit(
            "azure-ai-projects>=2.0.0 is not installed. Run "
            "`pip install -r requirements.txt` and try again."
        )

    project_client = AIProjectClient(
        endpoint=env["AZURE_AI_PROJECT_ENDPOINT"],
        credential=DefaultAzureCredential(),
    )

    # 1. Upload code files via OpenAI-compatible files API.
    oai_client = project_client.get_openai_client()
    file_ids: list[str] = []
    for py in sorted(CODE_FILES_DIR.glob("*.py")):
        if py.name == "__init__.py":
            continue
        logger.info("Uploading code file: %s", py.name)
        with py.open("rb") as fh:
            uploaded = oai_client.files.create(file=fh, purpose="assistants")
            file_ids.append(uploaded.id)

    # 2. Build tool definitions (code interpreter + Logic App OpenAPI tools).
    instructions = INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    agent_name = env["FOUNDRY_AGENT_NAME"]
    model = env["FOUNDRY_MODEL_DEPLOYMENT"]

    tools: list[dict] = [{"type": "code_interpreter"}]

    for tool_name, env_key in [
        ("download_contract", "DOWNLOAD_LOGIC_APP_URL"),
        ("upload_redlined_contract", "UPLOAD_LOGIC_APP_URL"),
    ]:
        spec_path = TOOLS_DIR / f"{tool_name}.openapi.json"
        logic_app_url = env.get(env_key, "")
        if not logic_app_url:
            logger.warning(
                "Skipping %s tool — %s not set in .env", tool_name, env_key
            )
            continue
        spec = jsonref.loads(spec_path.read_text(encoding="utf-8"))
        spec["servers"] = [{"url": logic_app_url}]

        tools.append({
            "type": "openapi",
            "openapi": {
                "name": tool_name,
                "description": spec["info"]["description"],
                "spec": spec,
                "auth": {"type": "anonymous"},
            },
        })
        logger.info("Registered OpenAPI tool: %s", tool_name)

    # Build the agent definition, injecting tool_resources via dict key
    definition = PromptAgentDefinition(
        model=model,
        instructions=instructions,
        tools=tools,
    )
    definition["tool_resources"] = {
        "code_interpreter": {"file_ids": file_ids},
    }

    # 3. Create a new agent version (idempotent — always creates a new version).
    logger.info("Creating new version of agent %s", agent_name)
    agent = project_client.agents.create_version(
        agent_name=agent_name,
        definition=definition,
    )

    logger.info("Done. Agent: %s, version: %s", agent.name, agent.version)
    print(json.dumps(
        {"agentName": agent.name, "version": agent.version},
        indent=2, ensure_ascii=True,
    ))


if __name__ == "__main__":
    main()
