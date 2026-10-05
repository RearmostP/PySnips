from io import BytesIO
from dataclasses import asdict
import hashlib
import json
from core.common.file_io import write_text_atomic
from whoosh.filedb.filestore import FileStorage
from whoosh.filedb.structfile import StructFile
from whoosh.analysis import RegexTokenizer, LowercaseFilter
from whoosh.fields import ID, TEXT, Schema
from whoosh.qparser import MultifieldParser, OrGroup
from whoosh.index import IndexError as WhooshIndexError
from pickle import UnpicklingError

SCHEMA = Schema(id=ID(stored=True, unique=True),
                title=TEXT(analyzer=RegexTokenizer() | LowercaseFilter()),
                tags=TEXT(analyzer=RegexTokenizer() | LowercaseFilter()),
                category=ID(), content=TEXT())


class _IndexStorage(FileStorage):
    """Avoid Whoosh 2.7's leaked Windows file handle when a TOC is corrupt."""
    def open_file(self, name, **kwargs):
        if name.endswith('.toc'):
            with open(self._fpath(name), 'rb') as stream:
                return StructFile(BytesIO(stream.read()), name=name, **kwargs)
        return super().open_file(name, **kwargs)


class SearchIndex:
    """Disposable derived data, with stable snippet IDs as document keys."""
    def __init__(self, directory):
        self.directory = directory

    @staticmethod
    def _digest(snippets):
        payload = json.dumps([asdict(s) for s in snippets], ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    def rebuild(self, snippets):
        self.directory.mkdir(parents=True, exist_ok=True)
        ix = _IndexStorage(str(self.directory), supports_mmap=False).create_index(SCHEMA)
        # Separate segment files close predictably on Windows/Python 3.14.
        with ix.writer(compound=False) as writer:
            for s in snippets:
                writer.update_document(id=s.id, title=s.title, tags=' '.join(s.tags),
                                       category=s.category, content=s.content)
        write_text_atomic(self.directory / 'source.sha256', self._digest(snippets))

    def ids(self, query, snippets):
        if not any(c in query for c in ':"()*?'):
            query = ' '.join(word + '*' for word in query.split())
        for attempt in range(2):
            try:
                if (self.directory / 'source.sha256').read_text(encoding='utf-8') != self._digest(snippets):
                    raise ValueError('Index no longer matches the source files')
                ix = _IndexStorage(str(self.directory), supports_mmap=False).open_index()
                if ix.schema != SCHEMA:
                    raise ValueError('Old index schema')
                parser = MultifieldParser(['title', 'tags', 'content'], ix.schema, group=OrGroup)
                with ix.searcher() as searcher:
                    return [hit['id'] for hit in searcher.search(parser.parse(query), limit=None)]
            except (OSError, WhooshIndexError, EOFError, ValueError, UnpicklingError):
                if attempt:
                    raise
            # Leave the exception handler before replacing files: Whoosh's
            # failed TOC reader may be kept alive by that exception traceback,
            # which locks the corrupt file on Windows until it is released.
            self.rebuild(snippets)
