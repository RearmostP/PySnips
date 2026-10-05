"""Atomic replacement of individual UTF-8 files, not multi-file transactions."""
import json
import os
import tempfile
from pathlib import Path


def write_text_atomic(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name, suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def write_json_atomic(path, value):
    write_text_atomic(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))
