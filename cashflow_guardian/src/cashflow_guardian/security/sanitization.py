import html

def escape_xml_text(text: str) -> str:
    """Escapes XML/HTML special characters (&, <, >, \", ') to prevent tag injection."""
    return html.escape(text)

def sanitize_memo(memo: str) -> str:
    """Sanitizes transaction memo text non-destructively.
    
    Legitimate financial text may contain words like 'ignore', 'override', etc.
    We do NOT remove these words from the trusted data. We simply escape special characters
    and enforce a reasonable maximum length (e.g. 200 characters) at the boundary.
    """
    if not memo:
        return ""
    # 1. Escape special characters to prevent injection
    escaped = escape_xml_text(memo)
    # 2. Enforce length boundary (e.g. 200 characters for presentation)
    if len(escaped) > 200:
        escaped = escaped[:197] + "..."
    return escaped

def wrap_in_xml_tags(text: str, tag: str = "memo") -> str:
    """Wraps the text in XML tags for presentation to the Agent.
    
    IMPORTANT: This is strictly a presentation boundary to separate data from instructions
    for the LLM. It is NOT a security boundary for authorization or policy enforcement.
    We escape special characters first to prevent closing tag breakout (e.g. </memo>).
    """
    # 1. Clean the tag name itself to prevent tag-name injection
    tag_clean = "".join(c for c in tag if c.isalnum())
    # 2. Escape the inner text fully
    escaped_text = escape_xml_text(text)
    # 3. Double-check and replace any remaining literal closing tags just in case
    closing_tag = f"</{tag_clean}>"
    if closing_tag in escaped_text:
        escaped_text = escaped_text.replace(closing_tag, f"&lt;/{tag_clean}&gt;")
        
    return f"<{tag_clean}>{escaped_text}</{tag_clean}>"
