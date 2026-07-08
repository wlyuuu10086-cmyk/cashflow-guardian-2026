import os
import json
import uuid
import datetime
import threading
from typing import List, Dict, Any, Optional, Tuple
from cashflow_guardian.security.schemas import SecurityContext
from cashflow_guardian.policy.schemas import WatchlistProposal, ApprovalDecision, WatchlistActionRecord
from cashflow_guardian.policy.permissions import has_permission
from cashflow_guardian.policy.approval import validate_approval_decision
from cashflow_guardian.security.redaction import redact_sensitive_data

# Thread lock for process-level safety
_LOCK = threading.Lock()

def _get_demo_actions_path() -> str:
    """Resolves target JSON action store path."""
    if "CASHFLOW_GUARDIAN_DEMO_ACTIONS_PATH" in os.environ:
        return os.environ["CASHFLOW_GUARDIAN_DEMO_ACTIONS_PATH"]
    from cashflow_guardian.data_engine.connection import get_repo_root
    return str(get_repo_root() / "cashflow_guardian" / "data" / "demo_actions.json")

def _initialize_store_if_absent(file_path: str) -> None:
    """Safely creates demo_actions.json with default schema structure if missing."""
    if not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        default_data = {
            "schema_version": "1.0",
            "updated_at": datetime.datetime.utcnow().isoformat() + "Z",
            "proposals": [],
            "decisions": [],
            "watchlist": []
        }
        # Thread-safe write
        temp_path = file_path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=2)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
        os.replace(temp_path, file_path)

def _load_store(file_path: str) -> Dict[str, Any]:
    """Loads and validates actions store. Raises ValueError on corruption."""
    _initialize_store_if_absent(file_path)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise ValueError(f"Persistence Corruption: Failed to read demo actions JSON file: {e}")
        
    # Schema validation
    if data.get("schema_version") != "1.0":
        raise ValueError(f"Persistence Corruption: Unsupported schema version: '{data.get('schema_version')}'")
        
    for k in ["proposals", "decisions", "watchlist"]:
        if k not in data:
            raise ValueError(f"Persistence Corruption: Missing required section '{k}' in store.")
            
    return data

def _save_store(file_path: str, data: Dict[str, Any]) -> None:
    """Atomically replaces actions store."""
    if not isinstance(data, dict) or data.get("schema_version") != "1.0":
        raise ValueError("Invalid store structure or version before write.")
        
    dir_name = os.path.dirname(file_path)
    temp_path = os.path.join(dir_name, f"temp_{uuid.uuid4().hex}.json")
    
    try:
        data["updated_at"] = datetime.datetime.utcnow().isoformat() + "Z"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            try:
                os.fsync(f.fileno())
            except Exception:
                pass
        os.replace(temp_path, file_path)
    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        raise IOError(f"Atomic persistence failure: {e}")

def create_watchlist_proposal(
    business_id: str,
    as_of_month: str,
    proposed_by: str,
    risk_result: Dict[str, Any],
    intervention_plan: Dict[str, Any],
    security_context: SecurityContext,
    idempotency_key: Optional[str] = None
) -> Dict[str, Any]:
    """Creates a new watchlist proposal in the pending state.
    
    Enforces RBAC permissions, validates business inputs, checks for duplicate
    pending proposals, and stores it atomically.
    """
    # 1. Enforce RBAC permission
    if not has_permission(security_context.role, "watchlist.propose"):
        raise PermissionError(f"Role '{security_context.role}' is not authorized to propose watchlist additions.")

    # 2. Check for SQLi / path traversal on business_id via security validation
    from cashflow_guardian.security.validation import validate_input_value
    validate_input_value("business_id", business_id)
    validate_input_value("as_of_month", as_of_month)

    # Resolve idempotency key from metadata if not explicitly provided
    if not idempotency_key:
        idempotency_key = security_context.metadata.get("idempotency_key")

    with _LOCK:
        file_path = _get_demo_actions_path()
        store = _load_store(file_path)

        # 3. Check Idempotency / Duplicate Pending Proposals
        # Reject if another proposal is pending for same business and month, or matched idempotency_key
        for prop_data in store["proposals"]:
            # Check metadata or parameters
            existing_key = prop_data.get("metadata", {}).get("idempotency_key")
            if idempotency_key and existing_key == idempotency_key:
                return prop_data
                
            if prop_data["business_id"] == business_id and prop_data["as_of_month"] == as_of_month and prop_data["status"] == "pending":
                # Return existing pending proposal
                return prop_data

        # 4. Extract safe fields for proposal
        risk_score = float(risk_result.get("risk_score", 0.0))
        risk_tier = risk_result.get("risk_tier", "GREEN")
        scoring_mode = risk_result.get("scoring_mode", "rule_based_fallback")
        model_version = risk_result.get("model_version")
        
        evidence_codes = intervention_plan.get("evidence_codes", [])
        top_risk_drivers = risk_result.get("feature_contributions", [])
        # Simplify top risk drivers to string names
        top_drivers_list = []
        for drv in top_risk_drivers:
            if isinstance(drv, dict) and "feature_name" in drv:
                top_drivers_list.append(drv["feature_name"])
            elif isinstance(drv, str):
                top_drivers_list.append(drv)
                
        # Benchmark and intervention summaries
        benchmark_summary = {
            "business_id": business_id,
            "as_of_month": as_of_month,
            "status": "available"
        }
        
        intervention_summary = {
            "recommended_playbook": intervention_plan.get("recommended_playbook", ""),
            "allowed_actions": intervention_plan.get("allowed_actions", [])
        }

        # Check future data usage flags
        future_data_used = risk_result.get("future_data_used", False) or risk_result.get("provenance", {}).get("future_data_used", False)

        # Build proposal structure
        now_str = datetime.datetime.utcnow().isoformat() + "Z"
        expires_dt = datetime.datetime.utcnow() + datetime.timedelta(days=30)
        expires_str = expires_dt.isoformat() + "Z"

        proposal_id = f"proposal_{uuid.uuid4().hex[:16]}"
        
        # Redact any potentially sensitive info in text arguments
        reason = security_context.metadata.get("reason", f"High risk score {risk_score} in {as_of_month}")
        redacted_reason, _ = redact_sensitive_data(reason)

        proposal = WatchlistProposal(
            proposal_id=proposal_id,
            business_id=business_id,
            as_of_month=as_of_month,
            proposed_action="add_to_watchlist",
            proposed_by=proposed_by,
            proposer_role=security_context.role,
            created_at=now_str,
            expires_at=expires_str,
            risk_score=risk_score,
            risk_tier=risk_tier,
            scoring_mode=scoring_mode,
            model_version=model_version,
            evidence_codes=evidence_codes,
            top_risk_drivers=top_drivers_list,
            benchmark_summary=benchmark_summary,
            intervention_summary=intervention_summary,
            human_approval_required=True,
            status="pending",
            source_provenance=risk_result.get("provenance", {}),
            future_data_used=future_data_used
        )

        proposal_dict = proposal.model_dump()
        # Add metadata for idempotency tracking
        proposal_dict["metadata"] = {
            "idempotency_key": idempotency_key,
            "reason": redacted_reason
        }

        store["proposals"].append(proposal_dict)
        _save_store(file_path, store)
        
        return proposal_dict

def review_watchlist_proposal(
    proposal_id: str,
    decision: str,  # "approve" or "reject"
    reviewed_by: str,
    rationale: str,
    security_context: SecurityContext
) -> Dict[str, Any]:
    """Reviews (approves/rejects) a pending proposal.
    
    Enforces proposer self-approval limits, role permissions, state transition limits,
    idempotency, and stores the updated watchlist record atomically.
    """
    from cashflow_guardian.security.validation import validate_input_value
    validate_input_value("proposal_id", proposal_id)
    
    with _LOCK:
        file_path = _get_demo_actions_path()
        store = _load_store(file_path)

        # 1. Fetch proposal
        proposal_idx = -1
        for idx, prop in enumerate(store["proposals"]):
            if prop["proposal_id"] == proposal_id:
                proposal_idx = idx
                break

        if proposal_idx == -1:
            raise ValueError(f"Proposal '{proposal_id}' was not found in actions store.")

        proposal_dict = store["proposals"][proposal_idx]
        proposal = WatchlistProposal(**proposal_dict)

        # 2. Idempotency checks
        # If proposal is already reviewed, verify if this matches the requested decision
        target_status = "approved" if decision == "approve" else "rejected"
        
        # Check if already processed
        if proposal.status != "pending":
            if proposal.status == "approved" and target_status == "approved":
                raise ValueError(f"Conflict: Proposal '{proposal_id}' is already approved.")
                
            if proposal.status == target_status:
                # Repeated decision (idempotent response for rejections)
                # Find the existing decision record
                for dec in store["decisions"]:
                    if dec["proposal_id"] == proposal_id:
                        return {
                            "action_id": proposal_id,
                            "updated_status": proposal.status,
                            "audit_timestamp": dec["reviewed_at"]
                        }
            # If transition is invalid (e.g. approved -> rejected or vice versa), raise conflict
            raise ValueError(f"Conflict: Proposal '{proposal_id}' is already in state '{proposal.status}' and cannot be reviewed as '{decision}'.")

        # 3. Enforce approval rules
        is_valid, policy_code, err_msg = validate_approval_decision(
            proposal=proposal,
            decision=decision,
            reviewed_by=reviewed_by,
            reviewed_role=security_context.role,
            rationale=rationale,
            security_context=security_context
        )

        if not is_valid:
            raise ValueError(f"Policy violation ({policy_code}): {err_msg}")

        # 4. Apply transition
        proposal.status = target_state = target_status
        store["proposals"][proposal_idx] = proposal.model_dump()
        
        # Redact review rationale
        redacted_rationale, _ = redact_sensitive_data(rationale)

        # Add review decision
        decision_id = f"decision_{uuid.uuid4().hex[:16]}"
        now_str = datetime.datetime.utcnow().isoformat() + "Z"
        
        decision_record = {
            "decision_id": decision_id,
            "proposal_id": proposal_id,
            "decision": decision,
            "reviewed_by": reviewed_by,
            "reviewed_role": security_context.role,
            "rationale": redacted_rationale,
            "reviewed_at": now_str
        }
        store["decisions"].append(decision_record)

        # 5. Mutate watchlist if approved
        if decision == "approve":
            biz_id = proposal.business_id
            # Enforce that a business never appears twice in the watchlist
            if biz_id not in store["watchlist"]:
                store["watchlist"].append(biz_id)

        # Save store atomically
        _save_store(file_path, store)

        return {
            "action_id": proposal_id,
            "updated_status": proposal.status,
            "audit_timestamp": now_str
        }

def list_pending_watchlist_proposals(security_context: SecurityContext) -> List[Dict[str, Any]]:
    """Lists all proposals that are currently in pending status."""
    # Read permission check
    if not (has_permission(security_context.role, "business.read") or has_permission(security_context.role, "watchlist.propose")):
        raise PermissionError(f"Role '{security_context.role}' is not authorized to list proposals.")

    with _LOCK:
        file_path = _get_demo_actions_path()
        store = _load_store(file_path)
        return [prop for prop in store["proposals"] if prop["status"] == "pending"]

def get_watchlist_action_history(
    business_id: Optional[str] = None,
    security_context: Optional[SecurityContext] = None
) -> List[Dict[str, Any]]:
    """Gets history of proposal actions, optionally filtered by business_id."""
    if security_context:
        if not (has_permission(security_context.role, "business.read") or has_permission(security_context.role, "audit.read")):
            raise PermissionError(f"Role '{security_context.role}' is not authorized to read history.")

    with _LOCK:
        file_path = _get_demo_actions_path()
        store = _load_store(file_path)
        
        history = []
        for prop in store["proposals"]:
            if business_id and prop["business_id"] != business_id:
                continue
                
            # Find associated decision
            assoc_decision = None
            for dec in store["decisions"]:
                if dec["proposal_id"] == prop["proposal_id"]:
                    assoc_decision = dec
                    break
                    
            history.append({
                "proposal": prop,
                "decision": assoc_decision
            })
            
        return history

def get_active_watchlist() -> List[str]:
    """Returns the list of active watchlist business IDs."""
    with _LOCK:
        file_path = _get_demo_actions_path()
        store = _load_store(file_path)
        return store.get("watchlist", [])
