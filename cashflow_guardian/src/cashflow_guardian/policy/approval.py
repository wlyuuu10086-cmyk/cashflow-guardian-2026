from typing import Dict, Any, Tuple
from cashflow_guardian.security.schemas import SecurityContext
from cashflow_guardian.policy.schemas import WatchlistProposal
from cashflow_guardian.policy.permissions import has_permission

# Allowed proposal states
VALID_STATES = {"pending", "approved", "rejected", "expired", "cancelled"}

# Allowed transitions
ALLOWED_TRANSITIONS = {
    "pending": {"approved", "rejected", "expired", "cancelled"}
}

def validate_state_transition(current_state: str, new_state: str) -> Tuple[bool, str]:
    """Validates the state transition of a watchlist proposal.
    
    Allowed transitions:
      pending -> approved
      pending -> rejected
      pending -> expired
      pending -> cancelled
      
    All other transitions are forbidden.
    """
    if current_state not in VALID_STATES:
        return False, f"Invalid current state: '{current_state}'"
        
    if new_state not in VALID_STATES:
        return False, f"Invalid target state: '{new_state}'"
        
    if current_state == new_state:
        return True, ""  # No-op is valid

    allowed_targets = ALLOWED_TRANSITIONS.get(current_state, set())
    if new_state not in allowed_targets:
        return False, f"Prohibited state transition: cannot transition from '{current_state}' to '{new_state}'"
        
    return True, ""

def validate_approval_decision(
    proposal: WatchlistProposal,
    decision: str,  # "approve" or "reject"
    reviewed_by: str,
    reviewed_role: str,
    rationale: str,
    security_context: SecurityContext
) -> Tuple[bool, str, str]:
    """Enforces deterministic business and safety rules for approving or rejecting proposals.
    
    Returns:
        Tuple[is_valid (bool), policy_code (str), error_message (str)]
    """
    # 1. Decision must be exactly approve or reject
    if decision not in ["approve", "reject"]:
        return False, "POLICY_TOOL_DENIED", "Decision must be exactly 'approve' or 'reject'."

    # 2. Rationale must be non-empty
    if not rationale or not rationale.strip():
        return False, "POLICY_TOOL_DENIED", "Approval rationale must be non-empty."

    # 3. Only authorized roles may approve/reject
    required_perm = "watchlist.approve" if decision == "approve" else "watchlist.reject"
    if not has_permission(reviewed_role, required_perm):
        return False, "POLICY_PERMISSION_MISSING", f"Role '{reviewed_role}' is not authorized to review proposals."

    # 4. system_agent may never approve/reject
    if reviewed_role == "system_agent":
        return False, "POLICY_TOOL_DENIED", "System agent is prohibited from reviewing watchlist proposals."

    # 5. Proposer may not approve/reject their own proposal (self-approval block)
    if proposal.proposed_by == reviewed_by:
        return False, "POLICY_SELF_APPROVAL_DENIED", "Conflict of interest: Proposer cannot review their own proposal."

    # 6. Expired proposals may not be reviewed
    if proposal.status == "expired":
        return False, "POLICY_PROPOSAL_EXPIRED", "Cannot review an expired proposal."

    # 7. Disallow duplicate decisions or invalid state transitions
    target_state = "approved" if decision == "approve" else "rejected"
    is_allowed_transition, err_msg = validate_state_transition(proposal.status, target_state)
    if not is_allowed_transition:
        return False, "POLICY_TOOL_DENIED", err_msg

    # 8. future_data_used=True must block approval
    if proposal.future_data_used:
        return False, "POLICY_FUTURE_DATA_BLOCKED", "Security block: Proposal contains future data and cannot be approved."

    # 9. Verify critical evidence present
    if not proposal.evidence_codes or len(proposal.evidence_codes) == 0:
        return False, "POLICY_TOOL_DENIED", "Block: Missing critical evidence codes in proposal."

    return True, "POLICY_TOOL_ALLOWED", ""
