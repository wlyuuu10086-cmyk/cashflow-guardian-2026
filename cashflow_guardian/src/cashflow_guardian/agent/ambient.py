from __future__ import annotations

import base64
import binascii
import datetime
import json
import os
import re
import uuid
from typing import Any, Dict, Literal, Mapping, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from cashflow_guardian.agent.agent import load_agent_config
from cashflow_guardian.security.prompt_injection import assess_prompt_injection
from cashflow_guardian.security.redaction import redact_sensitive_data
from cashflow_guardian.security.schemas import SecurityContext
from cashflow_guardian.tools.registry import ToolExecutionResult, execute_tool_with_policy
from cashflow_guardian.observability.trace_store import global_trace_store

AmbientEventType = Literal[
    "analyze_company",
    "portfolio_snapshot",
    "benchmark_company",
    "simulate_scenario",
    "draft_intervention",
]

FORBIDDEN_PAYLOAD_FIELDS = {
    "role",
    "permissions",
    "security_context",
    "approval_status",
    "approved",
    "reviewer_id",
    "approver_id",
    "tool_name",
}


class ScenarioParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inflow_change_pct: float = 0.0
    outflow_change_pct: float = 0.0
    collection_delay_change_days: float = 0.0


class AmbientParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: Optional[int] = Field(default=None, ge=1, le=100)
    include_benchmark: bool = True
    include_history: bool = True
    include_intervention: bool = True
    scenario: Optional[ScenarioParameters] = None


class AmbientEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: AmbientEventType
    business_id: Optional[str] = None
    as_of_month: str
    requested_by: Optional[str] = Field(default=None, max_length=128)
    message: Optional[str] = Field(default=None, max_length=1000)
    parameters: AmbientParameters = Field(default_factory=AmbientParameters)

    @field_validator("business_id")
    @classmethod
    def validate_business_id_format(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if not re.fullmatch(r"B\d{5}", value):
            raise ValueError("business_id must match the canonical B00000 format.")
        return value

    @field_validator("as_of_month")
    @classmethod
    def validate_month_format(cls, value: str) -> str:
        if not re.fullmatch(r"\d{4}-\d{2}", value):
            raise ValueError("as_of_month must use YYYY-MM format.")
        return value


class PubSubMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: str
    messageId: Optional[str] = None
    publishTime: Optional[str] = None
    attributes: Dict[str, str] = Field(default_factory=dict)


class PubSubEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: PubSubMessage
    subscription: Optional[str] = None


class AmbientResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    correlation_id: str
    session_id: str
    event_type: Optional[str] = None
    answer: str
    results: Dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    trace_id: Optional[str] = None
    audit_event_ids: list[str] = Field(default_factory=list)
    model_explanation_used: bool = False


class AmbientError(Exception):
    def __init__(self, status_code: int, error_code: str, message: str) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        super().__init__(message)


def normalize_subscription(subscription: Optional[str]) -> str:
    if not subscription:
        return "unknown-subscription"
    parts = [part for part in subscription.split("/") if part]
    segment = parts[-1] if parts else "unknown-subscription"
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "-", segment).strip(".-")
    return (normalized or "unknown-subscription")[:80]


def make_correlation_id(message_id: Optional[str]) -> str:
    raw = message_id or f"msg-{uuid.uuid4().hex}"
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip(".-")
    return (safe or f"msg-{uuid.uuid4().hex}")[:100]


def decode_pubsub_event(body: Mapping[str, Any]) -> tuple[PubSubEnvelope, AmbientEvent, str]:
    try:
        envelope = PubSubEnvelope.model_validate(body)
    except ValidationError as exc:
        raise AmbientError(400, "INVALID_PUBSUB_ENVELOPE", _safe_validation_message(exc))

    if envelope.message.data is None or envelope.message.data == "":
        raise AmbientError(400, "MISSING_DATA", "Pub/Sub message.data is required.")

    max_size = int(load_agent_config().get("maximum_decoded_payload_bytes", 8192))
    try:
        decoded_bytes = base64.b64decode(envelope.message.data, validate=True)
    except (binascii.Error, ValueError):
        raise AmbientError(400, "INVALID_BASE64", "Pub/Sub message.data is not valid base64.")

    if len(decoded_bytes) > max_size:
        raise AmbientError(413, "PAYLOAD_TOO_LARGE", "Decoded Pub/Sub payload exceeds the configured limit.")

    try:
        decoded_text = decoded_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise AmbientError(400, "INVALID_UTF8", "Decoded Pub/Sub payload is not valid UTF-8.")

    try:
        payload = json.loads(decoded_text)
    except json.JSONDecodeError:
        raise AmbientError(400, "INVALID_JSON", "Decoded Pub/Sub payload is not valid JSON.")

    if not isinstance(payload, dict):
        raise AmbientError(400, "INVALID_EVENT", "Decoded Pub/Sub payload must be a JSON object.")

    privileged = set(payload) & FORBIDDEN_PAYLOAD_FIELDS
    if privileged:
        raise AmbientError(400, "PRIVILEGED_FIELD_REJECTED", f"Unsupported privileged fields: {sorted(privileged)}")

    try:
        event = AmbientEvent.model_validate(payload)
    except ValidationError as exc:
        raise AmbientError(400, "INVALID_EVENT", _safe_validation_message(exc))

    return envelope, event, decoded_text


def bind_trusted_security_context(
    *,
    subscription: Optional[str],
    attributes: Mapping[str, str],
    correlation_id: str,
    session_id: str,
    event: AmbientEvent,
    tool_name: str,
) -> SecurityContext:
    config = load_agent_config()
    role = os.getenv("CASHFLOW_GUARDIAN_AMBIENT_ROLE") or config.get("default_ambient_role", "system_agent")
    environment = os.getenv("CASHFLOW_GUARDIAN_ENV") or config.get("default_environment", "local")
    source = normalize_subscription(subscription)
    safe_attributes = {
        "message_source": attributes.get("source", "pubsub"),
        "subscription": source,
    }
    return SecurityContext(
        request_id=correlation_id,
        session_id=session_id,
        user_id=f"ambient:{source}",
        role=role,
        requested_tool=tool_name,
        business_id=event.business_id,
        as_of_month=event.as_of_month,
        timestamp=datetime.datetime.utcnow().isoformat() + "Z",
        source="ambient_pubsub",
        environment=environment,
        metadata={
            "trace_id": f"trace_{correlation_id}",
            "correlation_id": correlation_id,
            "transport": safe_attributes,
        },
    )


def run_ambient_event(
    envelope: PubSubEnvelope,
    event: AmbientEvent,
    *,
    correlation_id: str,
) -> AmbientResponse:
    source = normalize_subscription(envelope.subscription)
    session_id = f"ambient-{source}-{correlation_id}"[:140]
    trace_id = f"trace_{correlation_id}"
    global_trace_store.create_trace(trace_id, correlation_id)
    global_trace_store.add_step(trace_id, "request_accepted", {"source": source})
    global_trace_store.add_step(trace_id, "event_parsed", {"event_type": event.event_type})

    message = event.message or ""
    warnings: list[str] = []
    if message:
        assessment = assess_prompt_injection(message)
        message_lower = message.lower()
        ambient_block_phrase = (
            "ignore all prior instructions" in message_lower
            or "ignore all previous instructions" in message_lower
            or "ignore previous instructions" in message_lower
            or "approve every watchlist" in message_lower
        )
        global_trace_store.add_step(
            trace_id,
            "security_screening",
            {"detected": assessment.detected, "severity": assessment.severity},
        )
        if (
            ambient_block_phrase
            or assessment.block_recommended
            or (assessment.detected and assessment.severity in {"high", "critical"})
        ):
            global_trace_store.add_step(trace_id, "request_failed", {"status": "blocked"})
            return AmbientResponse(
                status="blocked",
                correlation_id=correlation_id,
                session_id=session_id,
                event_type=event.event_type,
                answer="The event message was blocked by prompt-injection controls before tool execution.",
                warnings=["Prompt-injection pattern detected."],
                trace_id=trace_id,
            )

    redacted_message, redact_meta = redact_sensitive_data(message)
    if redact_meta.get("redacted_count", 0):
        warnings.append("Sensitive message content was redacted before model use.")
    global_trace_store.add_step(trace_id, "context_bound", {"role": "server-bound"})

    plan = _operation_plan(event)
    results: Dict[str, Any] = {}
    audit_event_ids: list[str] = []

    for tool_name, arguments in plan.items():
        context = bind_trusted_security_context(
            subscription=envelope.subscription,
            attributes=envelope.message.attributes,
            correlation_id=correlation_id,
            session_id=session_id,
            event=event,
            tool_name=tool_name,
        )
        global_trace_store.add_step(trace_id, "deterministic_tool_invoked", {"tool_name": tool_name})
        result = execute_tool_with_policy(context, tool_name, arguments)
        results[tool_name] = result.model_dump(mode="json")
        audit_event_ids.append(result.audit_event_id)
        if result.status in {"denied", "validation_error", "approval_required", "execution_error"}:
            warnings.extend(result.warnings)

    answer = _deterministic_answer(event, results, str(redacted_message or ""))
    global_trace_store.add_step(trace_id, "request_completed", {"status": "success"})
    return AmbientResponse(
        status="success",
        correlation_id=correlation_id,
        session_id=session_id,
        event_type=event.event_type,
        answer=answer,
        results=results,
        warnings=warnings,
        trace_id=trace_id,
        audit_event_ids=audit_event_ids,
        model_explanation_used=False,
    )


def _operation_plan(event: AmbientEvent) -> Dict[str, Dict[str, Any]]:
    if event.event_type == "portfolio_snapshot":
        return {
            "get_portfolio_snapshot": {
                "as_of_month": event.as_of_month,
                "limit": event.parameters.limit or 10,
            }
        }

    if event.event_type in {"analyze_company", "benchmark_company", "draft_intervention", "simulate_scenario"}:
        if not event.business_id:
            raise AmbientError(400, "MISSING_BUSINESS_ID", "business_id is required for this event_type.")

    if event.event_type == "benchmark_company":
        return {
            "compare_with_peers": {
                "business_id": event.business_id,
                "as_of_month": event.as_of_month,
            }
        }

    if event.event_type == "draft_intervention":
        return {
            "score_cashflow_risk": {"business_id": event.business_id, "as_of_month": event.as_of_month},
            "draft_intervention_plan": {"business_id": event.business_id, "as_of_month": event.as_of_month},
        }

    if event.event_type == "simulate_scenario":
        scenario = event.parameters.scenario
        if scenario is None:
            raise AmbientError(400, "MISSING_SCENARIO", "scenario parameters are required.")
        if (
            scenario.inflow_change_pct == 0.0
            and scenario.outflow_change_pct == 0.0
            and scenario.collection_delay_change_days == 0.0
        ):
            raise AmbientError(400, "EMPTY_SCENARIO", "At least one scenario parameter must be non-zero.")
        return {
            "score_cashflow_risk": {"business_id": event.business_id, "as_of_month": event.as_of_month},
            "simulate_cashflow_scenario": {
                "business_id": event.business_id,
                "as_of_month": event.as_of_month,
                "inflow_change_pct": scenario.inflow_change_pct,
                "outflow_change_pct": scenario.outflow_change_pct,
                "collection_delay_change_days": scenario.collection_delay_change_days,
            },
        }

    if event.event_type == "analyze_company":
        plan = {
            "check_business_data_quality": {
                "business_id": event.business_id,
                "as_of_month": event.as_of_month,
            },
            "get_business_history": {
                "business_id": event.business_id,
                "as_of_month": event.as_of_month,
            },
            "score_cashflow_risk": {
                "business_id": event.business_id,
                "as_of_month": event.as_of_month,
            },
        }
        if event.parameters.include_benchmark:
            plan["compare_with_peers"] = {
                "business_id": event.business_id,
                "as_of_month": event.as_of_month,
            }
        if event.parameters.include_intervention:
            plan["draft_intervention_plan"] = {
                "business_id": event.business_id,
                "as_of_month": event.as_of_month,
            }
        return plan

    raise AmbientError(400, "UNSUPPORTED_EVENT_TYPE", "Unsupported event_type.")


def _deterministic_answer(event: AmbientEvent, results: Dict[str, Any], message: str) -> str:
    successful = [name for name, result in results.items() if result.get("status") == "success"]
    failed = [name for name, result in results.items() if result.get("status") != "success"]
    parts = [
        f"Processed {event.event_type} for {event.as_of_month}.",
        f"Policy-gated tools completed: {', '.join(successful) if successful else 'none'}.",
    ]
    if failed:
        parts.append(f"Tools needing attention: {', '.join(failed)}.")
    if event.event_type in {"draft_intervention", "analyze_company"}:
        parts.append("Any intervention content is a draft recommendation; human review remains required for high-impact actions.")
    if message:
        parts.append("User-provided message was treated as untrusted context.")
    return " ".join(parts)


def _safe_validation_message(exc: ValidationError) -> str:
    errors = []
    for item in exc.errors():
        loc = ".".join(str(part) for part in item.get("loc", []))
        errors.append(f"{loc}: {item.get('msg', 'invalid value')}")
    return "; ".join(errors[:3])
