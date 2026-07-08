# Step 8 Local Runtime Acceptance

Date: 2026-07-03T11:28:07.736119Z
Environment: local Windows PowerShell, Python 3.10, google-adk 2.3.0.

## Server

Command: `python -m uvicorn app.adk_app:app --host 127.0.0.1 --port 8080`

Endpoints:
- `GET /health`
- `POST /apps/cashflow_guardian/trigger/pubsub`

## Supported Event Types

- `portfolio_snapshot`
- `analyze_company`
- `benchmark_company`
- `simulate_scenario`
- `draft_intervention`

## Model-Safe Tools

check_business_data_quality, get_portfolio_snapshot, get_business_history, score_cashflow_risk, compare_with_peers, simulate_cashflow_scenario, draft_intervention_plan

Approval, rejection, direct mutation, and tools accepting trusted identity fields are not model exposed.

## Test Matrix

| Scenario | HTTP | Event | Tools | Model | HITL | Trace | Result |
|---|---:|---|---|---|---|---|---|
| valid_portfolio | 200 | portfolio_snapshot | get_portfolio_snapshot | False | not_applicable | trace_step8-valid-1 | success |
| valid_analyze_company | 200 | analyze_company | check_business_data_quality, compare_with_peers, draft_intervention_plan, get_business_history, score_cashflow_risk | False | draft_only | trace_step8-valid-2 | success |
| valid_benchmark | 200 | benchmark_company | compare_with_peers | False | not_applicable | trace_step8-valid-3 | success |
| valid_scenario | 200 | simulate_scenario | score_cashflow_risk, simulate_cashflow_scenario | False | not_applicable | trace_step8-valid-4 | success |
| valid_draft_intervention | 200 | draft_intervention | draft_intervention_plan, score_cashflow_risk | False | draft_only | trace_step8-valid-5 | success |
| prompt_injection | 200 | portfolio_snapshot |  | False | not_applicable | trace_step8-injection | blocked |
| pii_redaction | 200 | portfolio_snapshot | get_portfolio_snapshot | False | not_applicable | trace_step8-pii | success |
| privilege_role | 400 | portfolio_snapshot |  | False | not_applicable |  | error (PRIVILEGED_FIELD_REJECTED) |
| privilege_permissions | 400 | portfolio_snapshot |  | False | not_applicable |  | error (PRIVILEGED_FIELD_REJECTED) |
| privilege_security_context | 400 | portfolio_snapshot |  | False | not_applicable |  | error (PRIVILEGED_FIELD_REJECTED) |
| privilege_approved | 400 | portfolio_snapshot |  | False | not_applicable |  | error (PRIVILEGED_FIELD_REJECTED) |
| privilege_approval_status | 400 | portfolio_snapshot |  | False | not_applicable |  | error (PRIVILEGED_FIELD_REJECTED) |
| privilege_reviewer_id | 400 | portfolio_snapshot |  | False | not_applicable |  | error (PRIVILEGED_FIELD_REJECTED) |
| privilege_tool_name | 400 | portfolio_snapshot |  | False | not_applicable |  | error (PRIVILEGED_FIELD_REJECTED) |
| session_a_001 | 200 | portfolio_snapshot | get_portfolio_snapshot | False | not_applicable | trace_session-a-001 | success |
| session_b_001 | 200 | portfolio_snapshot | get_portfolio_snapshot | False | not_applicable | trace_session-b-001 | success |
| session_a_002 | 200 | portfolio_snapshot | get_portfolio_snapshot | False | not_applicable | trace_session-a-002 | success |
| missing_message | 400 |  |  | False | not_applicable |  | error (INVALID_PUBSUB_ENVELOPE) |
| missing_data | 400 |  |  | False | not_applicable |  | error (INVALID_PUBSUB_ENVELOPE) |
| null_data | 400 |  |  | False | not_applicable |  | error (INVALID_PUBSUB_ENVELOPE) |
| invalid_base64 | 400 |  |  | False | not_applicable |  | error (INVALID_BASE64) |
| invalid_utf8 | 400 |  |  | False | not_applicable |  | error (INVALID_UTF8) |
| invalid_json | 400 |  |  | False | not_applicable |  | error (INVALID_JSON) |
| unsupported_event_type | 400 |  |  | False | not_applicable |  | error (INVALID_EVENT) |
| invalid_business_id | 400 |  |  | False | not_applicable |  | error (INVALID_EVENT) |
| unexpected_extra_field | 400 |  |  | False | not_applicable |  | error (INVALID_EVENT) |
| oversized_payload | 413 |  |  | False | not_applicable |  | error (PAYLOAD_TOO_LARGE) |

## Security Results

- Prompt-injection request was blocked before deterministic tool execution.
- Full malicious test text absent from sanitized artifacts: `True`.
- Raw synthetic PII absent from sanitized artifacts and trace dump: `True`.
- Privilege-escalation fields were rejected by schema/field checks.

## HITL Boundary

Draft intervention remained draft-only. The ambient endpoint rejected fake approval fields and did not expose approval or rejection operations.

## Session Isolation

- `session_a_001` normalized source `company-a-events`, session `ambient-company-a-events-session-a-001`, trace `trace_session-a-001`.
- `session_b_001` normalized source `company-b-events`, session `ambient-company-b-events-session-b-001`, trace `trace_session-b-001`.
- `session_a_002` normalized source `company-a-events`, session `ambient-company-a-events-session-a-002`, trace `trace_session-a-002`.

## Database and File Integrity

- DuckDB unchanged: `True`.
- demo_actions.json unchanged: `True`.
- DuckDB before/after: `{'size': 17313792, 'mtime': 1783066679.5767782}` / `{'size': 17313792, 'mtime': 1783066679.5767782}`.
- demo_actions before/after: `{'size': 3029, 'mtime': 1783076025.2022989}` / `{'size': 3029, 'mtime': 1783076025.2022989}`.

## Audit and Trace

- Trace records captured in memory for 10 accepted requests.
- Audit JSONL files were written under `artifacts/step8/audit/`.
- Records were inspected for raw payload bodies, raw synthetic PII, credentials, and full malicious text.

## Gemini Usage

Gemini live-model mode was not used. Deterministic runtime acceptance succeeded without a live model call.

## Reproduction Commands

```powershell
python -m compileall -q src tests app
python -m pip check
python -m pytest -q
python scripts\step8_local_acceptance.py
```

## Screenshot Checklist

1. Terminal showing server startup.
2. Health response.
3. Successful portfolio or company analysis response.
4. Prompt-injection blocked result.
5. PII redaction summary without raw PII.
6. Draft intervention result marked draft/human-review-required.
7. Full test suite passing.
8. Safe audit or trace stage summary.

## Known Limitations

- No live Gemini call was performed.
- No Google Cloud, Cloud Run, real Pub/Sub topic, or Agent Runtime deployment was tested.
- Trace store is in-memory for the local process.
