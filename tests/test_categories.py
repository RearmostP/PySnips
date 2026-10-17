import json
from pathlib import Path
import subprocess
import os
import tempfile
import unittest
from unittest.mock import patch

from core.common.file_io import read_json, write_json_atomic
from core.snips.library import SnippetLibrary
from core.snips.models import LibraryError


class CategoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.library = SnippetLibrary(self.base)

    def record(self, name):
        return next(c for c in read_json(self.library.categories_file) if c['name'] == name)

    def snapshot(self, root):
        return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}

    def test_legacy_migration_preserves_order_snippets_and_media(self):
        snippet = self.library.create('Example', 'Python', 'migrationword')
        media = self.library.media_base(snippet.id) / 'media/example.bin'
        media.write_bytes(b'keep these bytes')
        original = self.snapshot(self.library.root / 'Python')
        write_json_atomic(self.library.categories_file, ['Python', 'PySide6'])
        library = SnippetLibrary(self.base)
        self.assertEqual(library.categories(), ['Python', 'PySide6'])
        self.assertEqual(read_json(library.categories_file), [
            {'name': name, 'pinned': False, 'deleted': False} for name in ('Python', 'PySide6')])
        self.assertEqual(library.load(snippet.id), snippet)
        self.assertEqual(self.snapshot(library.root / 'Python'), original)

    def test_failed_migration_keeps_original_bytes_and_data(self):
        snippet = self.library.create('Example', 'Python', 'keep')
        self.library.categories_file.write_text('["Python", "PySide6"]', encoding='utf-8')
        original = self.snapshot(self.library.root)
        with patch('core.snips.library.write_json_atomic', side_effect=OSError('denied')):
            with self.assertRaises(OSError):
                SnippetLibrary(self.base)
        self.assertEqual(self.snapshot(self.library.root), original)
        self.assertEqual(self.library.load(snippet.id), snippet)

    def test_new_format_only_ensures_active_directories(self):
        records = [
            {'name': 'Gone', 'pinned': False, 'deleted': True},
            {'name': 'Active', 'pinned': True, 'deleted': False}]
        write_json_atomic(self.library.categories_file, records)
        library = SnippetLibrary(self.base)
        self.assertEqual(library.categories(), ['Active'])
        self.assertTrue((library.root / 'Active').is_dir())
        self.assertFalse((library.root / 'Gone').exists())
        self.assertEqual(library.deleted_categories(), ['Gone'])
        self.assertEqual(read_json(library.categories_file), records)

    def test_pin_unpin_stable_order_and_only_metadata_changes(self):
        self.library.add_category('Third')
        self.library.create('Example', 'Python', 'keep')
        before = self.snapshot(self.library.root)
        self.library.pin_category('Third', True)
        self.library.pin_category('PySide6', True)
        self.assertEqual(self.library.categories(), ['PySide6', 'Third', 'Python'])
        self.assertTrue(self.library.category_pinned('PySide6'))
        self.library.pin_category('PySide6', False)
        self.assertEqual(self.library.categories(), ['Third', 'Python', 'PySide6'])
        self.library.pin_category('Third', False)
        self.assertEqual(self.library.categories(), ['Python', 'PySide6', 'Third'])
        self.assertEqual(self.snapshot(self.library.root), before)
        self.assertEqual(list(self.library.category_trash.iterdir()), [])

    def test_soft_delete_moves_whole_directory_and_hides_search_results(self):
        snippets = [self.library.create(str(i), 'Python', 'uniquecategoryword') for i in range(2)]
        source = self.library.root / 'Python'
        (source / 'extra.txt').write_bytes(b'whole category must move')
        before = self.snapshot(source)
        self.library.pin_category('Python', True)
        rename = Path.rename
        moved = []
        def record_move(path, target):
            moved.append((path, target))
            return rename(path, target)
        with patch.object(Path, 'rename', record_move):
            self.library.delete_category('Python')
        target = self.library.category_trash / 'Python'
        self.assertEqual(moved, [(source, target)])
        self.assertFalse(source.exists())
        self.assertEqual(self.snapshot(target), before)
        self.assertEqual(self.record('Python'), {'name': 'Python', 'pinned': False, 'deleted': True})
        self.assertEqual(self.library.categories(), ['PySide6'])
        self.assertEqual(self.library.list(), [])
        self.assertEqual(self.library.search('uniquecategoryword'), [])
        self.assertEqual(self.library.deleted(), [])
        self.assertEqual(self.library.deleted_categories(), ['Python'])
        self.assertFalse((SnippetLibrary(self.base).root / 'Python').exists())
        for snippet in snippets:
            with self.assertRaisesRegex(LibraryError, 'not_found'):
                self.library.load(snippet.id)
        with self.assertRaisesRegex(LibraryError, 'name_exists'):
            self.library.add_category('python')
        with self.assertRaisesRegex(LibraryError, 'category_missing'):
            self.library.create('Blocked', 'Python', 'blocked')

    def test_restore_category_restores_all_contents_and_search(self):
        snippet = self.library.create('Example', 'Python', 'restoredword')
        (self.library.media_base(snippet.id) / 'media/test.bin').write_bytes(b'bytes')
        original = self.snapshot(self.library.root / 'Python')
        self.library.pin_category('Python', True)
        self.library.delete_category('Python')
        self.library.restore_category('Python')
        self.assertFalse((self.library.category_trash / 'Python').exists())
        self.assertEqual(self.snapshot(self.library.root / 'Python'), original)
        self.assertEqual(self.library.load(snippet.id), snippet)
        self.assertEqual(self.library.search('restoredword'), [snippet])
        self.assertEqual(self.record('Python'), {'name': 'Python', 'pinned': False, 'deleted': False})

    def test_move_failures_and_metadata_failures_preserve_state(self):
        self.library.create('Example', 'Python', 'keep')
        for deleting in (True, False):
            action = self.library.delete_category if deleting else self.library.restore_category
            before = self.snapshot(self.base / 'user_data')
            for target in ('pathlib.Path.rename', 'core.snips.library.write_json_atomic'):
                with self.subTest(deleting=deleting, target=target):
                    with patch(target, side_effect=OSError('denied')):
                        with self.assertRaises(OSError):
                            action('Python')
                    self.assertEqual(self.snapshot(self.base / 'user_data'), before)
            if deleting:
                self.library.delete_category('Python')

    def test_restore_conflict_does_not_overwrite_any_data(self):
        self.library.create('Example', 'Python', 'keep')
        self.library.delete_category('Python')
        (self.library.root / 'Python').mkdir()
        (self.library.root / 'Python/conflict.txt').write_bytes(b'conflict')
        before = self.snapshot(self.base / 'user_data')
        with self.assertRaisesRegex(LibraryError, 'category_destination_exists'):
            self.library.restore_category('Python')
        self.assertEqual(self.snapshot(self.base / 'user_data'), before)

    def test_trash_conflict_does_not_move_or_update_metadata(self):
        (self.library.category_trash / 'Python').mkdir()
        before = self.snapshot(self.base / 'user_data')
        with self.assertRaisesRegex(LibraryError, 'category_trash_exists'):
            self.library.delete_category('Python')
        self.assertTrue((self.library.root / 'Python').is_dir())
        self.assertEqual(self.snapshot(self.base / 'user_data'), before)

    def test_permanent_delete_removes_record_after_filesystem_success(self):
        self.library.create('Example', 'Python', 'keep')
        self.library.delete_category('Python')
        with patch('core.snips.library.shutil.rmtree', side_effect=OSError('denied')):
            with self.assertRaises(OSError):
                self.library.permanently_delete_category('Python')
        self.assertTrue(self.record('Python')['deleted'])
        self.assertTrue((self.library.category_trash / 'Python').is_dir())
        write = write_json_atomic
        def check_write(path, records):
            self.assertFalse((self.library.category_trash / 'Python').exists())
            self.assertTrue(self.record('Python')['deleted'])
            write(path, records)
        with patch('core.snips.library.write_json_atomic', side_effect=check_write):
            self.library.permanently_delete_category('Python')
        self.assertEqual(self.library.deleted_categories(), [])
        self.assertNotIn('Python', [c['name'] for c in read_json(self.library.categories_file)])
        self.library.add_category('Python')

    def test_permanent_metadata_failure_retains_record_and_can_be_retried(self):
        self.library.delete_category('Python')
        with patch('core.snips.library.write_json_atomic', side_effect=OSError('denied')):
            with self.assertRaises(OSError):
                self.library.permanently_delete_category('Python')
        self.assertTrue(self.record('Python')['deleted'])
        self.assertFalse((self.library.category_trash / 'Python').exists())
        self.library.permanently_delete_category('Python')
        self.assertEqual(self.library.deleted_categories(), [])

    def test_individual_trash_remains_separate(self):
        individual = self.library.create('Individual', 'Python', 'individualword')
        together = self.library.create('Together', 'Python', 'categoryword')
        self.library.delete(individual.id)
        self.library.delete_category('Python')
        self.assertEqual(self.library.deleted(), [individual])
        self.assertTrue((self.library.trash / individual.id).is_dir())
        with self.assertRaisesRegex(LibraryError, 'category_missing'):
            self.library.restore(individual.id)
        self.library.restore_category('Python')
        self.library.restore(individual.id)
        self.assertEqual({s.id for s in self.library.list()}, {individual.id, together.id})
        self.library.delete(individual.id)
        self.library.permanently_delete(individual.id)
        self.assertEqual(self.library.deleted(), [])

    def test_missing_categories_and_invalid_pin_value(self):
        (self.library.root / 'PySide6').rmdir()
        with self.assertRaisesRegex(LibraryError, 'category_missing'):
            self.library.delete_category('PySide6')
        self.assertFalse((self.library.root / 'PySide6').exists())
        for operation in (lambda: self.library.pin_category('Missing', True),
                          lambda: self.library.delete_category('Missing')):
            with self.assertRaisesRegex(LibraryError, 'category_missing'):
                operation()
        for operation in (self.library.restore_category, self.library.permanently_delete_category):
            with self.assertRaisesRegex(LibraryError, 'deleted_category_missing'):
                operation('Missing')
        with self.assertRaisesRegex(LibraryError, 'invalid_data'):
            self.library.pin_category('Python', 1)
        self.library.delete_category('Python')
        (self.library.category_trash / 'Python').rmdir()
        with self.assertRaisesRegex(LibraryError, 'deleted_category_missing'):
            self.library.restore_category('Python')

    def test_malformed_metadata_is_rejected_without_writes_or_directory_creation(self):
        cases = [None, {}, ['New', {'name': 'Python', 'pinned': False, 'deleted': False}],
                 ['New', '../escape'], ['New', 'new'],
                 [{'name': 'New', 'pinned': 1, 'deleted': False}],
                 [{'name': 'New', 'pinned': False}],
                 [{'name': 1, 'pinned': False, 'deleted': False}],
                 [{'name': '../escape', 'pinned': False, 'deleted': False}],
                 [{'name': 'New', 'pinned': True, 'deleted': True}],
                 [{'name': 'New', 'pinned': False, 'deleted': False, 'extra': 1}]]
        for records in cases:
            with self.subTest(records=records):
                write_json_atomic(self.library.categories_file, records)
                before = self.library.categories_file.read_bytes()
                with self.assertRaisesRegex(LibraryError, 'invalid_data'):
                    self.library.categories()
                self.assertEqual(self.library.categories_file.read_bytes(), before)
                self.assertFalse((self.library.root / 'New').exists())

    def test_empty_legacy_list_loads(self):
        write_json_atomic(self.library.categories_file, [])
        self.assertEqual(self.library.categories(), [])

    def test_restore_rejects_invalid_snippet_metadata_before_moving(self):
        snippet = self.library.create('Example', 'Python', 'keep')
        self.library.delete_category('Python')
        metadata = self.library.category_trash / 'Python' / snippet.disk_name / 'metadata.json'
        metadata.write_text('{}', encoding='utf-8')
        before = self.snapshot(self.base / 'user_data')
        with self.assertRaisesRegex(LibraryError, 'invalid_data'):
            self.library.restore_category('Python')
        self.assertEqual(self.snapshot(self.base / 'user_data'), before)

    def test_restore_rejects_uuid_collision_with_active_snippet(self):
        snippet = self.library.create('Example', 'Python', 'keep')
        other = self.library.create('Other', 'PySide6', 'other')
        self.library.delete_category('Python')
        metadata = self.library.category_trash / 'Python' / snippet.disk_name / 'metadata.json'
        value = read_json(metadata)
        value['id'] = other.id
        write_json_atomic(metadata, value)
        with self.assertRaisesRegex(LibraryError, 'invalid_data'):
            self.library.restore_category('Python')
        self.assertFalse((self.library.root / 'Python').exists())
        self.assertTrue(self.record('Python')['deleted'])

    def test_failed_move_rollback_reports_recovery_error_and_keeps_data(self):
        self.library.create('Example', 'Python', 'keep')
        rename = Path.rename
        def fail_rollback(path, target):
            if path.parent == self.library.category_trash:
                raise OSError('cannot roll back')
            return rename(path, target)
        with patch.object(Path, 'rename', fail_rollback):
            with patch('core.snips.library.write_json_atomic', side_effect=OSError('cannot write')):
                with self.assertRaisesRegex(LibraryError, 'category_rollback'):
                    self.library.delete_category('Python')
        self.assertFalse((self.library.root / 'Python').exists())
        self.assertTrue((self.library.category_trash / 'Python').is_dir())
        self.assertFalse(self.record('Python')['deleted'])

    def test_junction_inside_category_rejected_for_move_restore_and_delete(self):
        if os.name != 'nt':
            self.skipTest('Windows junction test')
        external = self.base / 'external'
        external.mkdir()
        (external / 'important.txt').write_bytes(b'keep')
        link = self.library.root / 'Python/linked'
        result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(external)], capture_output=True)
        if result.returncode:
            self.skipTest('Junction creation unavailable')
        try:
            with self.assertRaisesRegex(LibraryError, 'invalid_data'):
                self.library.delete_category('Python')
            self.assertFalse(self.record('Python')['deleted'])
            link.rmdir()
            self.library.delete_category('Python')
            link = self.library.category_trash / 'Python/linked'
            subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(external)], capture_output=True, check=True)
            for action in (self.library.restore_category, self.library.permanently_delete_category):
                with self.assertRaisesRegex(LibraryError, 'invalid_data'):
                    action('Python')
            self.assertEqual((external / 'important.txt').read_bytes(), b'keep')
        finally:
            if link.is_junction():
                link.rmdir()
