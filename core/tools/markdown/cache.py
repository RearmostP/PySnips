import hashlib
import json
from pathlib import Path

from core.tools.common.app_paths import AppPaths
from core.tools.common.atomic_json import write_json_atomic, write_text_atomic


class MarkdownCache:
    def __init__(self, cache_dir: Path = AppPaths.SNIPPET_HTML_CACHE_DIR):
        self.cache_dir = Path(cache_dir)

    def load_if_valid(
        self,
        snippet_id: str,
        source_path: Path,
        render_fingerprint: str,
    ) -> tuple[str, list[str], list[str]] | None:
        html_path, metadata_path = self._paths(snippet_id)
        if not html_path.is_file() or not metadata_path.is_file():
            return None

        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            source_stat = source_path.stat()
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(metadata, dict):
            return None

        expected_signature = {
            "source_path": str(source_path.resolve()),
            "source_mtime_ns": source_stat.st_mtime_ns,
            "source_size": source_stat.st_size,
            "render_fingerprint": render_fingerprint,
        }
        if any(metadata.get(key) != value for key, value in expected_signature.items()):
            return None

        diagnostics = metadata.get("diagnostics")
        repairs = metadata.get("repairs")
        if not isinstance(diagnostics, list):
            diagnostics = []
        if not isinstance(repairs, list):
            repairs = []

        try:
            return (
                html_path.read_text(encoding="utf-8"),
                [str(item) for item in diagnostics],
                [str(item) for item in repairs],
            )
        except OSError:
            return None

    def save(
        self,
        snippet_id: str,
        source_path: Path,
        render_fingerprint: str,
        html: str,
        diagnostics: list[str],
        repairs: list[str],
    ) -> None:
        source_stat = source_path.stat()
        html_path, metadata_path = self._paths(snippet_id)
        metadata = {
            "source_path": str(source_path.resolve()),
            "source_mtime_ns": source_stat.st_mtime_ns,
            "source_size": source_stat.st_size,
            "render_fingerprint": render_fingerprint,
            "diagnostics": list(diagnostics),
            "repairs": list(repairs),
        }
        write_text_atomic(html_path, html)
        write_json_atomic(metadata_path, metadata)

    def invalidate(self, snippet_id: str) -> None:
        for path in self._paths(snippet_id):
            try:
                path.unlink()
            except (FileNotFoundError, OSError):
                pass

    def invalidate_all(self) -> None:
        if not self.cache_dir.exists():
            return
        for path in self.cache_dir.glob("*"):
            if not path.is_file():
                continue
            try:
                path.unlink()
            except OSError:
                pass

    def _paths(self, snippet_id: str) -> tuple[Path, Path]:
        cache_key = hashlib.sha256(str(snippet_id).encode("utf-8")).hexdigest()
        return (
            self.cache_dir / f"{cache_key}.html",
            self.cache_dir / f"{cache_key}.meta.json",
        )
