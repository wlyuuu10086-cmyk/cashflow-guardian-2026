from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class UserPrincipal(BaseModel):
    user_id: str
    role: str
    permissions: List[str] = Field(default_factory=list)

class SecurityContext(BaseModel):
    request_id: str
    session_id: str
    user_id: str
    role: str
    requested_tool: str
    business_id: Optional[str] = None
    as_of_month: Optional[str] = None
    timestamp: str
    source: str
    environment: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SafeError(BaseModel):
    error_code: str
    message: str
    retryable: bool
    invalid_fields: List[str] = Field(default_factory=list)
    policy_codes: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    request_id: str

class RedactionResult(BaseModel):
    redacted_value: Any
    redacted_keys: List[str] = Field(default_factory=list)
    redacted_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)

class InjectionAssessment(BaseModel):
    detected: bool
    severity: str
    matched_patterns: List[str] = Field(default_factory=list)
    policy_codes: List[str] = Field(default_factory=list)
    sanitized_text: str
    block_recommended: bool
