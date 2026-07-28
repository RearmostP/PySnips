import json
import os
import uuid
from pathlib import Path


def write_text_atomic(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write text without exposing a partially written destination file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")

    try:
        with open(temp_path, "w", encoding=encoding) as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, path)
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def write_json_atomic(path: Path, data: object) -> None:
    """Write JSON atomically using the shared text writer."""
    serialized = json.dumps(data, ensure_ascii=False, indent=2)
    write_text_atomic(path, serialized)
