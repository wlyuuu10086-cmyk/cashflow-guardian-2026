# Standard Agents-CLI Adapter Package Fix

This plan implements a portable CLI adapter package (`agents_cli_agent/`) that imports and reuses the existing CashFlow Guardian agent factory, prompts, and policy enforcement, without any monkeypatching or global startup modifications.

## Proposed Changes

---

### Project Configuration & Dependencies

#### [MODIFY] [pyproject.toml](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/pyproject.toml)
Add the missing runtime packages genuinely imported by the source code:
- `pandas`
- `numpy`
- `scikit-learn`
- `joblib`

#### [MODIFY] [agents-cli-manifest.yaml](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/agents-cli-manifest.yaml)
Update the `agent_directory` configuration to point to the new adapter package:
```yaml
agent_directory: agents_cli_agent
```

---

### CLI Adapter Package

#### [NEW] [__init__.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/agents_cli_agent/__init__.py)
Expose the `root_agent` module so that the ADK `AgentLoader` can discover and load it cleanly under the package.

#### [NEW] [agent.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/agents_cli_agent/agent.py)
Construct and expose the `root_agent` bound to a fixed local-evaluation `SecurityContext` containing role `"system_agent"`. This allows model-safe tools (like `score_cashflow_risk` and `get_portfolio_snapshot`) to be executed, while keeping all privileged mutation tools (like watchlist approvals/rejections) completely hidden. All tool execution goes through `execute_tool_with_policy()`.

---

## Verification Plan

Verification will be performed in the following order:
1. **Import Test**: Verify that the adapter `root_agent` imports successfully from the command line:
   ```bash
   uv run python -c "from agents_cli_agent.agent import root_agent; print(root_agent)"
   ```
2. **Automated Tests**: Run the pytest suite to ensure no regressions:
   ```bash
   uv run pytest
   ```
3. **CLI Info**: Verify that the Agents CLI discovers the new agent path:
   ```bash
   agents-cli info
   ```
4. **CLI No-Tool Query**: Run a query that requires no tools:
   ```bash
   agents-cli run "Summarize CashFlow Guardian capabilities"
   ```
5. **CLI Read-Only Tool Query**: Run a query that exercises a read-only tool:
   ```bash
   agents-cli run "Show me the portfolio snapshot for 2026-03"
   ```
