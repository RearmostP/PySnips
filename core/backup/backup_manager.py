"""Portable snapshots with strict validation and same-volume rollback.

The caller must exclude concurrent library edits (the modal UI does this).
Rollback protects caught failures, not process termination or power loss.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import zipfile
import zlib

from core.common.paths import DATA_DIR, SNIPS_DIR, TRASH_DIR
from core.common.version import read_version, version_parts
from core.snips.library import SnippetLibrary, safe_name
from core.snips.models import LibraryError


class BackupError(Exception):
    """A localization key, never raw data or provider responses."""


def check_path(path):
    path = Path(path)
    # Check ancestors too: a safe leaf beneath a junction is still unsafe.
    for item in (path, *path.parents):
        if item.is_symlink() or getattr(item, 'is_junction', lambda: False)():
            raise BackupError('unsafe')
        if item.exists() and getattr(item.lstat(), 'st_file_attributes', 0) & 0x400:
            raise BackupError('unsafe')


class BackupManager:
    MAX_BYTES = 10 * 1024 ** 3
    MAX_ENTRIES = 100000

    def __init__(self, data_dir=DATA_DIR):
        self.data_dir = Path(data_dir)
        self.snips = self.data_dir / SNIPS_DIR.relative_to(DATA_DIR)
        self.trash = self.data_dir / TRASH_DIR.relative_to(DATA_DIR)

    def create(self, destination, *, version=None):
        destination = Path(destination)
        now = datetime.now(timezone.utc)
        name = 'PySnips-Backup-' + now.strftime('%Y-%m-%dT%H-%M-%S-%fZ') + '.zip'
        try:
            check_path(destination)
            for root in (self.snips, self.trash):
                check_path(root)
                if not root.is_dir() or destination.resolve().is_relative_to(root.resolve()):
                    raise BackupError('unsafe')
            destination.mkdir(parents=True, exist_ok=True)
            final = destination / name
            with tempfile.TemporaryDirectory(prefix='.backup-', dir=destination) as temporary:
                archive = Path(temporary) / name
                with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
                    output.writestr('manifest.json', json.dumps({
                        'format_version': 1,
                        'created_at': now.isoformat().replace('+00:00', 'Z'),
                        'pysnips_version': version or read_version(),
                    }, ensure_ascii=False))
                    for root, prefix in ((self.snips, 'snips'), (self.trash, 'trash/snips')):
                        output.writestr(prefix + '/', b'')
                        self._archive_tree(output, root, prefix)
                # Validate our finished snapshot too; never publish corrupt input.
                self.validate(archive)
                os.replace(archive, final)
            return final
        except BackupError:
            raise
        except (OSError, ValueError, zipfile.BadZipFile, LibraryError) as error:
            raise BackupError('local') from error

    def _archive_tree(self, output, root, prefix):
        for path in sorted(root.iterdir()):
            check_path(path)
            # Atomic writes and new snippet transactions use hidden names.
            if path.name.startswith('.'):
                continue
            safe_name(path.name)
            name = prefix + '/' + path.name
            if path.is_dir():
                output.writestr(name + '/', b'')
                self._archive_tree(output, path, name)
            elif path.is_file() and stat.S_ISREG(path.stat().st_mode):
                output.write(path, name)
            else:
                raise BackupError('unsafe')

    @staticmethod
    def _member(info):
        name = info.filename
        parts = name.rstrip('/').split('/')
        if (not name or info.orig_filename != name or '\\' in name or any(p in ('', '.', '..') for p in parts)
                or name.startswith('/') or ':' in name or '\x00' in name):
            raise BackupError('unsafe')
        for part in parts:
            try:
                safe_name(part)
            except LibraryError as error:
                raise BackupError('unsafe') from error
        mode = info.external_attr >> 16
        kind = stat.S_IFMT(mode)
        if kind not in (0, stat.S_IFREG, stat.S_IFDIR) or info.flag_bits & 1 or info.external_attr & 0x400:
            raise BackupError('unsafe')
        if kind == stat.S_IFDIR and not info.is_dir():
            raise BackupError('unsafe')
        if not (name == 'manifest.json' or parts[0] == 'snips'
                or parts == ['trash'] and info.is_dir()
                or parts[:2] == ['trash', 'snips']):
            raise BackupError('layout')
        return parts

    def _extract_validate(self, archive, staging):
        try:
            check_path(archive)
            with zipfile.ZipFile(archive) as source:
                entries = source.infolist()
                if len(entries) > self.MAX_ENTRIES or sum(i.file_size for i in entries) > self.MAX_BYTES:
                    raise BackupError('limits')
                names = set()
                for info in entries:
                    parts = self._member(info)
                    key = '/'.join(parts).casefold()
                    if key in names:
                        raise BackupError('unsafe')
                    names.add(key)
                if 'manifest.json' not in names:
                    raise BackupError('manifest')
                if source.getinfo('manifest.json').file_size > 65536:
                    raise BackupError('manifest')
                try:
                    manifest = json.loads(source.read('manifest.json').decode('utf-8'))
                    if not isinstance(manifest, dict):
                        raise ValueError()
                    if type(manifest.get('format_version')) is not int:
                        raise ValueError()
                    if manifest['format_version'] != 1:
                        raise BackupError('format')
                    created = datetime.fromisoformat(manifest['created_at'].replace('Z', '+00:00'))
                    if created.utcoffset() != timezone.utc.utcoffset(created):
                        raise ValueError()
                    version_parts(manifest['pysnips_version'])
                except (ValueError, KeyError, TypeError, AttributeError) as error:
                    raise BackupError('manifest') from error
                for info in entries:
                    target = staging.joinpath(*self._member(info))
                    if info.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with source.open(info) as incoming, target.open('xb') as outgoing:
                            shutil.copyfileobj(incoming, outgoing)
            self._validate_library(staging)
            return manifest
        except BackupError:
            raise
        except (zipfile.BadZipFile, EOFError, RuntimeError, ValueError, NotImplementedError, zlib.error) as error:
            raise BackupError('zip') from error
        except OSError as error:
            raise BackupError('local') from error

    @staticmethod
    def _validate_library(staging):
        root, trash = staging / 'snips', staging / 'trash/snips'
        if not (root / 'categories.json').is_file():
            raise BackupError('categories')
        if not trash.is_dir():
            raise BackupError('layout')
        try:
            # Use existing readers without their constructor's directory creation.
            library = SnippetLibrary.__new__(SnippetLibrary)
            library.root, library.trash = root, trash
            library.categories_file = root / 'categories.json'
            categories = json.loads(library.categories_file.read_text(encoding='utf-8-sig'))
            if not isinstance(categories, list) or any(not isinstance(c, str) for c in categories):
                raise LibraryError('invalid_data')
            if any(not (root / safe_name(c)).is_dir() for c in categories):
                raise LibraryError('invalid_data')
            # Existing library readers ignore unlisted categories. Preserve and
            # validate those directories too rather than dropping local data.
            category_dirs = []
            for directory in root.iterdir():
                if directory.name != 'categories.json':
                    safe_name(directory.name)
                    if not directory.is_dir():
                        raise LibraryError('invalid_data')
                    category_dirs.append(directory)
            ids = set()
            for parent, deleted in [*((directory, False) for directory in category_dirs), (trash, True)]:
                for directory in parent.iterdir():
                    if not directory.is_dir() or {p.name for p in directory.iterdir()} != {'metadata.json', 'snippet.md', 'media'}:
                        raise LibraryError('invalid_data')
                    if not (directory / 'media').is_dir():
                        raise LibraryError('invalid_data')
                    snippet = library._read(directory, deleted)
                    if snippet.id in ids:
                        raise LibraryError('invalid_data')
                    ids.add(snippet.id)
            library.list()
            library.deleted()
        except (LibraryError, ValueError, OSError, TypeError) as error:
            raise BackupError('metadata') from error

    def validate(self, archive):
        with tempfile.TemporaryDirectory(prefix='pysnips-validate-') as temporary:
            return self._extract_validate(Path(archive), Path(temporary))

    def restore(self, archive, *, rebuild=None, status=lambda key: None):
        check_path(self.snips)
        check_path(self.trash)
        user = self.snips.parent
        try:
            user.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='.restore-', dir=user, ignore_cleanup_errors=True) as temporary:
                stage = Path(temporary) / 'snapshot'
                stage.mkdir()
                status('validating')
                self._extract_validate(Path(archive), stage)
                status('restoring')
                moved, installed = [], []
                try:
                    for live, fresh, label in ((self.snips, stage / 'snips', 'snips'),
                                               (self.trash, stage / 'trash/snips', 'trash')):
                        live.parent.mkdir(parents=True, exist_ok=True)
                        old = Path(temporary) / ('old-' + label)
                        if live.exists():
                            live.rename(old)
                            moved.append((old, live))
                        fresh.rename(live)
                        installed.append(live)
                    status('index')
                    (rebuild or SnippetLibrary(self.data_dir).rebuild_search)()
                except Exception as error:
                    try:
                        for live in reversed(installed):
                            shutil.rmtree(live)
                        for old, live in reversed(moved):
                            old.rename(live)
                    except OSError as rollback_error:
                        # Keep recovery copies outside TemporaryDirectory cleanup.
                        recovery = user / ('backup-recovery-' + Path(temporary).name)
                        Path(temporary).rename(recovery)
                        raise BackupError('rollback') from rollback_error
                    raise BackupError('restore') from error
        except BackupError:
            raise
        except OSError as error:
            raise BackupError('local') from error
