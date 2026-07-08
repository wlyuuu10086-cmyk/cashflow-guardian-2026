# CashFlow Guardian: SME Cash-Flow Early Warning and Decision-Support System

## 1. Title
CashFlow Guardian: A Secure, Policy-Gated Agentic SME Liquidity Monitor

## 2. One-Sentence Summary
An SME cash-flow monitoring and decision-support system that combines deterministic financial calculators with a thin, policy-gated Google ADK explanation agent.

## 3. Problem
Small and Medium Enterprises (SMEs) face liquidity challenges due to unpredictable payment delays, seasonal revenue fluctuations, and cost increases. Traditional tools present historical data but do not offer predictive insights or mitigation plans. At the same time, using pure AI models for financial analysis is unsafe because models hallucinate calculations, leak sensitive information, and cannot enforce strict operational boundaries.

## 4. Why This Matters
For an SME, a cash deficit can quickly lead to insolvency. Business owners need early warnings, stress simulations, and action plans. However, they need these insights to be mathematically accurate (backed by database records) and secure (protecting customer privacy and ensuring no unauthorized actions occur).

## 5. Solution
CashFlow Guardian solves this by segregating concerns:
- Mathematical calculations and database queries are handled by authoritative, deterministic Python engines.
- User queries and data summaries are translated by a thin Google ADK agent layer.
- Access is gated by a robust Security and Policy Engine that enforces Role-Based Access Control (RBAC), prevents prompt injection, redacts PII, and maintains human-in-the-loop boundaries.

## 6. Why an Agent is Appropriate
An agent acts as a natural language interface. Instead of requiring users to construct SQL queries or use static dashboards, the agent:
1. Dynamically detects user intent (e.g., benchmarking, stress simulation).
2. Invokes appropriate model-safe tools in sequence.
3. Translates output tables and scores into human-readable early-warning summaries.

## 7. Architecture
```
[Event Source] -> [FastAPI Validation] -> [Trusted Context Binder] -> [Security & PII Screening]
       -> [execute_tool_with_policy] -> [Deterministic Engines & DuckDB] -> [ADK Explainer]
```

## 8. User Flow
1. An event (e.g., `analyze_company`) is pushed to the FastAPI endpoint.
2. The endpoint binds a `SecurityContext` containing user permissions.
3. The query is evaluated:
   - For read-only tasks, the agent queries the data engine and summarizes the risk.
   - For stress testing, the agent runs simulations and outputs cash-flow impact.
   - For interventions, the agent drafts a plan but halts for human approval.

## 9. Course Concepts Demonstrated
- **Agent Orchestration**: Using Google ADK to organize tool usage.
- **Role-Based Access Control (RBAC)**: Restricting agent tool access using structured permissions in `SecurityContext`.
- **Human-in-the-Loop (HITL)**: Restricting critical database/watchlist mutations to manual human approval.
- **Responsible AI**: Pattern-based PII masking and prompt injection containment.
- **Groundedness**: Grounding explanations strictly in deterministic database values rather than LLM-generated math.

## 10. Deterministic and Agent Responsibilities
- **Deterministic**: Querying database records, calculating risk scores, peer percentiles, stress simulations, and writing to the database.
- **Agent**: Introspecting user intent, formatting tables, explaining trends, and drafting intervention templates.

## 11. Model-Safe Tools
The agent has access to a strict allowlist of read-only and draft-only tools:
- `check_business_data_quality`
- `get_portfolio_snapshot`
- `get_business_history`
- `score_cashflow_risk`
- `compare_with_peers`
- `simulate_cashflow_scenario`
- `draft_intervention_plan`

It cannot access privileged watchlist actions.

## 12. Security and Responsible AI
- **PII Filtering**: Masking sensitive phone numbers and emails.
- **Injection Safety**: Terminating queries that attempt to override system rules.
- **Isolated Sessions**: Ensuring user sessions do not bleed memory.

## 13. Human-in-the-Loop
Watchlist actions and intervention executions are kept separate from model parameters. Watchlist additions are marked as `draft_requires_review` and must be manually approved or rejected by a human reviewer.

## 14. Local Runtime
The system is built as a local FastAPI app (`app/adk_app.py`) running on port 8080. It simulates Pub/Sub payloads locally and processes them through the dispatcher.

## 15. Evaluation Methodology
- **Deterministic Smoke Checker**: Validates that agent traces follow safety policies, call allowed tools, and refrain from false claims.
- **Metric Mapping**: Differentiates between local metrics (deterministic custom functions) and cloud-only metrics (Vertex AI Evaluation).

## 16. Results
- **Unit & Integration Tests**: 147 tests pass successfully.
- **Smoke Trace Validation**: Checked 2 smoke cases; passed deterministic validation with 100% compliance.
- **Regression Check**: Confirmed database state (`demo_actions.json`) remains completely unmodified by read-only calls.

## 17. Demo Walkthrough
Shows a walkthrough starting from FastAPI health checks, running portfolio snapshots, simulating a revenue drop, demonstrating prompt-injection blocks, and drafting an intervention plan requiring review.

## 18. Limitations
### Implemented and Verified:
- Deterministic analysis engines (DuckDB + math rules).
- FastAPI endpoint handling push envelopes.
- Policy engine, PII masking, and injection handling.
- Local Gemini inference and read-only tool routing.
- 147 pytest cases.

### Prepared but Not Fully Executed:
- Full 16-case evaluation dataset.

### Not Completed:
- Live Google Cloud / Cloud Run deployment.
- Vertex AI Evaluation/Grading service.
- Live Pub/Sub wireup.

## 19. Future Work
- Connect to GCP to execute automated Vertex AI evaluations.
- Implement production persistent session state.
- Wire to real Pub/Sub topics.

## 20. Repository and Reproduction Instructions
1. Install dependencies: `uv sync && uv pip install -e .`
2. Configure `.env` with a `GEMINI_API_KEY`.
3. Run tests: `uv run pytest`
4. Start FastAPI server: `uv run python -m uvicorn app.adk_app:app --host 0.0.0.0 --port 8080`
