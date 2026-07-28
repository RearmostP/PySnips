import hashlib
import json
from dataclasses import asdict, dataclass, field

from core.tools.common.app_paths import AppPaths


LANGUAGE_ALIASES = {
    "py": "python",
    "python3": "python",
    "js": "javascript",
    "ts": "typescript",
    "sh": "bash",
    "shell": "bash",
    "ps": "powershell",
    "ps1": "powershell",
    "yml": "yaml",
    "c++": "cpp",
    "cs": "csharp",
}

INVALID_LANGUAGE_BEHAVIORS = {"highlight_red", "plain_code"}
MISSING_LANGUAGE_BEHAVIORS = {"highlight_red", "plain_code"}
UNCLOSED_FENCE_BEHAVIORS = {"plain_red_marker", "plain_text", "auto_close"}


@dataclass
class MarkdownRenderSettings:
    invalid_language_behavior: str = "highlight_red"
    missing_language_behavior: str = "highlight_red"
    unclosed_fence_behavior: str = "plain_red_marker"
    code_font_size: int = 12
    docstring_font_size_offset: int = -1
    language_aliases: dict[str, str] = field(
        default_factory=lambda: dict(LANGUAGE_ALIASES)
    )

    def fingerprint(self, renderer_version: int) -> str:
        payload = {
            "renderer_version": renderer_version,
            "settings": asdict(self),
        }
        serialized = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


DEFAULT_MARKDOWN_SETTINGS = asdict(MarkdownRenderSettings())


def load_markdown_render_settings() -> MarkdownRenderSettings:
    try:
        raw_settings = json.loads(
            AppPaths.SNIPS_SETTINGS_JSON.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        raw_settings = {}

    markdown_settings = (
        raw_settings.get("markdown")
        if isinstance(raw_settings, dict)
        else None
    )
    return normalize_markdown_render_settings(markdown_settings)


def normalize_markdown_render_settings(raw_settings: object) -> MarkdownRenderSettings:
    raw = raw_settings if isinstance(raw_settings, dict) else {}
    aliases = raw.get("language_aliases")
    merged_aliases = dict(LANGUAGE_ALIASES)
    if isinstance(aliases, dict):
        merged_aliases.update(aliases)

    normalized_aliases = {
        str(alias).strip().lower(): str(language).strip().lower()
        for alias, language in merged_aliases.items()
        if str(alias).strip() and str(language).strip()
    }

    return MarkdownRenderSettings(
        invalid_language_behavior=_normalize_choice(
            raw.get("invalid_language_behavior"),
            INVALID_LANGUAGE_BEHAVIORS,
            "highlight_red",
        ),
        missing_language_behavior=_normalize_choice(
            raw.get("missing_language_behavior"),
            MISSING_LANGUAGE_BEHAVIORS,
            "highlight_red",
        ),
        unclosed_fence_behavior=_normalize_choice(
            raw.get("unclosed_fence_behavior"),
            UNCLOSED_FENCE_BEHAVIORS,
            "plain_red_marker",
        ),
        code_font_size=_normalize_integer(
            raw.get("code_font_size"),
            default=12,
            minimum=8,
            maximum=32,
        ),
        docstring_font_size_offset=_normalize_integer(
            raw.get("docstring_font_size_offset"),
            default=-1,
            minimum=-6,
            maximum=0,
        ),
        language_aliases=normalized_aliases,
    )


def _normalize_choice(value: object, allowed: set[str], default: str) -> str:
    normalized = str(value or "").strip()
    return normalized if normalized in allowed else default


def _normalize_integer(
    value: object,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        normalized = default
    return max(minimum, min(normalized, maximum))
