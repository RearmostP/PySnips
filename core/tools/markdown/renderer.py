from html import escape
import re

import markdown
from pygments.formatters.html import HtmlFormatter
from pygments.token import String

from core.tools.markdown.settings import MarkdownRenderSettings


CODE_FONT_FAMILY = "JetBrains Mono"


class SnippetHtmlFormatter(HtmlFormatter):
    """Pygments formatter that renders Python docstrings one size smaller."""

    def __init__(self, **options):
        self.docstring_font_size = int(options.pop("docstring_font_size", 17))
        super().__init__(**options)

    def _create_stylesheet(self):
        super()._create_stylesheet()
        css_class = self.ttype2class.get(String.Doc)
        if not css_class or css_class not in self.class2style:
            return

        style, token_type, token_length = self.class2style[css_class]
        self.class2style[css_class] = (
            f"{style}; font-size: {self.docstring_font_size}px",
            token_type,
            token_length,
        )

    def _format_lines(self, tokensource):
        return super()._format_lines(
            _normalize_triple_quoted_tokens(tokensource)
        )


TRIPLE_QUOTED_STRING_PATTERN = re.compile(
    r"^(?:r|u|b|f|br|rb|fr|rf)?(?:\"\"\"|''')",
    re.IGNORECASE,
)


def _is_triple_quoted(value: str) -> bool:
    return bool(TRIPLE_QUOTED_STRING_PATTERN.match(value))


def _normalize_triple_quoted_tokens(tokensource):
    inside_triple_quoted_string = False
    for token_type, value in tokensource:
        delimiter_count = value.count('"""') + value.count("'''")
        is_triple_string_token = token_type in String and (
            inside_triple_quoted_string
            or _is_triple_quoted(value)
            or delimiter_count > 0
        )
        yield (
            String.Doc if is_triple_string_token else token_type,
            value,
        )
        if token_type in String and delimiter_count % 2:
            inside_triple_quoted_string = not inside_triple_quoted_string


class MarkdownRenderer:
    VERSION = 3

    def render(
        self,
        markdown_text: str,
        settings: MarkdownRenderSettings | None = None,
    ) -> str:
        settings = settings or MarkdownRenderSettings()
        docstring_font_size = max(
            1,
            settings.code_font_size + settings.docstring_font_size_offset,
        )
        body = markdown.markdown(
            markdown_text or "",
            extensions=[
                "fenced_code",
                "codehilite",
                "tables",
                "sane_lists",
                "nl2br",
            ],
            extension_configs={
                "codehilite": {
                    "guess_lang": False,
                    "noclasses": True,
                    "nobackground": True,
                    "pygments_style": "monokai",
                    "pygments_formatter": SnippetHtmlFormatter,
                    "docstring_font_size": docstring_font_size,
                    "use_pygments": True,
                }
            },
            output_format="html5",
        )
        return self._wrap_html(body, settings.code_font_size)

    def render_plain_text(
        self,
        text: str,
        settings: MarkdownRenderSettings | None = None,
    ) -> str:
        settings = settings or MarkdownRenderSettings()
        return self._wrap_html(
            f"<pre>{escape(text or '')}</pre>",
            settings.code_font_size,
        )

    @staticmethod
    def _wrap_html(body: str, code_font_size: int) -> str:
        return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{
    background: #181818;
    color: #d4d4d4;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    margin: 0;
    padding: 4px;
}}
h1, h2, h3, h4 {{ color: #ffffff; }}
a {{ color: #4da3ff; }}
pre {{
    color: #f8f8f2;
    font-family: "{CODE_FONT_FAMILY}", Consolas, monospace;
    font-size: {code_font_size}px;
    padding: 10px;
    white-space: pre-wrap;
}}
code, pre span, code span {{
    font-family: "{CODE_FONT_FAMILY}", Consolas, monospace;
}}
table {{ border-collapse: collapse; }}
th, td {{ border: 1px solid #3a3a3a; padding: 5px; }}
</style>
</head>
<body>{body}</body>
</html>
""".strip()
