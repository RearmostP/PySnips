import json
import os
from pathlib import Path

from whoosh.fields import ID, KEYWORD, TEXT, Schema
from whoosh.index import create_in, open_dir
from whoosh.qparser import MultifieldParser, OrGroup, PrefixPlugin

from core.tools.common.app_paths import AppPaths


class SnippetSearchEngine:
    """Whoosh-based search engine for snippet metadata."""

    def __init__(self, index_dir: Path = AppPaths.SEARCH_INDEX_DIR):
        self.index_dir = index_dir
        self.schema = Schema(
            id=ID(stored=True, unique=True),
            title=TEXT(stored=True),
            category=ID(stored=True),
            tags=KEYWORD(stored=True, commas=True),
            content_file=ID(stored=True),
        )
        self.ix = self._get_or_create_index()
        self.query_parser = MultifieldParser(
            ["title", "tags"],
            schema=self.schema,
            group=OrGroup,
        )
        self.query_parser.add_plugin(PrefixPlugin())

    def _get_or_create_index(self):
        if not self.index_dir.exists():
            os.makedirs(self.index_dir)
            return create_in(self.index_dir, self.schema)

        try:
            index = open_dir(self.index_dir)
            if set(index.schema.names()) != set(self.schema.names()):
                return create_in(self.index_dir, self.schema)
            return index
        except Exception as e:
            print(f"Error opening Whoosh index: {e}. Recreating index.")
            return create_in(self.index_dir, self.schema)

    def rebuild_index_from_disk(self) -> None:
        snippets_metadata = self.load_all_snippets_metadata()
        self.ix = create_in(self.index_dir, self.schema)
        self.build_index(snippets_metadata)

    def load_all_snippets_metadata(self) -> list[dict]:
        snippets_metadata: list[dict] = []
        if not AppPaths.SNIPS_FILES.exists():
            return snippets_metadata

        for snips_json_path in AppPaths.SNIPS_FILES.glob("*/snips.json"):
            try:
                with open(snips_json_path, "r", encoding="utf-8") as f:
                    category_snippets = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue

            if not isinstance(category_snippets, list):
                continue

            snippets_metadata.extend(
                snippet_meta for snippet_meta in category_snippets
                if isinstance(snippet_meta, dict)
            )

        return snippets_metadata

    def build_index(self, snippets_metadata: list[dict]):
        writer = self.ix.writer()
        for snippet_meta in snippets_metadata:
            snippet_id = str(snippet_meta.get("id") or "")
            if not snippet_id:
                continue

            title = str(snippet_meta.get("title", ""))
            category = str(snippet_meta.get("category", ""))
            tags = ",".join(str(tag) for tag in snippet_meta.get("tags", []))
            content_file = str(snippet_meta.get("content_file", ""))

            writer.update_document(
                id=snippet_id,
                title=title,
                category=category,
                tags=tags,
                content_file=content_file,
            )
        writer.commit()

    def search(self, query_string: str) -> list[dict]:
        query_string = self._prepare_prefix_query(query_string)
        if not query_string:
            return []

        results = []
        with self.ix.searcher() as searcher:
            query = self.query_parser.parse(query_string)
            for hit in searcher.search(query):
                results.append(hit.fields())
        return results

    @staticmethod
    def _prepare_prefix_query(query_string: str) -> str:
        terms = []
        for term in (query_string or "").split():
            term = term.strip()
            if not term:
                continue
            if term.endswith("*") or ":" in term:
                terms.append(term)
            else:
                terms.append(f"{term}*")
        return " ".join(terms)


if __name__ == "__main__":
    search_engine = SnippetSearchEngine()
    search_engine.rebuild_index_from_disk()
