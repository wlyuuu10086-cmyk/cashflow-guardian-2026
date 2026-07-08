# CashFlow Guardian 2026

CashFlow Guardian is an SME cash-flow early warning and decision-support project. It combines deterministic financial engines with a Google ADK agent layer so users can inspect portfolio health, score cash-flow risk, compare companies with peers, simulate stress scenarios, and draft intervention plans while keeping sensitive operations behind policy and human-review boundaries.

The main application lives in [`cashflow_guardian/`](cashflow_guardian/).

## What This Repository Contains

- `cashflow_guardian/src/`: Core Python package for data access, risk scoring, benchmarking, scenario simulation, policy checks, security controls, and model-safe tools.
- `cashflow_guardian/app/`: FastAPI service for local ambient event handling.
- `cashflow_guardian/agents_cli_agent/`: Agent adapter for command-line usage.
- `cashflow_guardian/tests/`: Unit, integration, and evaluation-oriented tests.
- `cashflow_guardian/specs/`: Product, architecture, model, deployment, evaluation, security, and tool contracts.
- `cashflow_guardian/docs/`: Demo notes, evidence inventory, evaluation notes, and submission materials.
- `cashflow_guardian/artifacts/`: Generated validation outputs, traces, and test evidence.
- `cashflow_guardian/sme_cashflow_stress_project/`: Synthetic SME cash-flow dataset, DuckDB database, notebooks, and starter SQL.
- `new/`: Demo helper page, request payloads, and presentation-support materials.

## Key Capabilities

- Deterministic cash-flow risk scoring from structured financial data.
- Peer benchmarking and stress scenario simulation.
- Model-safe tool routing through explicit policy checks.
- Human-in-the-loop boundaries for privileged actions.
- PII redaction, prompt-injection checks, audit logging, and trace capture.
- Local FastAPI endpoint and Agents CLI integration.

## Quick Start

Install dependencies from the main project directory:

```powershell
cd cashflow_guardian
uv sync
uv pip install -e .
```

Create local environment settings:

```powershell
Copy-Item .env.example .env
```

Then edit `.env` and set your local values, including `GEMINI_API_KEY` if you want to run Gemini-backed agent flows.

Run tests:

```powershell
uv run pytest
```

Start the local API server:

```powershell
uv run python -m uvicorn app.adk_app:app --host 127.0.0.1 --port 8080
```

## Example API Payloads

Demo request payloads are available in [`new/demo_events/`](new/demo_events/) and [`new/curl_payloads/`](new/curl_payloads/). They cover portfolio snapshots, company analysis, scenario simulation, intervention drafting, and security-boundary checks.

## Data And Large Files

This repository includes synthetic SME cash-flow data and trained local artifacts used for validation. One CSV file, `cashflow_guardian/sme_cashflow_stress_project/data/csv/bank_transactions.csv`, is larger than GitHub's recommended 50 MB file size, but below GitHub's 100 MB hard limit.

## Security Notes

Do not commit real `.env` files, credentials, service-account keys, API tokens, or production financial data. The repository is configured to ignore common local secrets, virtual environments, caches, logs, and ADK session databases.

## More Documentation

For the full project description, architecture details, evaluation notes, and limitations, see [`cashflow_guardian/README.md`](cashflow_guardian/README.md).
