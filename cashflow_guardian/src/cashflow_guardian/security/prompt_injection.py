import re
from typing import List
from .schemas import InjectionAssessment
from .sanitization import escape_xml_text

# Deterministic patterns to search for prompt injections
INJECTION_PATTERNS = [
    (r"ignore\s+(?:the\s+)?(?:previous|above|prior)?\s*instructions", "ignore previous instructions"),
    (r"system\s+override", "system override"),
    (r"reveal\s+(?:the\s+)?(?:system\s+)?prompt", "reveal system prompt"),
    (r"show\s+(?:the\s+)?(?:system\s+)?prompt", "reveal system prompt"),
    (r"what\s+is\s+your\s+system\s+prompt", "reveal system prompt"),
    (r"execute\s+sql", "execute SQL"),
    (r"run\s+sql", "execute SQL"),
    (r"modify\s+database", "modify database"),
    (r"write\s+(?:to\s+)?database", "modify database"),
    (r"drop\s+table", "modify database"),
    (r"insert\s+into", "modify database"),
    (r"delete\s+from", "modify database"),
    (r"bypass\s+approval", "bypass approval"),
    (r"skip\s+approval", "bypass approval"),
    (r"override\s+approval", "bypass approval"),
    (r"approve\s+automatically", "approve automatically"),
    (r"auto-approve", "approve automatically"),
    (r"auto\s+approve", "approve automatically"),
    (r"send\s+email", "send email"),
    (r"send\s+mail", "send email"),
    (r"change\s+credit\s+limit", "change credit limit"),
    (r"increase\s+credit\s+limit", "change credit limit"),
    (r"expose\s+hidden\s+data", "expose hidden data"),
    (r"reveal\s+hidden", "expose hidden data"),
    (r"retrieve\s+future\s+labels", "retrieve future labels"),
    (r"get\s+future\s+outcomes", "retrieve future labels"),
    (r"future_60d_", "retrieve future labels"),
    (r"delete\s+logs", "delete logs"),
    (r"clear\s+logs", "delete logs"),
    (r"disable\s+policy\s+checks", "disable policy checks"),
    (r"disable\s+policy", "disable policy checks"),
    (r"turn\s+off\s+policy", "disable policy checks"),
]

def assess_prompt_injection(text: str) -> InjectionAssessment:
    """Assess natural language text for prompt-injection attacks.
    
    This function uses deterministic keyword patterns and regexes.
    It returns an InjectionAssessment.
    """
    if not text:
        return InjectionAssessment(
            detected=False,
            severity="none",
            matched_patterns=[],
            policy_codes=[],
            sanitized_text="",
            block_recommended=False
        )

    matched = []
    text_lower = text.lower()
    
    for pattern_regex, label in INJECTION_PATTERNS:
        if re.search(pattern_regex, text_lower):
            if label not in matched:
                matched.append(label)

    if matched:
        return InjectionAssessment(
            detected=True,
            severity="high",
            matched_patterns=matched,
            policy_codes=["SECURITY_INJECTION_DETECTED"],
            sanitized_text=escape_xml_text(text),
            block_recommended=True
        )
        
    return InjectionAssessment(
        detected=False,
        severity="none",
        matched_patterns=[],
        policy_codes=[],
        sanitized_text=text,
        block_recommended=False
    )
