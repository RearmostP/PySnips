from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from core.tools.markdown.cache import MarkdownCache
from core.tools.markdown.processor import prepare_markdown_for_render
from core.tools.markdown.renderer import MarkdownRenderer
from core.tools.markdown.settings import (
    MarkdownRenderSettings,
    load_markdown_render_settings,
)


@dataclass(frozen=True)
class MarkdownRenderResult:
    html: str
    warnings: list[str]
    repairs: list[str]
    loaded_from_cache: bool


class MarkdownService:
    def __init__(
        self,
        renderer: MarkdownRenderer | None = None,
        cache: MarkdownCache | None = None,
        settings: MarkdownRenderSettings | None = None,
        settings_loader: Callable[[], MarkdownRenderSettings] = load_markdown_render_settings,
    ):
        self.renderer = renderer or MarkdownRenderer()
        self.cache = cache or MarkdownCache()
        self._fixed_settings = settings
        self._settings_loader = settings_loader

    def load_or_render(self, snippet_id: str, source_path: str | Path) -> MarkdownRenderResult:
        source_path = Path(source_path)
        if not source_path.is_file():
            raise FileNotFoundError(source_path)

        settings = self._current_settings()
        render_fingerprint = settings.fingerprint(self.renderer.VERSION)
        cached = self.cache.load_if_valid(
            snippet_id=snippet_id,
            source_path=source_path,
            render_fingerprint=render_fingerprint,
        )
        if cached is not None:
            html, diagnostics, repairs = cached
            return MarkdownRenderResult(
                html=html,
                warnings=diagnostics,
                repairs=repairs,
                loaded_from_cache=True,
            )

        markdown_text = source_path.read_text(encoding="utf-8")
        preparation = prepare_markdown_for_render(markdown_text, settings)
        diagnostics = list(preparation.diagnostics)
        repairs = list(preparation.repairs)

        try:
            html = self.renderer.render(preparation.markdown, settings)
        except Exception as error:
            diagnostics.append(f"רינדור ה־Markdown נכשל: {error}")
            html = self.renderer.render_plain_text(markdown_text, settings)

        try:
            self.cache.save(
                snippet_id=snippet_id,
                source_path=source_path,
                render_fingerprint=render_fingerprint,
                html=html,
                diagnostics=diagnostics,
                repairs=repairs,
            )
        except OSError as error:
            diagnostics.append(f"שמירת ה־cache נכשלה: {error}")

        return MarkdownRenderResult(
            html=html,
            warnings=diagnostics,
            repairs=repairs,
            loaded_from_cache=False,
        )

    def invalidate(self, snippet_id: str) -> None:
        self.cache.invalidate(snippet_id)

    def invalidate_all(self) -> None:
        self.cache.invalidate_all()

    def _current_settings(self) -> MarkdownRenderSettings:
        return self._fixed_settings or self._settings_loader()
