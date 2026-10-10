import json
from pathlib import Path
import shutil
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from core.backup.backup_manager import BackupManager, BackupError
from core.snips.library import SnippetLibrary


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.data = self.base / 'data'
        self.library = SnippetLibrary(self.data)
        self.manager = BackupManager(self.data)
        self.library.add_category('עברית')
        self.snippet = self.library.create('שלום', 'עברית', 'שלום\r\n```python\nprint(1)\n```', disk_name='דוגמה')
        self.directory = self.library.media_base(self.snippet.id)
        self.media = bytes(range(256))
        (self.directory / 'media' / 'תמונה.bin').write_bytes(self.media)
        self.deleted = self.library.create('Deleted', 'Python', 'deleted content')
        self.library.delete(self.deleted.id)
        self.settings = self.data / 'user_data/settings/settings.json'
        self.settings.parent.mkdir()
        self.settings.write_bytes(b'settings must stay')
        (self.directory / '.metadata.json-test.tmp').write_text('partial')

    def backup(self):
        return self.manager.create(self.base / 'exports')

    def rewrite(self, archive, *, remove=(), replace=None, extra=()):
        target = self.base / 'modified.zip'
        with zipfile.ZipFile(archive) as source, zipfile.ZipFile(target, 'w') as output:
            for entry in source.infolist():
                if entry.filename not in remove:
                    output.writestr(entry, (replace or {}).get(entry.filename, source.read(entry)))
            for name, content in extra:
                output.writestr(name, content)
        return target

    def snapshot(self):
        return {p.relative_to(self.data).as_posix(): p.read_bytes()
                for p in self.data.rglob('*') if p.is_file() and 'cache' not in p.parts}

    def test_archive_exact_content_and_exclusions(self):
        archive = self.backup()
        with zipfile.ZipFile(archive) as source:
            names = source.namelist()
            self.assertIn('snips/', names)
            self.assertIn('trash/snips/', names)
            self.assertIn('manifest.json', names)
            self.assertIn('snips/categories.json', names)
            self.assertFalse(any('settings' in n or 'cache' in n or 'search_index' in n or '.tmp' in n for n in names))
            prefix = 'snips/עברית/דוגמה/'
            for name in ('metadata.json', 'snippet.md', 'media/תמונה.bin'):
                self.assertEqual(source.read(prefix + name), (self.directory / name).read_bytes())
            manifest = json.loads(source.read('manifest.json'))
            self.assertEqual(manifest['format_version'], 1)
            self.assertEqual(manifest['pysnips_version'], '0.2.1')
            self.assertNotIn('settings', manifest)

    def test_restore_replaces_library_and_trash_preserves_settings_rebuilds_index(self):
        archive = self.backup()
        self.library.permanently_delete(self.deleted.id)
        extra = self.library.create('Extra', 'Python', 'extra')
        self.library.update(self.snippet.id, content='changed')
        statuses = []
        with patch.object(self.library, 'rebuild_search', wraps=self.library.rebuild_search) as rebuild:
            self.manager.restore(archive, rebuild=rebuild, status=statuses.append)
            rebuild.assert_called_once()
        self.assertEqual([s.id for s in self.library.list()], [self.snippet.id])
        self.assertNotIn(extra.id, [s.id for s in self.library.list()])
        self.assertEqual(self.library.deleted(), [self.deleted])
        self.assertEqual(self.library.load(self.snippet.id).content, self.snippet.content.replace('\r\n', '\n'))
        self.assertEqual((self.directory / 'media/תמונה.bin').read_bytes(), self.media)
        self.assertEqual(self.settings.read_bytes(), b'settings must stay')
        self.assertEqual(statuses, ['validating', 'restoring', 'index'])
        self.assertEqual(self.library.search('שלום')[0].id, self.snippet.id)

    def test_empty_trash_valid(self):
        self.library.permanently_delete(self.deleted.id)
        archive = self.backup()
        self.manager.restore(archive)
        self.assertEqual(self.library.deleted(), [])

    def test_unlisted_category_preserved_without_changing_categories(self):
        from core.common.file_io import write_json_atomic
        orphan = self.library.root / 'Unlisted'
        shutil.copytree(self.directory, orphan / self.directory.name)
        metadata = json.loads((orphan / self.directory.name / 'metadata.json').read_text(encoding='utf-8'))
        import uuid
        metadata['id'], metadata['category'] = str(uuid.uuid4()), 'Unlisted'
        write_json_atomic(orphan / self.directory.name / 'metadata.json', metadata)
        categories = self.library.categories_file.read_bytes()
        archive = self.backup()
        shutil.rmtree(orphan)
        self.manager.restore(archive)
        self.assertEqual(self.library.categories_file.read_bytes(), categories)
        self.assertEqual((orphan / self.directory.name / 'media/תמונה.bin').read_bytes(), self.media)

    def test_failed_creation_publishes_no_partial_archive(self):
        with patch('core.backup.backup_manager.zipfile.ZipFile.write', side_effect=OSError('disk full')):
            with self.assertRaises(BackupError):
                self.backup()
        self.assertEqual(list((self.base / 'exports').iterdir()), [])

    def test_bad_archives_leave_live_data_unchanged(self):
        archive = self.backup()
        manifest = {'format_version': 99, 'created_at': '2026-10-10T00:00:00Z', 'pysnips_version': '0.2.1'}
        cases = [
            {'remove': ['manifest.json']},
            {'replace': {'manifest.json': b'not json'}},
            {'replace': {'manifest.json': json.dumps(manifest)}},
            {'replace': {'manifest.json': '[]'}},
            {'remove': ['snips/categories.json']},
            {'replace': {'snips/עברית/דוגמה/metadata.json': '{}'}},
            {'extra': [('../outside.txt', 'unsafe')]},
            {'extra': [('/absolute.txt', 'unsafe')]},
            {'extra': [('C:/absolute.txt', 'unsafe')]},
            {'extra': [('snips\\outside.txt', 'unsafe')]},
            {'extra': [('settings/settings.json', 'unsafe')]},
            {'extra': [('SNIPS/categories.json', 'collision')]},
        ]
        original = self.snapshot()
        for case in cases:
            with self.subTest(case=case):
                changed = self.rewrite(archive, **case)
                with self.assertRaises(BackupError):
                    self.manager.restore(changed)
                self.assertEqual(self.snapshot(), original)

    def test_corrupt_zip(self):
        path = self.base / 'broken.zip'
        path.write_bytes(b'not a zip')
        with self.assertRaisesRegex(BackupError, 'zip'):
            self.manager.validate(path)

    def test_archive_symlink_rejected(self):
        info = zipfile.ZipInfo('snips/linked')
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        changed = self.rewrite(self.backup(), extra=[(info, '../outside')])
        with self.assertRaisesRegex(BackupError, 'unsafe'):
            self.manager.validate(changed)

    def test_symlink_or_junction_rejected_before_traversal(self):
        # Portable test for both Windows link kinds without Developer Mode.
        with patch.object(Path, 'is_symlink', return_value=True):
            with self.assertRaisesRegex(BackupError, 'unsafe'):
                self.backup()
        with patch.object(Path, 'is_junction', return_value=True):
            with self.assertRaisesRegex(BackupError, 'unsafe'):
                self.backup()

    def test_real_junction_rejected(self):
        import os
        import subprocess
        if os.name != 'nt':
            self.skipTest('Windows junction test')
        external = self.base / 'external'
        external.mkdir()
        link = self.directory / 'media/linked'
        result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(external)], capture_output=True)
        if result.returncode:
            self.skipTest('Junction creation unavailable')
        try:
            with self.assertRaisesRegex(BackupError, 'unsafe'):
                self.backup()
        finally:
            link.rmdir()

    def test_install_failure_rolls_back_both_trees(self):
        archive = self.backup()
        original = self.snapshot()
        rename = Path.rename
        def fail(path, target):
            if path.as_posix().endswith('/snapshot/trash/snips'):
                raise OSError('replacement failed')
            return rename(path, target)
        with patch.object(Path, 'rename', fail):
            with self.assertRaisesRegex(BackupError, 'restore'):
                self.manager.restore(archive)
        self.assertEqual(self.snapshot(), original)

    def test_index_failure_rolls_back(self):
        archive = self.backup()
        original = self.snapshot()
        with self.assertRaisesRegex(BackupError, 'restore'):
            self.manager.restore(archive, rebuild=lambda: (_ for _ in ()).throw(OSError('index failed')))
        self.assertEqual(self.snapshot(), original)

    def test_rollback_failure_retains_recovery_copy(self):
        archive = self.backup()
        rename = Path.rename
        def fail(path, target):
            if path.name == 'old-snips':
                raise OSError('rollback failed')
            return rename(path, target)
        with patch.object(Path, 'rename', fail):
            with self.assertRaisesRegex(BackupError, 'rollback'):
                self.manager.restore(archive, rebuild=lambda: (_ for _ in ()).throw(OSError('index failed')))
        recovery = list((self.data / 'user_data').glob('backup-recovery-*'))
        self.assertEqual(len(recovery), 1)
        self.assertTrue((recovery[0] / 'old-snips/categories.json').is_file())
        self.assertTrue(self.library.trash.is_dir())  # Trash rollback already succeeded.

    def test_limits_and_duplicate_paths_rejected(self):
        archive = self.backup()
        with patch.object(self.manager, 'MAX_BYTES', 1):
            with self.assertRaisesRegex(BackupError, 'limits'):
                self.manager.validate(archive)
        changed = self.rewrite(archive, extra=[('snips/CATEGORIES.json', '[]')])
        with self.assertRaisesRegex(BackupError, 'unsafe'):
            self.manager.validate(changed)
