import re

from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound


FENCE_PATTERN = re.compile(r"^[ \t]{0,3}(?P<fence>`{3,}|~{3,})(?P<info>.*)$")


def validate_markdown_syntax(markdown_text: str) -> list[str]:
    """Return non-fatal warnings for fenced code block syntax."""
    warnings: list[str] = []
    opening_fence: tuple[str, int, str] | None = None

    for line_number, line in enumerate((markdown_text or "").splitlines(), start=1):
        match = FENCE_PATTERN.match(line)
        if not match:
            continue

        fence = match.group("fence")
        info = match.group("info").strip()

        if opening_fence is not None:
            opening_marker, opening_line, _ = opening_fence
            is_closing_fence = (
                fence[0] == opening_marker[0]
                and len(fence) >= len(opening_marker)
                and not info
            )
            if is_closing_fence:
                opening_fence = None
            continue

        language = extract_fence_language(info)
        opening_fence = (fence, line_number, language)
        if not language:
            warnings.append(
                f"שורה {line_number}: בלוק הקוד אינו מגדיר שפה; הקוד יוצג ללא צביעת תחביר."
            )
            continue

        try:
            get_lexer_by_name(language)
        except ClassNotFound:
            warnings.append(
                f"שורה {line_number}: שפת התחביר '{language}' אינה מוכרת; הקוד יוצג ללא צביעה."
            )

    if opening_fence is not None:
        _, opening_line, _ = opening_fence
        warnings.append(
            f"שורה {opening_line}: בלוק הקוד לא נסגר באמצעות fence מתאים."
        )

    return warnings


def extract_fence_language(info: str) -> str:
    if not info:
        return ""

    first_token = info.split(maxsplit=1)[0].strip()
    if first_token.startswith("{.") and first_token.endswith("}"):
        first_token = first_token[2:-1]
    return first_token.lstrip(".").lower()
