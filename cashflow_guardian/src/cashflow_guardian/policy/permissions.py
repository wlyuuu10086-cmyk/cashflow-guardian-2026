import yaml
from pathlib import Path
from typing import Dict, Any, List, Set

# Standard lists of approved entities for fail-closed validation
APPROVED_ROLES: Set[str] = {"analyst", "relationship_manager", "risk_manager", "administrator", "system_agent"}
APPROVED_PERMISSIONS: Set[str] = {
    "portfolio.read",
    "business.read",
    "risk.read",
    "benchmark.read",
    "scenario.run",
    "intervention.draft",
    "watchlist.propose",
    "watchlist.approve",
    "watchlist.reject",
    "audit.read"
}

def get_repo_root() -> Path:
    """Resolves the repository root dynamically."""
    return Path(__file__).resolve().parent.parent.parent.parent.parent

def load_policies_config() -> Dict[str, Any]:
    """Loads policies.yaml configuration."""
    repo_root = get_repo_root()
    path = repo_root / "cashflow_guardian" / "policies.yaml"
    if not path.exists():
        path = repo_root / "policies.yaml"
    if not path.exists():
        raise FileNotFoundError(f"policies.yaml not found at {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f)

# Global configurations populated at import time
_ROLE_PERMISSIONS: Dict[str, List[str]] = {}
_TOOL_PERMISSIONS: Dict[str, str] = {}

def validate_policy_integrity() -> None:
    """Compares registry permissions with policies.yaml at import time.
    
    Fails closed on unknown roles, tools, permissions, or conflicts.
    """
    global _ROLE_PERMISSIONS, _TOOL_PERMISSIONS
    
    # 1. Load policies.yaml
    policies = load_policies_config()
    
    # 2. Import registry after configuration helper is declared to avoid circular imports
    from cashflow_guardian.tools.registry import APPROVED_TOOL_NAMES, get_tool_registry
    
    role_perms = policies.get("role_permissions", {})
    tool_perms = policies.get("tool_permissions", {})
    
    # 3. Check for unknown roles
    for role in role_perms:
        if role not in APPROVED_ROLES:
            raise ValueError(f"Policy Integrity Error: Unknown role '{role}' configured in policies.yaml")
            
    # 4. Check for unknown permissions
    for role, data in role_perms.items():
        allowed_perms = data.get("allowed_permissions", [])
        for perm in allowed_perms:
            if perm not in APPROVED_PERMISSIONS:
                raise ValueError(f"Policy Integrity Error: Unknown permission '{perm}' configured for role '{role}'")
                
    # 5. Check tool permissions alignment with registry approved tool list
    policy_tools = set(tool_perms.keys())
    registry_tools = set(APPROVED_TOOL_NAMES)
    
    if policy_tools != registry_tools:
        missing_in_policy = registry_tools - policy_tools
        missing_in_registry = policy_tools - registry_tools
        msg = "Policy Integrity Error: Tool mismatch between registry and policies.yaml."
        if missing_in_policy:
            msg += f" Missing in policies.yaml: {missing_in_policy}."
        if missing_in_registry:
            msg += f" Missing in registry: {missing_in_registry}."
        raise ValueError(msg)
        
    # 6. Check that every configured tool maps to a known approved permission
    for tool_name, perm in tool_perms.items():
        if perm not in APPROVED_PERMISSIONS:
            raise ValueError(f"Policy Integrity Error: Tool '{tool_name}' maps to unknown permission '{perm}'")
            
    # 7. Check for conflicts with the Tool Registry permissions (read-only vs write)
    registry = get_tool_registry()
    for tool_name, entry in registry.items():
        required_perm = tool_perms[tool_name]
        
        # Check read-only alignment
        if required_perm.endswith(".read") and entry.permission != "read-only":
            raise ValueError(f"Policy Integrity Error: Tool '{tool_name}' is read-only in policy but registry says '{entry.permission}'")
            
        # Check simulation and draft_action which should be read-only in the registry
        if required_perm in ["scenario.run", "intervention.draft"] and entry.permission != "read-only":
            raise ValueError(f"Policy Integrity Error: Tool '{tool_name}' requires read-only registry but registry says '{entry.permission}'")
            
        # Check write alignment
        if required_perm in ["watchlist.propose", "watchlist.approve", "watchlist.reject"] and entry.permission != "write":
            raise ValueError(f"Policy Integrity Error: Tool '{tool_name}' requires write registry but registry says '{entry.permission}'")

    # Set globals
    _ROLE_PERMISSIONS = {role: data.get("allowed_permissions", []) for role, data in role_perms.items()}
    _TOOL_PERMISSIONS = tool_perms

# Perform integrity check on module import
validate_policy_integrity()

def has_permission(role: str, permission: str) -> bool:
    """Checks if a role has the specified permission."""
    if role not in _ROLE_PERMISSIONS:
        return False
    return permission in _ROLE_PERMISSIONS[role]

def get_required_permission_for_tool(tool_name: str) -> str:
    """Returns the permission required to execute a tool."""
    if tool_name not in _TOOL_PERMISSIONS:
        raise ValueError(f"Tool '{tool_name}' is not configured in policies.yaml")
    return _TOOL_PERMISSIONS[tool_name]
