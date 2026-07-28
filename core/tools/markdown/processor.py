from dataclasses import dataclass
from html import escape

from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

from core.tools.markdown.renderer import CODE_FONT_FAMILY
from core.tools.markdown.settings import MarkdownRenderSettings
from core.tools.markdown.validator import FENCE_PATTERN, extract_fence_language


@dataclass(frozen=True)
class MarkdownPreparationResult:
    markdown: str
    diagnostics: list[str]
    repairs: list[str]


def prepare_markdown_for_render(
    markdown_text: str,
    settings: MarkdownRenderSettings,
) -> MarkdownPreparationResult:
    """Normalize safe cases and render recoverable fence problems inline."""
    lines = (markdown_text or "").splitlines()
    output: list[str] = []
    diagnostics: list[str] = []
    repairs: list[str] = []
    index = 0

    while index < len(lines):
        opening_line = lines[index]
        opening_match = FENCE_PATTERN.match(opening_line)
        if not opening_match:
            output.append(opening_line)
            index += 1
            continue

        fence = opening_match.group("fence")
        info = opening_match.group("info").strip()
        closing_index = _find_closing_fence(lines, index + 1, fence)

        if closing_index is None:
            diagnostics.append(
                f"שורה {index + 1}: בלוק הקוד לא נסגר; הוא הוצג כטקסט רגיל."
            )
            content_lines = lines[index + 1:]
            if settings.unclosed_fence_behavior == "auto_close":
                repairs.append(
                    f"שורה {index + 1}: נוסף fence סוגר זמני לצורך הרינדור."
                )
                block = _prepare_closed_block(
                    fence=fence,
                    info=info,
                    content_lines=content_lines,
                    closing_fence=fence,
                    line_number=index + 1,
                    settings=settings,
                    diagnostics=diagnostics,
                    repairs=repairs,
                )
                output.extend(block)
            elif settings.unclosed_fence_behavior == "plain_text":
                output.append(_plain_unclosed_block(fence, info, content_lines))
            else:
                output.append(_red_marker_unclosed_block(fence, info, content_lines))
            break

        content_lines = lines[index + 1:closing_index]
        output.extend(
            _prepare_closed_block(
                fence=fence,
                info=info,
                content_lines=content_lines,
                closing_fence=lines[closing_index],
                line_number=index + 1,
                settings=settings,
                diagnostics=diagnostics,
                repairs=repairs,
            )
        )
        index = closing_index + 1

    return MarkdownPreparationResult(
        markdown="\n".join(output),
        diagnostics=diagnostics,
        repairs=repairs,
    )


def _prepare_closed_block(
    fence: str,
    info: str,
    content_lines: list[str],
    closing_fence: str,
    line_number: int,
    settings: MarkdownRenderSettings,
    diagnostics: list[str],
    repairs: list[str],
) -> list[str]:
    language = extract_fence_language(info)
    canonical_language = settings.language_aliases.get(language, language)

    if language and canonical_language != language:
        repairs.append(
            f"שורה {line_number}: שם השפה '{language}' נורמל ל־'{canonical_language}'."
        )

    if not language:
        diagnostics.append(
            f"שורה {line_number}: בלוק הקוד אינו מגדיר שפת תחביר."
        )
        if settings.missing_language_behavior == "highlight_red":
            return [
                _diagnostic_code_block(
                    "שפה לא הוגדרה",
                    content_lines,
                    settings.code_font_size,
                )
            ]
        return [fence, *content_lines, closing_fence]

    if not _is_known_language(canonical_language):
        diagnostics.append(
            f"שורה {line_number}: שפת התחביר '{language}' אינה מוכרת."
        )
        if settings.invalid_language_behavior == "highlight_red":
            return [
                _diagnostic_code_block(
                    language,
                    content_lines,
                    settings.code_font_size,
                )
            ]
        return [fence, *content_lines, closing_fence]

    trailing_info = info.split(maxsplit=1)
    suffix = f" {trailing_info[1]}" if len(trailing_info) > 1 else ""
    normalized_opening = f"{fence}{canonical_language}{suffix}"
    return [normalized_opening, *content_lines, closing_fence]


def _find_closing_fence(
    lines: list[str],
    start_index: int,
    opening_fence: str,
) -> int | None:
    for index in range(start_index, len(lines)):
        match = FENCE_PATTERN.match(lines[index])
        if not match:
            continue
        candidate = match.group("fence")
        info = match.group("info").strip()
        if (
            candidate[0] == opening_fence[0]
            and len(candidate) >= len(opening_fence)
            and not info
        ):
            return index
    return None


def _is_known_language(language: str) -> bool:
    try:
        get_lexer_by_name(language)
        return True
    except ClassNotFound:
        return False


def _diagnostic_code_block(
    label: str,
    content_lines: list[str],
    code_font_size: int,
) -> str:
    escaped_content = escape("\n".join(content_lines))
    return (
        '<div style="margin:6px 0;">'
        f'<div style="color:#ff5c5c;font-weight:700;">{escape(label)}</div>'
        '<pre style="color:#f8f8f2;'
        f'font-family:{CODE_FONT_FAMILY},Consolas,monospace;'
        f'font-size:{code_font_size}px;padding:10px;">'
        f"{escaped_content}</pre></div>"
    )


def _red_marker_unclosed_block(
    fence: str,
    info: str,
    content_lines: list[str],
) -> str:
    marker = f'<span style="color:#ff5c5c;font-weight:700;">{escape(fence)}</span>'
    opening = marker + escape(info)
    content = "<br>".join(escape(line) for line in content_lines)
    separator = "<br>" if content else ""
    return (
        '<div style="white-space:normal;font-family:Segoe UI,Arial,sans-serif;">'
        f"{opening}{separator}{content}</div>"
    )


def _plain_unclosed_block(
    fence: str,
    info: str,
    content_lines: list[str],
) -> str:
    text = "\n".join([f"{fence}{info}", *content_lines])
    return (
        '<div style="white-space:pre-wrap;font-family:Segoe UI,Arial,sans-serif;">'
        f"{escape(text)}</div>"
    )
