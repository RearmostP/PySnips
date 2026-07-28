from pathlib import Path

from core.tools.common.atomic_json import write_text_atomic


class SnippetContentStore:
    def read(self, content_file: str | Path) -> str:
        path = self._validated_path(content_file)
        if not path.is_file():
            raise FileNotFoundError(path)
        return path.read_text(encoding="utf-8")

    def write(self, content_file: str | Path, content: str) -> None:
        path = self._validated_path(content_file)
        if path.exists() and path.is_dir():
            raise IsADirectoryError(path)
        write_text_atomic(path, content or "")

    @staticmethod
    def _validated_path(content_file: str | Path) -> Path:
        if not str(content_file or "").strip():
            raise ValueError("חסר נתיב לקובץ התוכן של השליף.")
        return Path(content_file)
