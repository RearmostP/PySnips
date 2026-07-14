def sanitize_snippet_name(name: str) -> str:
    safe = "".join(c for c in (name or "") if c.isalnum() or c in (" ", "_", "-")).strip()
    if not safe:
        return "uncategorized"
    return safe.replace(" ", "_")
