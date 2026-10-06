import os
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch

from core.common import paths
from core.snips.library import SnippetLibrary


class PathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.installation = self.base / 'Programs' / 'PySnips'
        self.local_app_data = self.base / 'LocalAppData'

    def resolve_paths(self, frozen=False, override=None, bundle=None, local_app_data=True):
        environment = {}
        if local_app_data:
            environment['LOCALAPPDATA'] = str(self.local_app_data)
        if override is not None:
            environment['PYSNIPS_DATA_DIR'] = str(override)
        with patch.dict(os.environ, environment, clear=True):
            with patch.object(sys, 'frozen', frozen, create=True):
                with patch.object(sys, 'executable', str(self.installation / 'PySnips.exe')):
                    with patch.object(sys, 'platform', 'win32'):
                        with patch.object(sys, '_MEIPASS', str(bundle or self.installation), create=True):
                            return runpy.run_path(str(Path(paths.__file__)))

    def assert_user_paths(self, result, root):
        self.assertEqual(result['DATA_DIR'], root)
        self.assertEqual(result['USER_DATA_DIR'], root / 'user_data')
        self.assertEqual(result['CACHE_DIR'], root / 'cache')
        self.assertEqual(result['SNIPS_DIR'], root / 'user_data' / 'snips')
        self.assertEqual(result['TRASH_DIR'], root / 'user_data' / 'trash' / 'snips')
        self.assertEqual(result['SETTINGS_DIR'], root / 'user_data' / 'settings')
        self.assertEqual(result['SEARCH_INDEX_DIR'], root / 'cache' / 'search_index')

    def test_source_mode_uses_repository_data(self):
        result = self.resolve_paths()
        repository = Path(paths.__file__).resolve().parents[2]
        self.assertEqual(result['PROJECT_ROOT'], repository)
        self.assertEqual(result['ASSETS_DIR'], repository / 'assets')
        self.assert_user_paths(result, repository / 'data')
        self.assertEqual(result['VERSION_FILE'], repository / 'data' / 'system_data' / 'version.json')

    def test_source_override_preserves_existing_behavior(self):
        override = self.base / 'custom'
        result = self.resolve_paths(override=override)
        self.assert_user_paths(result, override)
        self.assertEqual(result['SYSTEM_DATA_DIR'], override / 'system_data')
        self.assertEqual(result['VERSION_FILE'], override / 'system_data' / 'version.json')

    def test_frozen_windows_separates_installation_and_user_data(self):
        bundle = self.installation / '_internal'
        result = self.resolve_paths(frozen=True, bundle=bundle)
        self.assertEqual(result['PROJECT_ROOT'], self.installation)
        self.assertEqual(result['ASSETS_DIR'], bundle / 'assets')
        self.assert_user_paths(result, self.local_app_data / 'PySnips')
        self.assertEqual(result['SYSTEM_DATA_DIR'], self.installation / 'data' / 'system_data')
        self.assertEqual(result['VERSION_FILE'], self.installation / 'data' / 'system_data' / 'version.json')
        self.assertFalse(result['USER_DATA_DIR'].is_relative_to(self.installation))
        self.assertFalse(result['CACHE_DIR'].is_relative_to(result['USER_DATA_DIR']))
        self.assertFalse(self.local_app_data.exists())

    def test_frozen_override_keeps_version_with_application(self):
        override = self.base / 'custom'
        result = self.resolve_paths(frozen=True, override=override)
        self.assert_user_paths(result, override)
        self.assertEqual(result['VERSION_FILE'], self.installation / 'data' / 'system_data' / 'version.json')

    def test_missing_local_app_data_uses_home_fallback(self):
        with patch.object(Path, 'home', return_value=self.base / 'home'):
            result = self.resolve_paths(frozen=True, local_app_data=False)
        self.assert_user_paths(result, self.base / 'home' / 'AppData' / 'Local' / 'PySnips')

    def test_library_consumes_frozen_user_and_cache_paths(self):
        result = self.resolve_paths(frozen=True)
        with patch.multiple('core.snips.library', **{
            name: result[name] for name in ('DATA_DIR', 'SNIPS_DIR', 'TRASH_DIR', 'SEARCH_INDEX_DIR')
        }):
            library = SnippetLibrary(result['DATA_DIR'])
        self.assertEqual(library.root, result['SNIPS_DIR'])
        self.assertEqual(library.trash, result['TRASH_DIR'])
        self.assertEqual(library.index.directory, result['SEARCH_INDEX_DIR'])
        self.assertFalse(self.installation.exists())
