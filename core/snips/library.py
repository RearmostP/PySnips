"""UI boundary for snippets, categories, media, trash and search.

Files are authoritative. No persistent registry or content database. One running
instance is supported; atomic writes protect individual files, not whole edits.
"""
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import uuid
from core.common.file_io import read_json, write_json_atomic, write_text_atomic
from core.common.paths import DATA_DIR, SNIPS_DIR, TRASH_DIR, SEARCH_INDEX_DIR
from core.snips.models import LibraryError, Snippet
from core.snips.search import SearchIndex

RESERVED = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}


def safe_name(value):
    if (not value or value.startswith('.') or value[-1:] in {' ', '.'}
            or re.search(r'[<>:"/\\|?*\x00-\x1f]', value)
            or value.split('.')[0].upper() in RESERVED or len(value) > 100):
        raise LibraryError('invalid_name')
    return value


def make_disk_name(title):
    value = re.sub(r'[^\w-]+', '_', title.strip()).strip('_')[:70].lower() or 'snippet'
    return 'snippet_' + value if value.upper() in RESERVED else value


def normalize_tags(tags):
    values = tags.split(',') if isinstance(tags, str) else tags
    return list(dict.fromkeys(tag.strip() for tag in values if tag.strip()))


class SnippetLibrary:
    def __init__(self, data_dir=DATA_DIR):
        self.root = Path(data_dir) / SNIPS_DIR.relative_to(DATA_DIR)
        self.trash = Path(data_dir) / TRASH_DIR.relative_to(DATA_DIR)
        self.category_trash = self.trash.parent / 'categories'
        self.index = SearchIndex(Path(data_dir) / SEARCH_INDEX_DIR.relative_to(DATA_DIR))
        self._safe(self.root, Path(data_dir))
        self._safe(self.trash, Path(data_dir))
        self.root.mkdir(parents=True, exist_ok=True)
        self.trash.mkdir(parents=True, exist_ok=True)
        self._safe(self.category_trash, self.trash.parent)
        self.category_trash.mkdir(exist_ok=True)
        self.categories_file = self.root / 'categories.json'
        self._safe(self.categories_file, self.root)
        if not self.categories_file.exists():
            write_json_atomic(self.categories_file, [
                {'name': name, 'pinned': False, 'deleted': False}
                for name in ('Python', 'PySide6')])
        self.categories()

    @staticmethod
    def _safe(path, root):
        if (any(p.is_symlink() or p.is_junction() for p in (path, *path.parents))
                or not path.resolve().is_relative_to(root.resolve())):
            raise LibraryError('invalid_data')

    def _category_records(self, *, migrate=True):
        """Validate everything before migrating or creating any directories."""
        try:
            self._safe(self.categories_file, self.root)
            records = read_json(self.categories_file)
            if not isinstance(records, list):
                raise LibraryError('invalid_data')
            legacy = bool(records) and all(isinstance(c, str) for c in records)
            if legacy:
                records = [{'name': c, 'pinned': False, 'deleted': False} for c in records]
            for record in records:
                if (not isinstance(record, dict) or set(record) != {'name', 'pinned', 'deleted'}
                        or not isinstance(record['name'], str)
                        or type(record['pinned']) is not bool or type(record['deleted']) is not bool
                        or record['deleted'] and record['pinned']):
                    raise LibraryError('invalid_data')
                safe_name(record['name'])
            if len({c['name'].casefold() for c in records}) != len(records):
                raise LibraryError('invalid_data')
        except (ValueError, OSError, LibraryError) as error:
            raise LibraryError('invalid_data') from error
        if legacy and migrate:
            write_json_atomic(self.categories_file, records)
        return records

    def categories(self):
        records = [c for c in self._category_records() if not c['deleted']]
        for c in records:
            self._safe(self.root / c['name'], self.root)
        for c in records:
            (self.root / c['name']).mkdir(exist_ok=True)
        return [c['name'] for c in sorted(records, key=lambda c: not c['pinned'])]

    def category_pinned(self, name):
        return self._category_record(self._category_records(), name, False)['pinned']

    @staticmethod
    def _category_record(records, name, deleted):
        for record in records:
            if record['name'] == name and record['deleted'] == deleted:
                return record
        raise LibraryError('deleted_category_missing' if deleted else 'category_missing')

    def pin_category(self, name, pinned):
        if type(pinned) is not bool:
            raise LibraryError('invalid_data')
        records = self._category_records()
        self._category_record(records, name, False)['pinned'] = pinned
        write_json_atomic(self.categories_file, records)

    def deleted_categories(self):
        return [c['name'] for c in self._category_records() if c['deleted']]

    def _safe_category_tree(self, directory, root):
        self._safe(directory, root)
        pending = [directory]
        while pending:
            parent = pending.pop()
            for path in parent.iterdir():
                self._safe(path, root)
                if path.is_dir():
                    pending.append(path)

    @staticmethod
    def _category_destination(target, error_key):
        if any(p.name.casefold() == target.name.casefold() for p in target.parent.iterdir()):
            raise LibraryError(error_key)

    def _move_category(self, name, *, deleted):
        records = self._category_records()
        record = self._category_record(records, name, not deleted)
        origin, destination = (self.root, self.category_trash) if deleted else (self.category_trash, self.root)
        source, target = origin / name, destination / name
        self._safe(source, origin)
        self._safe(target, destination)
        if not source.is_dir():
            raise LibraryError('category_missing' if deleted else 'deleted_category_missing')
        self._category_destination(target, 'category_trash_exists' if deleted else 'category_destination_exists')
        self._safe_category_tree(source, origin)
        if not deleted:
            # Validate restored metadata and UUIDs before making it searchable.
            seen = {s.id for s in self.list()}
            for directory in source.iterdir():
                if directory.is_dir() and not directory.name.startswith('.'):
                    snippet = self._read(directory, category_deleted=True)
                    if snippet.id in seen:
                        raise LibraryError('invalid_data')
                    seen.add(snippet.id)
        source.rename(target)
        try:
            record.update(deleted=deleted, pinned=False)
            write_json_atomic(self.categories_file, records)
        except OSError:
            try:
                target.rename(source)
            except OSError as error:
                raise LibraryError('category_rollback') from error
            raise
        self._refresh_index()

    def delete_category(self, name):
        self._move_category(name, deleted=True)

    def restore_category(self, name):
        self._move_category(name, deleted=False)

    def permanently_delete_category(self, name):
        records = self._category_records()
        record = self._category_record(records, name, True)
        directory = self.category_trash / name
        self._safe(directory, self.category_trash)
        if directory.exists():
            self._safe_category_tree(directory, self.category_trash)
            shutil.rmtree(directory)
        # A failed metadata write leaves a tombstone that can be retried safely.
        records.remove(record)
        write_json_atomic(self.categories_file, records)

    def add_category(self, name):
        name = safe_name(name.strip())
        records = self._category_records()
        if name.casefold() in {c['name'].casefold() for c in records}:
            raise LibraryError('name_exists')
        directory = self.root / name
        self._safe(directory, self.root)
        existed = directory.exists()
        directory.mkdir(exist_ok=True)
        try:
            write_json_atomic(self.categories_file, records + [
                {'name': name, 'pinned': False, 'deleted': False}])
        except OSError:
            if not existed:
                directory.rmdir()
            raise

    def _valid_category(self, category):
        if category not in self.categories():
            raise LibraryError('category_missing')

    def _read(self, directory, deleted=False, *, category_deleted=False):
        self._safe(directory, self.category_trash if category_deleted else self.trash if deleted else self.root)
        try:
            meta = read_json(directory / 'metadata.json')
            keys = {'id', 'title', 'disk_name', 'category', 'tags', 'created_at'}
            if not isinstance(meta, dict) or not keys <= meta.keys():
                raise LibraryError('invalid_data')
            if not all(isinstance(meta[k], str) and meta[k] for k in keys - {'tags'}):
                raise LibraryError('invalid_data')
            if not isinstance(meta['tags'], list) or not all(isinstance(t, str) for t in meta['tags']):
                raise LibraryError('invalid_data')
            uuid.UUID(meta['id'])
            safe_name(meta['disk_name'])
            safe_name(meta['category'])
            if not deleted and (meta['category'] != directory.parent.name or meta['disk_name'] != directory.name):
                raise LibraryError('invalid_data')
            for name in ('metadata.json', 'snippet.md', 'media'):
                self._safe(directory / name, directory)
            (directory / 'media').mkdir(exist_ok=True)
            return Snippet(**{k: meta[k] for k in keys}, content=(directory / 'snippet.md').read_text(encoding='utf-8'))
        except (OSError, ValueError) as error:
            raise LibraryError('invalid_data') from error

    def _entries(self, deleted=False):
        directories = self.trash.iterdir() if deleted else (d for c in self.categories() for d in (self.root / c).iterdir())
        seen = set()
        for d in directories:
            if d.is_dir() and not d.name.startswith('.'):
                s = self._read(d, deleted)
                if s.id in seen:
                    raise LibraryError('invalid_data')
                seen.add(s.id)
                yield d, s

    def list(self, category=None):
        if category is not None:
            self._valid_category(category)
        return sorted((s for _, s in self._entries() if category is None or s.category == category), key=lambda s: s.title.casefold())

    def _find(self, snippet_id, deleted=False):
        for d, s in self._entries(deleted):
            if s.id == snippet_id:
                return d, s
        raise LibraryError('not_found')

    def load(self, snippet_id):
        return self._find(snippet_id)[1]

    def _available(self, category, name):
        target = self.root / category / safe_name(name)
        if target.exists():
            raise LibraryError('name_exists')
        return target

    @staticmethod
    def _metadata(snippet):
        value = asdict(snippet)
        del value['content']
        return value

    def create(self, title, category, content, tags=(), disk_name=None, media=()):
        self._valid_category(category)
        if not title.strip() or not content.strip():
            raise LibraryError('required')
        name = safe_name(disk_name) if disk_name else make_disk_name(title)
        if disk_name is None:
            base, suffix = name, 2
            while (self.root / category / name).exists():
                name, suffix = f'{base}_{suffix}', suffix + 1
        target = self._available(category, name)
        s = Snippet(str(uuid.uuid4()), title.strip(), name, category, normalize_tags(tags),
                    datetime.now(timezone.utc).isoformat(timespec='seconds'), content)
        staging = target.parent / ('.new_' + s.id)
        try:
            (staging / 'media').mkdir(parents=True)
            for source in media:
                source = Path(source)
                destination = staging / 'media' / safe_name(source.name)
                if destination.exists():
                    raise LibraryError('name_exists')
                shutil.copyfile(source, destination)
            write_text_atomic(staging / 'snippet.md', content)
            write_json_atomic(staging / 'metadata.json', self._metadata(s))
            staging.rename(target)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
        self._refresh_index()
        return s

    def update(self, snippet_id, *, title=None, content=None, tags=None):
        directory, s = self._find(snippet_id)
        if (title is not None and not title.strip()) or (content is not None and not content.strip()):
            raise LibraryError('required')
        updated = replace(s, title=title.strip() if title is not None else s.title,
                          content=content if content is not None else s.content,
                          tags=normalize_tags(tags) if tags is not None else s.tags)
        if content is not None:
            write_text_atomic(directory / 'snippet.md', updated.content)
        write_json_atomic(directory / 'metadata.json', self._metadata(updated))
        self._refresh_index()
        return updated

    def _relocate(self, directory, s, category):
        self._valid_category(category)
        target = self._available(category, s.disk_name)
        updated = replace(s, category=category)
        directory.rename(target)
        try:
            write_json_atomic(target / 'metadata.json', self._metadata(updated))
        except OSError:
            target.rename(directory)
            raise
        self._refresh_index()
        return updated

    def move(self, snippet_id, category):
        directory, s = self._find(snippet_id)
        return s if category == s.category else self._relocate(directory, s, category)

    def add_media(self, snippet_id, source):
        directory, _ = self._find(snippet_id)
        source = Path(source)
        name = safe_name(source.name)
        target = directory / 'media' / name
        if target.exists():
            raise LibraryError('name_exists')
        shutil.copyfile(source, target)
        return 'media/' + name

    @staticmethod
    def media_reference(source):
        return 'media/' + safe_name(Path(source).name)

    def media_base(self, snippet_id):
        return self._find(snippet_id)[0]

    def delete(self, snippet_id):
        directory, s = self._find(snippet_id)
        target = self.trash / s.id
        if target.exists():
            raise LibraryError('name_exists')
        directory.rename(target)
        self._refresh_index()

    def deleted(self):
        return [s for _, s in self._entries(True)]

    def restore(self, snippet_id, category=None):
        directory, s = self._find(snippet_id, True)
        return self._relocate(directory, s, category or s.category)

    def permanently_delete(self, snippet_id):
        directory, _ = self._find(snippet_id, True)
        self._safe(directory, self.trash)
        shutil.rmtree(directory)

    def rebuild_search(self):
        self.index.rebuild(self.list())

    def _refresh_index(self):
        try:
            self.rebuild_search()
        except OSError:
            # Saved content is authoritative. The search fingerprint remains
            # old/missing, so later searches retry the rebuild before returning.
            pass

    def search(self, query, category=None):
        snippets = self.list()
        if category is not None:
            self._valid_category(category)
        if not query.strip():
            return [s for s in snippets if category is None or s.category == category]
        ids = self.index.ids(query.strip(), snippets)
        by_id = {s.id: s for s in snippets}
        return [by_id[i] for i in ids if i in by_id and (category is None or by_id[i].category == category)]
