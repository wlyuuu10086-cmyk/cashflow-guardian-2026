# Walkthrough - Agents CLI Adapter Implementation

We have successfully implemented a portable `agents_cli_agent` adapter package to enable running `agents-cli` queries securely and cleanly under local evaluation.

## Changes Made

### 1. Declared Dependencies
Added missing third-party packages to [pyproject.toml](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/pyproject.toml):
- `pandas`
- `numpy`
- `scikit-learn`
- `joblib`

And updated the lockfile via `uv lock` and synchronized the virtualenv using `uv pip install -e .`.

### 2. Configured Agents CLI Manifest
Updated [agents-cli-manifest.yaml](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/agents-cli-manifest.yaml) to point to the adapter package:
```yaml
agent_directory: agents_cli_agent
```

### 3. CLI Agent Adapter Package
Created the `agents_cli_agent` package:
- [__init__.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/agents_cli_agent/__init__.py): Explicitly exports `root_agent`.
- [agent.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/agents_cli_agent/agent.py): Instantiates `root_agent` with a fixed local-evaluation `SecurityContext` using the verified least-privileged role `"analyst"`.

### 4. Custom Unit Test Suite
Created [test_cli_adapter.py](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/tests/unit/agent/test_cli_adapter.py) to assert that:
- `root_agent` imports successfully.
- It contains only model-safe tools and lacks mutation/watchlist-decision tools.
- Its prompt/signatures prevent model control of role/permissions/approvals.
- All tool execution routes correctly through `execute_tool_with_policy()`.

---

## Verification Results

### 1. Focused & Full Test Suite
- **Focused Tests:** `uv run pytest tests/unit/agent/test_cli_adapter.py` passed (5/5).
- **Full Test Suite:** `uv run pytest` passed (147/147).

### 2. Dependency Check
- `uv pip check` passed successfully:
  ```
  Checked 63 packages in 8ms
  All installed packages are compatible
  ```

### 3. Agents CLI Info Discovery
- `agents-cli info` correctly recognized the package path:
  ```
  Project name:       cashflow-guardian
  Agent directory:    agents_cli_agent
  ```

### 4. CLI Execution: No-Tool Prompt
- Query: `agents-cli run "Summarize CashFlow Guardian capabilities"`
- Output: Successfully loaded the agent and returned a full text response outlining portfolio monitoring, risk assessment, simulation, and guardrails.

### 5. CLI Execution: Read-Only Tool Prompt
- Query: `agents-cli run "Show me the portfolio snapshot for 2025-06"`
- Output: Successfully called the `get_portfolio_snapshot` tool, evaluated and allowed the request via the policy engine under `"analyst"`, queried the local database, and formatted the results in a markdown table.

---

## Trace Generation & Validation

### 1. Prerequisite Handling
Since `agents-cli eval generate` checks Google Cloud credentials to support GCS dataset inputs/outputs (even when evaluating locally), we resolved this dependency by:
- Adding `google-cloud-vertexai` and `google-cloud-aiplatform[evaluation]` packages to the `eval` optional-dependencies group of [pyproject.toml](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/pyproject.toml).
- Creating a temporary mock Application Default Credentials (ADC) file during the CLI evaluation run to satisfy `google-auth` initialization checks, which succeeded and ran local inference via the configured `GEMINI_API_KEY`.

### 2. Trace Generation Command
Generated real populated traces for the two representative smoke cases:
```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="D:\5-Days-AI-Kaggle\Capstone\cashflow_guardian\dummy_credentials.json"; agents-cli eval generate --project dummy-project --dataset tests/eval/datasets/cashflow_guardian_smoke_dataset.json --output artifacts/step9/smoke_traces/
```
The CLI successfully generated:
- [step9_smoke_traces.json](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/artifacts/step9/smoke_traces/step9_smoke_traces.json)

### 3. Trace Validation
Validated the generated traces using the repository's verification script:
```powershell
uv run python tests/eval/check_step9_traces.py artifacts/step9/smoke_traces/step9_smoke_traces.json
```
- **Result:** **PASSED** (2 out of 2 cases checked successfully).
- **Details:** Checked model-safe tool calls (`get_portfolio_snapshot` was executed), verified no forbidden/privileged tools were called, and confirmed zero safety/policy violations or trace leaks. The output log is saved in [deterministic_trace_check.json](file:///d:/5-Days-AI-Kaggle/Capstone/cashflow_guardian/artifacts/step9/deterministic_trace_check.json).
