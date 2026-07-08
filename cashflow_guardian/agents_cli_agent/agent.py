from __future__ import annotations

import datetime
import uuid

from cashflow_guardian.agent.agent import create_root_agent
from cashflow_guardian.security.schemas import SecurityContext

# Create a fixed local-evaluation SecurityContext entirely in code
# Role is set to "analyst", which is the verified least-privileged role
# that allows only read-only and draft-only early warning tools.
cli_security_context = SecurityContext(
    request_id="cli_req_" + uuid.uuid4().hex[:8],
    session_id="cli_session",
    user_id="cli_user",
    role="analyst",
    requested_tool="",
    timestamp=datetime.datetime.utcnow().isoformat() + "Z",
    source="cli",
    environment="local"
)

# Reuse the existing agent factory to instantiate the root agent with CLI context
root_agent = create_root_agent(cli_security_context)
