from __future__ import annotations

import os
from typing import Optional

import yaml
from google.adk.agents import Agent
from google.genai import types as genai_types

from cashflow_guardian.agent.prompts import ROOT_AGENT_INSTRUCTION
from cashflow_guardian.agent.tool_adapter import get_model_safe_tools
from cashflow_guardian.security.schemas import SecurityContext


def load_agent_config() -> dict:
    from cashflow_guardian.data_engine.connection import get_repo_root

    path = get_repo_root() / "config" / "agent.yaml"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def create_root_agent(security_context: Optional[SecurityContext] = None) -> Agent:
    config = load_agent_config()
    model_name = os.getenv("CASHFLOW_GUARDIAN_AGENT_MODEL") or config.get(
        "model_name", "gemini-flash-latest"
    )
    temperature = float(config.get("temperature", 0.1))
    max_output_tokens = int(config.get("max_output_tokens", 1024))

    tools = get_model_safe_tools(security_context) if security_context else []

    return Agent(
        name=config.get("root_agent_name", "cashflow_guardian_agent"),
        model=model_name,
        description="Explains policy-gated CashFlow Guardian deterministic analysis.",
        instruction=ROOT_AGENT_INSTRUCTION,
        tools=tools,
        generate_content_config=genai_types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        ),
    )


root_agent = create_root_agent()
