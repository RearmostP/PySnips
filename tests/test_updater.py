from io import BytesIO
from http.client import IncompleteRead
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from core.common.paths import SYSTEM_DATA_DIR, VERSION_FILE
from core.updater import Updater, UpdateError, UpdateInfo
from core.updater.updater import CHUNK_SIZE, LATEST_RELEASE_URL


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


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        temp_patch = patch('core.updater.updater.tempfile.gettempdir', return_value=self.temp.name)
        temp_patch.start()
        self.addCleanup(temp_patch.stop)
        self.updater = Updater()
        self.update = UpdateInfo('0.1.1', 'https://example.com/arbitrary-name.exe', '')
        self.installer = Path(self.temp.name) / 'PySnips' / 'updates' / 'PySnips-0.1.1-Setup.exe'
        self.partial = self.installer.with_suffix('.exe.part')

    def response(self, chunks):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.side_effect = chunks
        return response

    def test_success_and_chunked_download(self):
        payload = b'x' * CHUNK_SIZE
        response = self.response([payload, b'end', b''])
        with patch('core.updater.updater.urlopen', return_value=response) as request:
            result = self.updater.download(self.update)
        self.assertIsInstance(result, Path)
        self.assertEqual(result, self.installer)
        self.assertEqual(result.read_bytes(), payload + b'end')
        self.assertFalse(self.partial.exists())
        self.assertEqual(response.read.call_count, 3)
        for call in response.read.call_args_list:
            self.assertEqual(call.args, (CHUNK_SIZE,))
        args, kwargs = request.call_args
        self.assertEqual(args[0].full_url, self.update.download_url)
        self.assertEqual(args[0].get_header('User-agent'), 'PySnips-Updater')
        self.assertEqual(kwargs['timeout'], 30)

    def test_existing_installer_replaced_after_success(self):
        self.installer.parent.mkdir(parents=True)
        self.installer.write_bytes(b'old')
        self.partial.write_bytes(b'stale partial')
        with patch('core.updater.updater.urlopen', return_value=BytesIO(b'new')):
            self.updater.download(self.update)
        self.assertEqual(self.installer.read_bytes(), b'new')
        self.assertFalse(self.partial.exists())

    def test_network_failure(self):
        error = URLError('offline')
        with patch('core.updater.updater.urlopen', side_effect=error):
            with self.assertRaises(UpdateError) as caught:
                self.updater.download(self.update)
        self.assertIs(caught.exception.__cause__, error)
        self.assertFalse(self.partial.exists())
        self.assertFalse(self.installer.exists())

    def test_interrupted_download_preserves_completed_installer(self):
        self.installer.parent.mkdir(parents=True)
        self.installer.write_bytes(b'completed')
        for error in (TimeoutError('timeout'), IncompleteRead(b'partial')):
            with self.subTest(error=error):
                response = self.response([b'partial', error])
                with patch('core.updater.updater.urlopen', return_value=response):
                    with self.assertRaises(UpdateError) as caught:
                        self.updater.download(self.update)
                self.assertIs(caught.exception.__cause__, error)
                self.assertEqual(self.installer.read_bytes(), b'completed')
                self.assertFalse(self.partial.exists())

    def test_write_failure_cleans_partial_file(self):
        error = OSError('disk full')
        real_open = Path.open

        def failing_open(path, *args, **kwargs):
            stream = real_open(path, *args, **kwargs)
            file = MagicMock()
            file.__enter__.return_value = file
            file.__exit__.side_effect = lambda *args: stream.close()
            file.write.side_effect = error
            return file

        with patch('core.updater.updater.urlopen', return_value=BytesIO(b'data')):
            with patch.object(Path, 'open', failing_open):
                with self.assertRaises(UpdateError) as caught:
                    self.updater.download(self.update)
        self.assertIs(caught.exception.__cause__, error)
        self.assertFalse(self.partial.exists())
        self.assertFalse(self.installer.exists())

    def test_directory_failure(self):
        error = PermissionError('access denied')
        with patch.object(Path, 'mkdir', side_effect=error):
            with self.assertRaises(UpdateError) as caught:
                self.updater.download(self.update)
        self.assertIs(caught.exception.__cause__, error)

    def test_replace_failure_preserves_completed_installer(self):
        self.installer.parent.mkdir(parents=True)
        self.installer.write_bytes(b'completed')
        error = PermissionError('installer is locked')
        with patch('core.updater.updater.urlopen', return_value=BytesIO(b'new')):
            with patch.object(Path, 'replace', side_effect=error):
                with self.assertRaises(UpdateError) as caught:
                    self.updater.download(self.update)
        self.assertIs(caught.exception.__cause__, error)
        self.assertEqual(self.installer.read_bytes(), b'completed')
        self.assertFalse(self.partial.exists())

    def test_invalid_input_does_not_access_network(self):
        for update in (None, UpdateInfo('../bad', 'https://example.com/setup.exe', ''),
                       UpdateInfo('0.1.1', 'http://example.com/setup.exe', '')):
            with self.subTest(update=update):
                with patch('core.updater.updater.urlopen') as request:
                    with self.assertRaises(UpdateError):
                        self.updater.download(update)
                    request.assert_not_called()
