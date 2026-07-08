# Necessary Code and Demo Commands

Use these snippets in the Kaggle write-up, a demo notebook, or the local screen recording.

## 1. Start the Local API

Run from `cashflow_guardian/`:

```powershell
uv run python -m uvicorn app.adk_app:app --host 0.0.0.0 --port 8080
```

If port `8080` is already occupied, use:

```powershell
uv run python -m uvicorn app.adk_app:app --host 127.0.0.1 --port 8090
```

## 2. Health Check

Run from `cashflow_guardian/` in a second terminal:

```powershell
curl.exe -s http://127.0.0.1:8080/health
```

Expected evidence to show:

```json
{
  "status": "ok",
  "service": "cashflow_guardian",
  "adk_agent": "cashflow_guardian_agent",
  "otel_to_cloud": false
}
```

## 3. Portfolio Snapshot Evidence

Run from the repository root:

```powershell
curl.exe -s -X POST http://127.0.0.1:8080/portfolio_snapshot -H "Content-Type: application/json" --data-binary "@new\curl_payloads\portfolio_snapshot.json"
```

Expected shape:

```json
{
  "company_id": "SME_001",
  "risk_level": "Medium",
  "risk_score": 10,
  "key_drivers": [
    "negative cashflow",
    "low liquidity coverage",
    "increasing overdue receivables"
  ]
}
```

## 4. Prompt Injection Block Evidence

```powershell
curl.exe -s -X POST http://127.0.0.1:8080/prompt_injection_block -H "Content-Type: application/json" --data-binary "@new\curl_payloads\prompt_injection_block.json"
```

Expected evidence to show:

```json
{
  "status": "blocked",
  "answer": "The event message was blocked by prompt-injection controls before tool execution.",
  "warnings": ["Prompt-injection pattern detected."]
}
```

## 5. Draft Intervention Evidence

```powershell
curl.exe -s -X POST http://127.0.0.1:8080/draft_intervention -H "Content-Type: application/json" --data-binary "@new\curl_payloads\draft_intervention.json"
```

Expected shape:

```json
{
  "company_id": "SME_001",
  "recommendations": [
    "increase monitoring frequency",
    "request updated cash-flow information"
  ]
}
```

## 6. Swagger / OpenAPI Evidence

Open this in a browser:

```text
http://127.0.0.1:8080/docs
```

You should see:

- `GET /health`
- `POST /portfolio_snapshot`
- `POST /prompt_injection_block`
- `POST /draft_intervention`
- `POST /apps/cashflow_guardian/trigger/pubsub`

## 7. Optional Pub/Sub-Style Demo Events

The original ADK Pub/Sub endpoint is still available. To create its request bodies:

```powershell
python new\demo_payloads.py
```

Those are stored in `new/demo_events/`.

## 8. Notebook-Style Minimal Code Cell

```python
import base64
import json
from pathlib import Path


def make_pubsub_body(payload: dict, message_id: str) -> dict:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return {
        "message": {
            "data": base64.b64encode(raw).decode("ascii"),
            "messageId": message_id,
            "attributes": {"source": "demo"},
        },
        "subscription": "projects/local/subscriptions/cashflow-guardian-demo",
    }


payload = {
    "event_type": "simulate_scenario",
    "business_id": "B01395",
    "as_of_month": "2025-06",
    "requested_by": "demo.presenter",
    "message": "Stress test a downside liquidity scenario.",
    "parameters": {
        "scenario": {
            "inflow_change_pct": -20.0,
            "outflow_change_pct": 10.0,
            "collection_delay_change_days": 15.0,
        }
    },
}

Path("simulate_scenario.json").write_text(
    json.dumps(make_pubsub_body(payload, "demo-simulate-2025-06"), indent=2),
    encoding="utf-8",
)
```

## 9. Source Code References to Screenshot

- FastAPI entrypoint: `cashflow_guardian/app/adk_app.py`
- Event parsing and routing: `cashflow_guardian/src/cashflow_guardian/agent/ambient.py`
- Policy-gated executor: `cashflow_guardian/src/cashflow_guardian/tools/registry.py`
- RBAC decision function: `cashflow_guardian/src/cashflow_guardian/policy/engine.py`
- Security guards: `cashflow_guardian/src/cashflow_guardian/security/guards.py`
