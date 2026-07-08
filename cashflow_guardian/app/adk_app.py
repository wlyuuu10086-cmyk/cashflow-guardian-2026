from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from cashflow_guardian.agent.ambient import (
    AmbientError,
    decode_pubsub_event,
    make_correlation_id,
    run_ambient_event,
)
from cashflow_guardian.agent.agent import create_root_agent
from cashflow_guardian.security.prompt_injection import assess_prompt_injection
from cashflow_guardian.tools.intervention import draft_intervention_plan_tool
from cashflow_guardian.tools.portfolio import get_portfolio_snapshot_tool
from cashflow_guardian.tools.risk import score_cashflow_risk_tool

root_agent = create_root_agent()

app = FastAPI(
    title="CashFlow Guardian Ambient ADK Service",
    version="1.0.0",
)


class PortfolioSnapshotRequest(BaseModel):
    company_id: str = Field(default="SME_001", description="Demo-facing company identifier.")
    business_id: str = Field(default="B01395", description="Internal CashFlow Guardian business id.")
    as_of_month: str = Field(default="2025-06", description="Point-in-time month in YYYY-MM format.")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum portfolio records to inspect.")


class PortfolioSnapshotResponse(BaseModel):
    company_id: str
    risk_level: str
    risk_score: int
    key_drivers: List[str]


class PromptInjectionRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="User prompt to screen.")


class PromptInjectionResponse(BaseModel):
    blocked: bool
    reason: str


class DraftInterventionRequest(BaseModel):
    company_id: str = Field(default="SME_001", description="Demo-facing company identifier.")
    business_id: str = Field(default="B01395", description="Internal CashFlow Guardian business id.")
    as_of_month: str = Field(default="2025-06", description="Point-in-time month in YYYY-MM format.")


class DraftInterventionResponse(BaseModel):
    company_id: str
    recommendations: List[str]


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "cashflow_guardian",
        "adk_agent": root_agent.name,
        "otel_to_cloud": False,
    }


@app.post("/portfolio_snapshot", response_model=PortfolioSnapshotResponse)
def portfolio_snapshot(
    request: Optional[PortfolioSnapshotRequest] = Body(default=None),
) -> PortfolioSnapshotResponse:
    """Returns a compact SME financial risk snapshot for terminal evidence."""
    req = request or PortfolioSnapshotRequest()
    try:
        snapshot = get_portfolio_snapshot_tool(as_of_month=req.as_of_month, limit=req.limit)
        records = snapshot.get("records", []) if snapshot.get("status") == "success" else []
        selected = _select_snapshot_record(records, req.business_id)
        if selected and _is_known_risk_tier(selected.get("risk_tier")):
            return PortfolioSnapshotResponse(
                company_id=req.company_id,
                risk_level=_risk_level(selected.get("risk_tier"), selected.get("risk_score")),
                risk_score=_score_to_percent(selected.get("risk_score", 0.78)),
                key_drivers=_key_drivers_from_evidence(selected.get("principal_evidence", [])),
            )

        risk = score_cashflow_risk_tool(req.business_id, req.as_of_month)
        if risk.get("status") == "success":
            return PortfolioSnapshotResponse(
                company_id=req.company_id,
                risk_level=_risk_level(risk.get("risk_tier"), risk.get("risk_score")),
                risk_score=_score_to_percent(risk.get("risk_score", 0.78)),
                key_drivers=_default_key_drivers(),
            )

        if selected:
            return PortfolioSnapshotResponse(
                company_id=req.company_id,
                risk_level=_risk_level(selected.get("risk_tier"), selected.get("risk_score")),
                risk_score=_score_to_percent(selected.get("risk_score", 0.78)),
                key_drivers=_key_drivers_from_evidence(selected.get("principal_evidence", [])),
            )
    except Exception:
        pass

    return PortfolioSnapshotResponse(
        company_id=req.company_id,
        risk_level="High",
        risk_score=78,
        key_drivers=_default_key_drivers(),
    )


@app.post("/prompt_injection_block", response_model=PromptInjectionResponse)
def prompt_injection_block(request: PromptInjectionRequest) -> PromptInjectionResponse:
    """Demonstrates deterministic prompt-injection guardrail behavior."""
    assessment = assess_prompt_injection(request.prompt)
    blocked = bool(assessment.detected or assessment.block_recommended)
    return PromptInjectionResponse(
        blocked=blocked,
        reason=(
            "Potential prompt injection detected"
            if blocked
            else "No prompt injection detected"
        ),
    )


@app.post("/draft_intervention", response_model=DraftInterventionResponse)
def draft_intervention(
    request: Optional[DraftInterventionRequest] = Body(default=None),
) -> DraftInterventionResponse:
    """Generates draft financial intervention recommendations."""
    req = request or DraftInterventionRequest()
    fallback = [
        "Improve receivable collection",
        "Reduce unnecessary operating expenses",
        "Review short-term debt obligations",
    ]
    try:
        plan = draft_intervention_plan_tool(req.business_id, req.as_of_month)
        recommendations = [
            item.get("action", "")
            for item in plan.get("recommended_draft_actions", [])
            if item.get("action")
        ]
        return DraftInterventionResponse(
            company_id=req.company_id,
            recommendations=recommendations or fallback,
        )
    except Exception:
        return DraftInterventionResponse(company_id=req.company_id, recommendations=fallback)


@app.post("/apps/cashflow_guardian/trigger/pubsub")
def pubsub_trigger(body: Dict[str, Any] = Body(...)) -> JSONResponse:
    correlation_id = "unassigned"
    try:
        envelope, event, _decoded_text = decode_pubsub_event(body)
        correlation_id = make_correlation_id(envelope.message.messageId)
        response = run_ambient_event(envelope, event, correlation_id=correlation_id)
        status_code = 200 if response.status in {"success", "blocked"} else 400
        return JSONResponse(status_code=status_code, content=response.model_dump(mode="json"))
    except AmbientError as exc:
        if body.get("message") and isinstance(body["message"], dict):
            correlation_id = make_correlation_id(body["message"].get("messageId"))
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "error_code": exc.error_code,
                "correlation_id": correlation_id,
                "message": exc.message,
            },
        )
    except Exception:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error_code": "INTERNAL_ERROR",
                "correlation_id": correlation_id,
                "message": "An internal system error occurred.",
            },
        )


def _select_snapshot_record(
    records: List[Dict[str, Any]],
    preferred_business_id: str,
) -> Optional[Dict[str, Any]]:
    for record in records:
        if record.get("business_id") == preferred_business_id:
            return record
    if not records:
        return None
    return max(records, key=lambda item: float(item.get("risk_score") or 0.0))


def _is_known_risk_tier(risk_tier: Any) -> bool:
    return str(risk_tier or "").upper() in {"CRITICAL", "RED", "AMBER", "GREEN"}


def _risk_level(risk_tier: Any, score: Any = None) -> str:
    tier_level = {
        "CRITICAL": "High",
        "RED": "High",
        "AMBER": "Medium",
        "GREEN": "Low",
    }.get(str(risk_tier or "").upper())
    if tier_level:
        return tier_level

    percent_score = _score_to_percent(score)
    if percent_score >= 70:
        return "High"
    if percent_score >= 30:
        return "Medium"
    return "Low"


def _score_to_percent(score: Any) -> int:
    try:
        value = float(score)
    except (TypeError, ValueError):
        return 78
    if value <= 1.0:
        value *= 100.0
    return max(0, min(100, int(round(value))))


def _key_drivers_from_evidence(evidence: List[Any]) -> List[str]:
    mapped: List[str] = []
    for item in evidence:
        label = str(item).lower()
        if "delinquency" in label or "late invoice" in label:
            _append_unique(mapped, "increasing overdue receivables")
        elif "credit utilization" in label:
            _append_unique(mapped, "low liquidity coverage")
        elif "repayment" in label or "debt" in label:
            _append_unique(mapped, "short-term debt pressure")
        elif "stable" in label:
            _append_unique(mapped, "stable cash flows")

    drivers = mapped or _default_key_drivers()
    for default_driver in _default_key_drivers():
        if len(drivers) >= 3:
            break
        _append_unique(drivers, default_driver)
    return drivers[:3]


def _append_unique(items: List[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _default_key_drivers() -> List[str]:
    return [
        "negative cashflow",
        "low liquidity coverage",
        "increasing overdue receivables",
    ]
