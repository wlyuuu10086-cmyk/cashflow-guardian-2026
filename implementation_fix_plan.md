# Minimal Step 9 Fix (Safe Mode)

This plan implements the minimal fix required to make `agents-cli run` succeed without any structural or architectural changes, keeping the existing agent directory in the manifest and leaving the core FastAPI system and tests untouched.

## Proposed Changes

---

### Project Startup & Routing Fixes

#### [NEW] [sitecustomize.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/sitecustomize.py)
Create a Python startup script at the project root to:
1. Append the system Python packages path (`E:\lib\site-packages`) to `sys.path` to resolve missing dependencies (`pandas`, `numpy`, etc.) without altering the project's virtualenv configuration.
2. Monkeypatch `google.adk.cli.utils.agent_loader.AgentLoader` at startup to allow slash-containing names in validation and cleanly intercept/load the CLI entry agent when `src/cashflow_guardian/agent` is requested.

---

### CLI Agent Adapter

#### [NEW] [cli_entry.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/src/cashflow_guardian/agent/cli_entry.py)
A lightweight CLI adapter that:
- Imports the existing root agent factory.
- Binds a default read-only `SecurityContext` (using role `"system_agent"`).
- Exposes `root_agent` with model-safe tools enabled while ensuring no privileged tools (e.g. watchlist approvals/rejections) are exposed. All tool execution goes through `execute_tool_with_policy()`.

---

## Verification Plan

### Automated Tests
- Run `uv run pytest` to verify that all 142 existing tests pass successfully.

### Manual Verification
- Run the target CLI command to check for successful model response output:
  ```bash
  agents-cli run "Summarize CashFlow Guardian capabilities"
  ```
