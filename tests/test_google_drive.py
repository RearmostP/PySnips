from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from core.backup.backup_manager import BackupError
from core.backup.google_drive import GoogleDrive, CredentialStore, SCOPES, SERVICE, ACCOUNT


class GoogleDriveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.client = self.base / 'client.json'
        self.client.write_text('{"installed":{"client_id":"test","client_secret":"test","auth_uri":"test","token_uri":"test"}}')
        self.store = MagicMock()
        self.store.load.return_value = None
        self.service = MagicMock()
        self.files = self.service.files.return_value
        self.credentials = MagicMock(valid=True, refresh_token='sensitive-not-to-log')
        self.provider = GoogleDrive(client_path=self.client, store=self.store,
                                    service_factory=lambda credentials: self.service)
        self.provider.credentials = self.credentials
        # No unexpected transport is allowed in this suite.
        self.network = patch('socket.socket.connect', side_effect=AssertionError('real network forbidden'))
        self.network.start()
        self.addCleanup(self.network.stop)

    def folders(self, *folders):
        self.files.list.return_value.execute.return_value = {'files': list(folders)}

    def test_scope_connect_stores_without_logging(self):
        self.assertEqual(SCOPES, ['https://www.googleapis.com/auth/drive.file'])
        with patch('google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file') as factory:
            flow = factory.return_value
            flow.run_local_server.return_value = self.credentials
            with patch('logging.Logger._log') as log:
                self.provider.connect()
                log.assert_not_called()
            factory.assert_called_once_with(str(self.client), SCOPES, autogenerate_code_verifier=True)
            self.store.save.assert_called_once_with(self.credentials.to_json.return_value)
            options = flow.run_local_server.call_args.kwargs
            self.assertEqual(options['port'], 0)
            self.assertTrue(options['open_browser'])
            self.assertEqual(options['timeout_seconds'], 180)

    def test_configuration_missing_and_oauth_cancelled(self):
        self.client.unlink()
        with self.assertRaisesRegex(BackupError, 'configuration'):
            self.provider.connect()
        self.client.write_text('{"installed":{"client_id":"test","client_secret":"test","auth_uri":"test","token_uri":"test"}}')
        with patch('google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file') as factory:
            factory.return_value.run_local_server.side_effect = TimeoutError('secret token')
            with self.assertRaisesRegex(BackupError, '^cancelled$'):
                self.provider.connect()
        self.store.save.assert_not_called()

    def test_disconnect_deletes_credentials(self):
        self.provider.disconnect()
        self.store.delete.assert_called_once()
        self.assertFalse(self.provider.connected)

    def test_secure_os_store_keys_and_plaintext_backend_rejection(self):
        backend = MagicMock()
        # A real backend class identity, with methods mocked, avoids real keyring writes.
        from keyring.backends.Windows import WinVaultKeyring
        with patch.object(WinVaultKeyring, 'get_password', return_value='private') as get:
            with patch.object(WinVaultKeyring, 'set_password') as save:
                with patch.object(WinVaultKeyring, 'delete_password') as delete:
                    with patch('keyring.get_keyring', return_value=WinVaultKeyring()):
                        store = CredentialStore()
                        self.assertEqual(store.load(), 'private')
                        store.save('private')
                        store.delete()
                        get.assert_called_with(SERVICE, ACCOUNT)
                        save.assert_called_once_with(SERVICE, ACCOUNT, 'private')
                        delete.assert_called_once_with(SERVICE, ACCOUNT)
        with patch('keyring.get_keyring', return_value=backend):
            with self.assertRaisesRegex(BackupError, 'credentials'):
                CredentialStore().save('private')

    def test_resume_refreshes_and_persists_without_interactive_login(self):
        self.store.load.return_value = '{}'
        self.credentials.valid = False
        self.credentials.scopes = SCOPES
        with patch('google.oauth2.credentials.Credentials.from_authorized_user_info', return_value=self.credentials):
            with patch('google.auth.transport.requests.Request'):
                self.assertTrue(self.provider.resume())
        self.credentials.refresh.assert_called_once()
        self.store.save.assert_called_once()

    def test_revoked_credentials_are_safe_application_error(self):
        from google.auth.exceptions import RefreshError
        self.credentials.valid = False
        self.credentials.refresh.side_effect = RefreshError('secret raw response')
        with self.assertRaisesRegex(BackupError, '^authorization$'):
            self.provider.list_backups()
        self.assertFalse(self.provider.connected)

    def test_folder_created_when_missing_and_reused_when_present(self):
        self.folders()
        self.files.create.return_value.execute.return_value = {'id': 'folder'}
        self.assertEqual(self.provider._folder(self.files), 'folder')
        body = self.files.create.call_args.kwargs['body']
        self.assertEqual(body['name'], 'PySnips Backups')
        self.assertEqual(body['parents'], ['root'])
        self.assertEqual(body['appProperties'], {'pysnipsBackup': 'v1'})
        self.files.create.reset_mock()
        self.folders({'id': 'existing', 'createdTime': '2026'})
        self.assertEqual(self.provider._folder(self.files), 'existing')
        self.files.create.assert_not_called()
        query = self.files.list.call_args.kwargs['q']
        self.assertIn('appProperties', query)
        self.assertNotIn('appDataFolder', query)

    def test_folder_failure_classified(self):
        self.files.list.return_value.execute.side_effect = OSError('network token')
        with self.assertRaisesRegex(BackupError, '^folder$'):
            self.provider.list_backups()

    def test_list_paginated_sorted_newest_first(self):
        self.files.list.return_value.execute.side_effect = [
            {'files': [{'id': 'folder'}]},
            {'files': [{'id': 'old', 'name': 'PySnips-Backup-old.zip', 'createdTime': '2025'}], 'nextPageToken': 'page2'},
            {'files': [{'id': 'new', 'name': 'PySnips-Backup-new.zip', 'createdTime': '2026'},
                       {'id': 'other', 'name': 'other.zip', 'createdTime': '2027'}]},
        ]
        self.assertEqual([f['id'] for f in self.provider.list_backups()], ['new', 'old'])
        self.assertEqual(self.files.list.call_args.kwargs['pageToken'], 'page2')

    def test_upload_completed_zip_and_real_progress(self):
        self.folders({'id': 'folder'})
        archive = self.base / 'PySnips-Backup-test.zip'
        archive.write_bytes(b'completed snapshot')
        status = MagicMock()
        status.progress.return_value = 0.5
        request = self.files.create.return_value
        request.next_chunk.side_effect = [(status, None), (None, {'id': 'uploaded'})]
        updates = []
        with patch('googleapiclient.http.MediaFileUpload') as media:
            self.assertEqual(self.provider.upload(archive, updates.append), {'id': 'uploaded'})
            self.assertEqual(media.call_args.args[0], str(archive))
            self.assertTrue(media.call_args.kwargs['resumable'])
            media.return_value.stream.return_value.close.assert_called_once()
        self.assertEqual(updates, [50])
        self.assertEqual(request.next_chunk.call_count, 2)

    def test_download_uses_id_and_local_name_exposes_only_completed_file(self):
        destination = self.base / 'snapshot.zip'
        with patch.object(self.provider, 'list_backups', return_value=[{'id': 'chosen'}]):
            with patch('googleapiclient.http.MediaIoBaseDownload') as downloader:
                def make(stream, request, **kwargs):
                    stream.write(b'zip bytes')
                    worker = MagicMock()
                    worker.next_chunk.return_value = (None, True)
                    return worker
                downloader.side_effect = make
                self.assertEqual(self.provider.download('chosen', destination), destination)
        self.assertEqual(destination.read_bytes(), b'zip bytes')
        self.files.get_media.assert_called_once_with(fileId='chosen')
        self.assertEqual(list(self.base.glob('.download-*')), [])

    def test_failed_download_keeps_existing_destination(self):
        destination = self.base / 'snapshot.zip'
        destination.write_bytes(b'old complete file')
        with patch.object(self.provider, 'list_backups', return_value=[{'id': 'chosen'}]):
            with patch('googleapiclient.http.MediaIoBaseDownload') as downloader:
                downloader.return_value.next_chunk.side_effect = OSError('network secret')
                with self.assertRaisesRegex(BackupError, '^download$'):
                    self.provider.download('chosen', destination)
        self.assertEqual(destination.read_bytes(), b'old complete file')
        self.assertEqual(list(self.base.glob('.download-*')), [])

    def test_api_errors_never_expose_response(self):
        with patch.object(self.provider, '_folder', return_value='folder'):
            self.files.list.return_value.execute.side_effect = OSError('token secret')
            with self.assertRaisesRegex(BackupError, '^list$'):
                self.provider.list_backups()
            self.files.create.return_value.next_chunk.side_effect = OSError('token secret')
            archive = self.base / 'backup.zip'
            archive.write_bytes(b'zip')
            with self.assertRaisesRegex(BackupError, '^upload$'):
                self.provider.upload(archive)
