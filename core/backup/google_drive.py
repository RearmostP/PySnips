"""Small Drive boundary. Completed archives in, downloaded archives out."""
from functools import wraps
import os
from pathlib import Path
import tempfile

from core.common.paths import RESOURCE_ROOT
from core.backup.backup_manager import BackupError

SCOPES = ['https://www.googleapis.com/auth/drive.file']
SERVICE = 'PySnips.GoogleDrive'
ACCOUNT = 'desktop-oauth-v1'
FOLDER = 'PySnips Backups'
MARKER = {'pysnipsBackup': 'v1'}


def boundary(key):
    def decorate(method):
        @wraps(method)
        def call(*args, **kwargs):
            try:
                return method(*args, **kwargs)
            except BackupError:
                raise
            except Exception as error:
                from google.auth.exceptions import RefreshError
                from googleapiclient.errors import HttpError
                if isinstance(error, RefreshError) or isinstance(error, HttpError) and error.resp.status == 401:
                    args[0].credentials = None
                    raise BackupError('authorization') from None
                # Never expose OAuth responses, tokens, URLs or client configuration.
                raise BackupError(key) from None
        return call
    return decorate


class CredentialStore:
    """Use only an OS-backed keyring. No plaintext fallback."""
    def _backend(self):
        import keyring
        backend = keyring.get_keyring()
        allowed = ('keyring.backends.Windows', 'keyring.backends.macOS',
                   'keyring.backends.SecretService')
        if not backend.__class__.__module__.startswith(allowed):
            raise BackupError('credentials')
        return backend

    def load(self):
        try:
            return self._backend().get_password(SERVICE, ACCOUNT)
        except Exception:
            raise BackupError('credentials') from None

    def save(self, value):
        try:
            self._backend().set_password(SERVICE, ACCOUNT, value)
        except Exception:
            raise BackupError('credentials') from None

    def delete(self):
        try:
            backend = self._backend()
            if backend.get_password(SERVICE, ACCOUNT) is not None:
                backend.delete_password(SERVICE, ACCOUNT)
        except Exception:
            raise BackupError('credentials') from None


class GoogleDrive:
    def __init__(self, *, client_path=None, store=None, service_factory=None):
        self.client_path = Path(client_path or os.environ.get('PYSNIPS_GOOGLE_CLIENT_JSON')
                                or RESOURCE_ROOT / 'assets/oauth/google-desktop-client.json')
        self.store = store or CredentialStore()
        self.credentials = None
        self.service_factory = service_factory

    @property
    def connected(self):
        return self.credentials is not None

    @boundary('authorization')
    def resume(self):
        from google.oauth2.credentials import Credentials
        import json
        saved = self.store.load()
        if saved:
            self.credentials = Credentials.from_authorized_user_info(json.loads(saved), SCOPES)
            if set(self.credentials.scopes or ()) != set(SCOPES):
                self.credentials = None
                raise BackupError('authorization')
            self._refresh()
        return self.connected

    @boundary('connect')
    def connect(self):
        from google_auth_oauthlib.flow import InstalledAppFlow, WSGITimeoutError
        from oauthlib.oauth2 import AccessDeniedError
        import json
        if not self.client_path.is_file():
            raise BackupError('configuration')
        try:
            configuration = json.loads(self.client_path.read_text(encoding='utf-8-sig'))
            installed = configuration['installed']
            if not isinstance(installed, dict) or not all(
                    isinstance(installed.get(key), str) and installed[key]
                    for key in ('client_id', 'client_secret', 'auth_uri', 'token_uri')):
                raise ValueError()
            flow = InstalledAppFlow.from_client_secrets_file(str(self.client_path), SCOPES,
                                                            autogenerate_code_verifier=True)
        except (ValueError, OSError, KeyError, TypeError):
            raise BackupError('configuration') from None
        try:
            credentials = flow.run_local_server(host='localhost', port=0, open_browser=True,
                                               timeout_seconds=180, authorization_prompt_message='',
                                               success_message='PySnips', access_type='offline', prompt='consent')
        except (TimeoutError, WSGITimeoutError, AccessDeniedError):
            raise BackupError('cancelled') from None
        if not credentials.refresh_token or not credentials.has_scopes(SCOPES):
            raise BackupError('authorization')
        self.store.save(credentials.to_json())
        self.credentials = credentials
        return True

    def disconnect(self):
        self.store.delete()
        self.credentials = None

    def _refresh(self):
        from google.auth.transport.requests import Request
        if not self.connected:
            raise BackupError('authorization')
        if not self.credentials.valid:
            self.credentials.refresh(Request())
            self.store.save(self.credentials.to_json())

    def _service(self):
        self._refresh()
        if self.service_factory:
            return self.service_factory(self.credentials)
        from googleapiclient.discovery import build
        from google_auth_httplib2 import AuthorizedHttp
        from httplib2 import Http
        # Bundled static discovery avoids an extra runtime discovery request.
        return build('drive', 'v3', http=AuthorizedHttp(self.credentials, http=Http(timeout=60)), cache_discovery=False,
                     static_discovery=True)

    @staticmethod
    def _all(files, query, fields, **kwargs):
        result, token = [], None
        while True:
            response = files.list(q=query, spaces='drive', fields='nextPageToken,files(' + fields + ')',
                                  pageToken=token, pageSize=100, **kwargs).execute()
            result.extend(response.get('files', []))
            token = response.get('nextPageToken')
            if not token:
                return result

    @boundary('folder')
    def _folder(self, files):
        folders = self._all(files, "trashed = false and mimeType = 'application/vnd.google-apps.folder' "
                            "and name = 'PySnips Backups' and 'root' in parents "
                            "and appProperties has { key='pysnipsBackup' and value='v1' }", 'id,createdTime')
        if folders:
            return sorted(folders, key=lambda f: f.get('createdTime', ''))[0]['id']
        return files.create(body={'name': FOLDER, 'mimeType': 'application/vnd.google-apps.folder',
                                  'parents': ['root'], 'appProperties': MARKER}, fields='id').execute()['id']

    @boundary('list')
    def list_backups(self):
        files = self._service().files()
        folder = self._folder(files)
        backups = self._all(files, f"'{folder}' in parents and trashed = false and mimeType = 'application/zip' "
                            "and appProperties has { key='pysnipsBackup' and value='v1' }",
                            'id,name,size,createdTime', orderBy='createdTime desc')
        return sorted((f for f in backups if f.get('name', '').startswith('PySnips-Backup-')
                       and f['name'].endswith('.zip')), key=lambda f: f.get('createdTime', ''), reverse=True)

    @boundary('upload')
    def upload(self, archive, progress=lambda value: None):
        from googleapiclient.http import MediaFileUpload
        archive = Path(archive)
        if not archive.is_file() or archive.suffix != '.zip':
            raise BackupError('upload')
        files = self._service().files()
        folder = self._folder(files)
        media = MediaFileUpload(str(archive), mimetype='application/zip', resumable=True, chunksize=1024 * 1024)
        try:
            request = files.create(body={'name': archive.name, 'parents': [folder], 'appProperties': MARKER},
                                   media_body=media, fields='id,name,size,createdTime')
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress(round(status.progress() * 100))
            return response
        finally:
            media.stream().close()

    @boundary('download')
    def download(self, backup_id, destination):
        from googleapiclient.http import MediaIoBaseDownload
        from core.backup.backup_manager import check_path
        # Verify membership before downloading; never use a remote filename locally.
        if backup_id not in {b['id'] for b in self.list_backups()}:
            raise BackupError('download')
        destination = Path(destination)
        check_path(destination)
        descriptor, temporary = tempfile.mkstemp(prefix='.download-', dir=destination.parent)
        try:
            with os.fdopen(descriptor, 'wb') as stream:
                request = self._service().files().get_media(fileId=backup_id)
                downloader = MediaIoBaseDownload(stream, request, chunksize=1024 * 1024)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
                    if stream.tell() > 10 * 1024 ** 3:
                        raise BackupError('limits')
            os.replace(temporary, destination)
            return destination
        finally:
            Path(temporary).unlink(missing_ok=True)
