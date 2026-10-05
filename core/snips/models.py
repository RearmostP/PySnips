from dataclasses import dataclass


class LibraryError(Exception):
    """Expected data problem; its key is translated by the UI."""


@dataclass(frozen=True)
class Snippet:
    id: str
    title: str
    disk_name: str
    category: str
    tags: list[str]
    created_at: str
    content: str
