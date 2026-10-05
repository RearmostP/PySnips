import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from core.common.file_io import read_json, write_json_atomic
from core.snips.library import SnippetLibrary
from core.snips.models import LibraryError


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.library = SnippetLibrary(self.base)

    def create(self, **kwargs):
        return self.library.create('Create Python environment', 'Python',
                                   '# Example\n```python\nprint(123)\n```', tags=['venv', 'venv'], **kwargs)

    def test_create_self_contained_directory(self):
        s = self.create()
        directory = self.library.media_base(s.id)
        self.assertEqual({p.name for p in directory.iterdir()}, {'snippet.md', 'metadata.json', 'media'})
        self.assertEqual(self.library.load(s.id), s)
        meta = read_json(directory / 'metadata.json')
        self.assertEqual(set(meta), {'id', 'title', 'disk_name', 'category', 'tags', 'created_at'})
        self.assertEqual(meta['tags'], ['venv'])

    def test_title_does_not_change_identity_or_directory(self):
        s = self.create()
        updated = self.library.update(s.id, title='Different title', tags='one, one, two')
        self.assertEqual(updated.disk_name, s.disk_name)
        self.assertEqual(updated.id, s.id)
        self.assertEqual(updated.created_at, s.created_at)
        self.assertEqual(updated.tags, ['one', 'two'])

    def test_category_authority_and_missing_directory(self):
        (self.library.root / 'Python').rmdir()
        (self.library.root / 'Unlisted').mkdir()
        self.assertEqual(self.library.categories(), ['Python', 'PySide6'])
        self.assertTrue((self.library.root / 'Python').is_dir())
        with self.assertRaises(LibraryError):
            self.library.create('test', 'Unlisted', 'test')

    def test_names_and_collision(self):
        for name in ('../outside', 'CON', 'bad.', 'a/b', 'x\\y', '.hidden'):
            with self.subTest(name=name), self.assertRaises(LibraryError):
                self.create(disk_name=name)
        first, second = self.create(), self.create()
        self.assertNotEqual(first.disk_name, second.disk_name)
        with self.assertRaises(LibraryError):
            self.create(disk_name=first.disk_name)

    def test_move_keeps_media_and_relative_links(self):
        s = self.create()
        source = self.base / 'sample.png'
        source.write_bytes(b'image bytes')
        relative = self.library.add_media(s.id, source)
        self.library.update(s.id, content=f'![sample]({relative})')
        old = self.library.media_base(s.id)
        moved = self.library.move(s.id, 'PySide6')
        self.assertEqual(moved.category, 'PySide6')
        self.assertFalse(old.exists())
        self.assertEqual((self.library.media_base(s.id) / relative).read_bytes(), b'image bytes')
        self.assertEqual(moved.content, '![sample](media/sample.png)')

    def test_move_conflict_does_not_overwrite(self):
        s = self.create(disk_name='same')
        other = self.library.create('Other', 'PySide6', 'other', disk_name='same')
        with self.assertRaises(LibraryError):
            self.library.move(s.id, 'PySide6')
        self.assertEqual(self.library.load(s.id).category, 'Python')
        self.assertEqual(self.library.load(other.id).content, 'other')

    def test_move_metadata_failure_rolls_back_directory(self):
        s = self.create()
        with patch('core.snips.library.write_json_atomic', side_effect=OSError('no permission')):
            with self.assertRaises(OSError):
                self.library.move(s.id, 'PySide6')
        self.assertEqual(self.library.load(s.id), s)

    def test_delete_restore_and_permanent_delete(self):
        s = self.create()
        media = self.library.media_base(s.id) / 'media' / 'keep.txt'
        media.write_text('keep')
        self.library.delete(s.id)
        self.assertEqual(self.library.list(), [])
        self.assertEqual(self.library.deleted(), [s])
        restored = self.library.restore(s.id)
        self.assertEqual(restored, s)
        self.assertEqual((self.library.media_base(s.id) / 'media' / 'keep.txt').read_text(), 'keep')
        self.library.delete(s.id)
        self.library.permanently_delete(s.id)
        self.assertEqual(self.library.deleted(), [])

    def test_restore_conflict_keeps_trash(self):
        s = self.create(disk_name='same')
        self.library.delete(s.id)
        self.create(disk_name='same')
        with self.assertRaises(LibraryError):
            self.library.restore(s.id)
        self.assertEqual(self.library.deleted(), [s])

    def test_search_rebuild_and_updates(self):
        s = self.create()
        shutil.rmtree(self.library.index.directory)
        self.assertEqual([hit.id for hit in self.library.search('ven')], [s.id])
        self.library.update(s.id, title='UniqueTitle', tags=['newtag'], content='specialbody')
        self.assertEqual([hit.id for hit in self.library.search('unique')], [s.id])
        self.assertEqual([hit.id for hit in self.library.search('specialbody')], [s.id])
        self.assertEqual(self.library.search('venv'), [])
        self.library.delete(s.id)
        self.assertEqual(self.library.search('unique'), [])
        self.library.restore(s.id)
        self.assertEqual([hit.id for hit in self.library.search('newtag')], [s.id])

    def test_invalid_data_is_not_silently_overwritten(self):
        self.library.categories_file.write_text('{broken')
        with self.assertRaises(LibraryError):
            self.library.categories()
        self.assertEqual(self.library.categories_file.read_text(), '{broken')

    def test_create_media_is_committed_with_directory(self):
        source = self.base / 'image.png'
        source.write_bytes(b'image')
        s = self.library.create('Media', 'Python', '![image](media/image.png)', media=[source])
        self.assertEqual((self.library.media_base(s.id) / 'media' / 'image.png').read_bytes(), b'image')
        with self.assertRaises(OSError):
            self.library.create('Missing media', 'Python', 'example', media=[self.base / 'missing.png'])
        self.assertEqual(len(self.library.list()), 1)

    def test_corrupt_index_is_rebuilt(self):
        s = self.create()
        for toc in self.library.index.directory.glob('*.toc'):
            toc.write_bytes(b'corrupted index')
        self.assertEqual([hit.id for hit in self.library.search('ven')], [s.id])

    def test_search_failure_does_not_undo_save(self):
        with patch.object(self.library.index, 'rebuild', side_effect=OSError('read only index')):
            s = self.create()
        self.assertEqual(self.library.load(s.id), s)
        self.assertEqual([hit.id for hit in self.library.search('ven')], [s.id])

    def test_search_detects_external_markdown_changes(self):
        s = self.create()
        (self.library.media_base(s.id) / 'snippet.md').write_text('externalword', encoding='utf-8')
        self.assertEqual([hit.id for hit in self.library.search('externalword')], [s.id])

    def test_atomic_write_failure_keeps_original(self):
        path = self.base / 'atomic.json'
        write_json_atomic(path, {'title': 'old'})
        with patch('core.common.file_io.os.replace', side_effect=OSError('denied')):
            with self.assertRaises(OSError):
                write_json_atomic(path, {'title': 'new'})
        self.assertEqual(read_json(path), {'title': 'old'})
        self.assertEqual(list(self.base.glob('.*.tmp')), [])

    def test_create_failure_does_not_leave_visible_snippet(self):
        with patch('core.snips.library.write_json_atomic', side_effect=OSError('denied')):
            with self.assertRaises(OSError):
                self.create()
        self.assertEqual(self.library.list(), [])
        self.assertEqual(list((self.library.root / 'Python').iterdir()), [])
