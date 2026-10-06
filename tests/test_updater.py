from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from core.common.paths import SYSTEM_DATA_DIR, VERSION_FILE
from core.updater import Updater, UpdateError, UpdateInfo
from core.updater.updater import LATEST_RELEASE_URL


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.version_file = Path(self.temp.name) / 'version.json'
        self.version_file.write_text('{"version": "0.1.0"}', encoding='utf-8')
        self.updater = Updater(self.version_file)

    @staticmethod
    def release(version='0.1.1'):
        return {
            'tag_name': 'v' + version, 'draft': False, 'prerelease': False,
            'body': 'Release notes',
            'assets': [{'name': f'PySnips-{version}-Setup.exe',
                        'browser_download_url': f'https://github.com/RearmostP/PySnips/releases/download/v{version}/PySnips-{version}-Setup.exe'}],
        }

    def check_release(self, release):
        with patch('core.updater.updater.urlopen', return_value=BytesIO(json.dumps(release).encode())) as request:
            result = self.updater.check()
        args, kwargs = request.call_args
        self.assertEqual(args[0].full_url, LATEST_RELEASE_URL)
        self.assertEqual(args[0].get_header('User-agent'), 'PySnips-Updater')
        self.assertEqual(kwargs['timeout'], 10)
        return result

    def test_current_version_and_central_path(self):
        self.assertEqual(self.updater.current_version, '0.1.0')
        self.assertEqual(VERSION_FILE, SYSTEM_DATA_DIR / 'version.json')
        self.assertEqual(Updater().version_file, VERSION_FILE)

    def test_invalid_local_metadata(self):
        for content in ('{broken', '[]', '{}', '{"version": 1}',
                        '{"version": "v0.1.0"}', '{"version": "0.1"}'):
            with self.subTest(content=content):
                self.version_file.write_text(content, encoding='utf-8')
                with self.assertRaises(UpdateError):
                    _ = self.updater.current_version

    def test_missing_local_metadata(self):
        self.version_file.unlink()
        with self.assertRaises(UpdateError):
            self.updater.check()

    def test_same_and_older_versions(self):
        for version in ('0.1.0', '0.0.9'):
            with self.subTest(version=version):
                self.assertIsNone(self.check_release(self.release(version)))

    def test_newer_version_and_v_prefix(self):
        release = self.release()
        release['assets'].insert(0, {'name': 'Other.exe', 'browser_download_url': 'https://example.com/other.exe'})
        self.assertEqual(self.check_release(release), UpdateInfo(
            '0.1.1', release['assets'][1]['browser_download_url'], 'Release notes'))

    def test_numeric_version_comparison(self):
        self.version_file.write_text('{"version": "0.9.0"}', encoding='utf-8')
        self.assertEqual(self.check_release(self.release('0.10.0')).version, '0.10.0')
        self.version_file.write_text('{"version": "0.10.0"}', encoding='utf-8')
        self.assertIsNone(self.check_release(self.release('0.9.0')))

    def test_missing_or_ambiguous_installer(self):
        for assets in ([], [{'name': 'Other.exe'}], self.release()['assets'] * 2):
            with self.subTest(assets=assets):
                release = self.release()
                release['assets'] = assets
                with self.assertRaises(UpdateError):
                    self.check_release(release)

    def test_invalid_download_url(self):
        for url in (None, '', 'http://example.com/setup.exe', 'https:///setup.exe'):
            with self.subTest(url=url):
                release = self.release()
                release['assets'][0]['browser_download_url'] = url
                with self.assertRaises(UpdateError):
                    self.check_release(release)

    def test_invalid_release_response(self):
        for release in ([], {}, {'tag_name': 'v0.1.1'},
                        {**self.release(), 'assets': None},
                        {**self.release(), 'body': 3},
                        {**self.release(), 'draft': True},
                        {**self.release(), 'prerelease': True}):
            with self.subTest(release=release), self.assertRaises(UpdateError):
                self.check_release(release)

    def test_invalid_release_tags(self):
        for tag in (None, 1, '0.1.1', 'v0.1', 'v0.1.1-beta', 'v01.1.0'):
            with self.subTest(tag=tag), self.assertRaises(UpdateError):
                self.check_release({**self.release(), 'tag_name': tag})

    def test_empty_release_notes(self):
        self.assertEqual(self.check_release({**self.release(), 'body': None}).release_notes, '')

    def test_network_and_http_failures(self):
        for error in (URLError('offline'), TimeoutError('timeout'),
                      HTTPError(LATEST_RELEASE_URL, 503, 'Unavailable', {}, None),
                      HTTPError(LATEST_RELEASE_URL, 404, 'Not found', {}, None)):
            with self.subTest(error=error):
                with patch('core.updater.updater.urlopen', side_effect=error):
                    with self.assertRaises(UpdateError) as caught:
                        self.updater.check()
                    self.assertIs(caught.exception.__cause__, error)

    def test_invalid_json_response(self):
        with patch('core.updater.updater.urlopen', return_value=BytesIO(b'{broken')):
            with self.assertRaises(UpdateError):
                self.updater.check()
