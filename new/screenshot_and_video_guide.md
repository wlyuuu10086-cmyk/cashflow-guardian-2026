# Screenshot and Video Recording Guide

## Screenshot: What to Capture

### 1. Main Architecture / Mind Map

Capture:

- `new/index.html`

How:

1. Open `D:\5-Days-AI-Kaggle\Capstone\new\index.html` in a browser.
2. Set browser zoom around 90-100% on a 1920x1080 screen.
3. Screenshot the title and the first grey "Executive Mind Map" panel.
4. Take a second screenshot of the "Runtime Architecture Flow" panel if the full flow is too tall.

Do not screenshot the old Mermaid diagram for the primary submission visual.

### 2. FastAPI Endpoint

Capture:

- `cashflow_guardian/app/adk_app.py`

Show:

- `@app.get("/health")`
- `@app.post("/apps/cashflow_guardian/trigger/pubsub")`
- `run_ambient_event(...)`

Why:

- This proves the project has an executable local service, not only a static diagram.

### 3. Event Routing and Trusted Context

Capture:

- `cashflow_guardian/src/cashflow_guardian/agent/ambient.py`

Show:

- `FORBIDDEN_PAYLOAD_FIELDS`
- `bind_trusted_security_context(...)`
- `_operation_plan(...)`

Why:

- This proves requests cannot set their own role, approval flag, or privileged tool name.

### 4. Policy-Gated Tool Executor

Capture:

- `cashflow_guardian/src/cashflow_guardian/tools/registry.py`

Show:

- `APPROVED_TOOL_NAMES`
- `execute_tool_with_policy(...)`
- trace/audit creation
- policy decision handling

Why:

- This is the central control point of the system.

### 5. RBAC / HITL Policy

Capture:

- `cashflow_guardian/src/cashflow_guardian/policy/engine.py`

Show:

- `evaluate_tool_request(...)`
- role permission check
- human approval check

Why:

- This proves model-safe tools and privileged tools are separated.

### 6. Terminal Evidence

Capture terminal outputs for:

- `uv run python -m uvicorn app.adk_app:app --host 0.0.0.0 --port 8080`
- `/health` response
- `portfolio_snapshot` event response
- `prompt_injection_block` response
- `draft_intervention` response
- test summary or validation report showing passing tests

Crop tightly so API keys, local usernames, and long absolute paths are not visible.

## Video: 3-4 Minute Recording Plan

### Before Recording

1. Open browser tab: `new/index.html`.
2. Open VS Code tabs:
   - `cashflow_guardian/app/adk_app.py`
   - `cashflow_guardian/src/cashflow_guardian/agent/ambient.py`
   - `cashflow_guardian/src/cashflow_guardian/tools/registry.py`
   - `cashflow_guardian/src/cashflow_guardian/policy/engine.py`
3. Run from repository root:

```powershell
python new\demo_payloads.py
```

4. Start the API from `cashflow_guardian/`:

```powershell
uv run python -m uvicorn app.adk_app:app --host 0.0.0.0 --port 8080
```

If `8080` is already occupied, use `--port 8090` and replace `8080` with `8090` in the curl commands below.

### Recording Timeline

#### 0:00-0:25 - Title and Problem

Screen:

- Show `new/index.html` title and "Executive Mind Map".

Narration:

> CashFlow Guardian is a secure SME cash-flow early-warning system. The key design is separation of concerns: deterministic engines calculate financial facts, while Google ADK only explains and routes approved outputs.

#### 0:25-0:55 - Architecture Flow

Screen:

- Scroll to "Runtime Architecture Flow".

Narration:

> A user or Pub/Sub-style event enters FastAPI. The server validates the event, binds a trusted SecurityContext, screens for prompt injection and PII, then routes all tool calls through execute_tool_with_policy.

#### 0:55-1:25 - Code Proof: API and Routing

Screen:

- Show `app/adk_app.py`, then `agent/ambient.py`.

Narration:

> The API exposes health and event-trigger endpoints. In ambient.py, the request cannot provide privileged fields like role, approval status, or tool name. The operation planner maps event types to model-safe deterministic tools.

#### 1:25-1:55 - Code Proof: Policy Gate

Screen:

- Show `tools/registry.py`, then `policy/engine.py`.

Narration:

> Every tool call passes through execute_tool_with_policy. The policy engine checks registry membership, role permissions, scope, prohibited actions, and human approval requirements before any engine executes.

#### 1:55-2:30 - Live Demo: Health and Portfolio

Screen:

- Terminal with:

```powershell
curl.exe -s http://127.0.0.1:8080/health
curl.exe -s -X POST http://127.0.0.1:8080/portfolio_snapshot -H "Content-Type: application/json" --data-binary "@new\curl_payloads\portfolio_snapshot.json"
```

Narration:

> The service is running locally, and the portfolio endpoint returns a compact SME risk snapshot for terminal evidence.

#### 2:30-3:05 - Live Demo: Scenario or Company Analysis

Screen:

- Run:

```powershell
curl.exe -s -X POST http://127.0.0.1:8080/draft_intervention -H "Content-Type: application/json" --data-binary "@new\curl_payloads\draft_intervention.json"
```

Narration:

> The draft intervention endpoint calls existing financial recommendation logic and returns actions that are safe to show in a terminal.

#### 3:05-3:35 - Live Demo: Security Boundary

Screen:

- Run:

```powershell
curl.exe -s -X POST http://127.0.0.1:8080/prompt_injection_block -H "Content-Type: application/json" --data-binary "@new\curl_payloads\prompt_injection_block.json"
```

Narration:

> Prompt injection is blocked before tool execution. This demonstrates that the agent layer is not trusted blindly.

#### 3:35-4:00 - Wrap-Up

Screen:

- Show validation report or test summary:
  - `cashflow_guardian/docs/final_project_status.md`
  - `cashflow_guardian/artifacts/business_engines_validation.md`

Narration:

> The project is backed by tests, immutable database checks, audit traces, and HITL boundaries. The core claim is secure, policy-gated financial intelligence rather than unrestricted LLM automation.

## Recording Tips

- Use 1920x1080 resolution.
- Hide browser bookmarks, API keys, `.env` files, and local user folders.
- Keep terminal font at 14-16 px.
- Use one command per shot so outputs remain readable.
- If a command output is too long, collapse or crop to show `status`, `answer`, `warnings`, `trace_id`, and `audit_event_ids`.
