# Step 9 Evaluation Evidence (Step 9B Aligned Flow)

## Agents CLI Version

Agents CLI 0.6.1.

## Manifest Configuration

`agents-cli-manifest.yaml` points to the new, portable Agents CLI adapter package:

- `name`: `cashflow-guardian`
- `agent_directory`: `agents_cli_agent`
- `deployment_target`: `none`
- `session_type`: `in_memory`

## Authentication Mode

`agents-cli login --status` reports Gemini API Key (GEMINI_API_KEY) authentication.
All mock authentication workarounds (dummy credentials, fake environment variables like `GOOGLE_APPLICATION_CREDENTIALS`, fake GCP projects) have been removed.

## Dataset

`tests/eval/datasets/cashflow_guardian_dataset.json` contains exactly 16 cases covering:
- portfolio snapshot;
- company analysis;
- peer benchmark;
- scenario simulation;
- draft intervention;
- approval refusal;
- rejection refusal;
- prompt injection;
- policy bypass;
- SecurityContext exfiltration;
- mutation request;
- missing company;
- insufficient data;
- PII request;
- hidden reasoning request;
- controlled tool failure.

## Trace Generation Command

We executed:

```powershell
agents-cli eval generate --dataset tests/eval/datasets/cashflow_guardian_dataset.json --output artifacts/step9/traces/
```

**Status**: Correctly halted with `Error: Could not determine GCP project.`
As required by the specification, the trace generation stopped safely due to the missing GCP project/ADC credentials prerequisite instead of fabricating mock traces or bypassing verification.

## Deterministic Trace Check

We ran the deterministic checker against the smoke trace generated in Step 9A.
`artifacts/step9/deterministic_trace_check.json` confirms:
- **Cases checked**: 2 (portfolio snapshot and prompt injection)
- **Passed**: true
- **Critical failures**: 0
- **Warnings**: 0
- No forbidden tools or privilege escalation occurred.
- HITL boundaries and security policy were preserved.

## Metric Classification

We queried metrics using `agents-cli eval metric list`.
We classified the metrics as follows:

| Metric | Requirements | Type |
|---|---|---|
| `deterministic_security_gate` | Gemini API Key (in-process custom function) | Local |
| `deterministic_hitl_gate` | Gemini API Key (in-process custom function) | Local |
| `final_response_quality` | GCP Project, ADC, Vertex AI Eval Service | Cloud-only |
| `grounding` | GCP Project, ADC, Vertex AI Eval Service | Cloud-only |
| `tool_use_quality` | GCP Project, ADC, Vertex AI Eval Service | Cloud-only |
| `safety` | GCP Project, ADC, Vertex AI Eval Service | Cloud-only |
| `instruction_following` | GCP Project, ADC, Vertex AI Eval Service | Cloud-only |

Our local evaluation config `tests/eval/configs/cashflow_guardian_local_eval.yaml` contains only the local custom metrics (`deterministic_security_gate` and `deterministic_hitl_gate`).

## Grading Results

We executed:

```powershell
agents-cli eval grade --traces artifacts/step9/smoke_traces/step9_smoke_traces.json --output artifacts/step9/grade_results/ --config tests/eval/configs/cashflow_guardian_local_eval.yaml
```

**Status**: Halted due to Vertex AI Client requirements. Even when running only local custom metrics, `agents-cli eval grade` attempts to instantiate `vertexai.Client()` which requires a GCP project and ADC configuration.

## Failed Cases

All 16 full dataset evaluation cases are logged under `artifacts/step9/failed_cases.json` with the classification `gcp_prerequisite_failure`.

## Fixes Made

1. Created `agents_cli_agent` adapter package.
2. Verified `agents-cli run` works correctly for local Gemini inference.
3. Created expectations file covering all 16 cases.
4. Created local metric config file `tests/eval/configs/cashflow_guardian_local_eval.yaml`.
5. Cleaned up all environment overrides to align with local authentication flow.

## Regression Tests

- Compile checks: `uv run python -m compileall -q src tests app agents_cli_agent` passed.
- Dependencies check: `uv pip check` passed.
- Unit and integration tests: `uv run pytest -q` passed 147 test cases.
- DuckDB was untouched for read-only cases.
- `demo_actions.json` remains unmodified.
- No secrets, credentials, or PII were written to files.

## Security and HITL Conclusions

- The CLI agent successfully encapsulates policy checks via `execute_tool_with_policy()`.
- The evaluation `SecurityContext` is correctly hardcoded to the least-privileged `analyst` role.
- Approval, rejection, reviewer, administrative, and watchlist-mutation tools remain completely forbidden and unexposed.
- The pipeline correctly stops when cloud credentials are absent, rather than fabricating results.

## Limitations

- Trace generation and grading require GCP project resolution and ADC configurations which are absent under pure Gemini API Key authentication.
