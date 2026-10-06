"""Local version metadata and stable GitHub Release checks."""

from dataclasses import dataclass
from http.client import HTTPException
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from core.common.file_io import read_json
from core.common.paths import VERSION_FILE


LATEST_RELEASE_URL = 'https://api.github.com/repos/RearmostP/PySnips/releases/latest'
INSTALLER_NAME = 'PySnips-{version}-Setup.exe'
CHUNK_SIZE = 64 * 1024


class UpdateError(Exception):
    """Raised when update metadata or an installer cannot be fetched, stored or launched."""


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    download_url: str
    checksum_url: str
    release_notes: str


# בודק שמספר הגרסה תקין וממיר אותו למספרים שאפשר להשוות ביניהם.
def _version_parts(version):
    pattern = (
        r'(0|[1-9][0-9]*)\.'
        r'(0|[1-9][0-9]*)\.'
        r'(0|[1-9][0-9]*)'
    )

    if not isinstance(version, str) or not re.fullmatch(pattern, version):
        raise UpdateError('Invalid stable version metadata')

    return tuple(int(part) for part in version.split('.'))


# מביא מ-GitHub את המידע על ה-Release היציב האחרון.
def _fetch_latest_release():
    request = Request(
        LATEST_RELEASE_URL,
        headers={
            'User-Agent': 'PySnips-Updater',
            'Accept': 'application/vnd.github+json',
        },
    )

    try:
        with urlopen(request, timeout=10) as response:
            return json.load(response)

    except (OSError, ValueError) as error:
        raise UpdateError(
            'Unable to fetch the latest GitHub release'
        ) from error


# מוציא את מספר הגרסה מה-Release ובודק שהוא תקין.
def _release_version(release):
    if not isinstance(release, dict):
        raise UpdateError('Invalid GitHub release response')

    if release.get('draft') is not False:
        raise UpdateError('Latest release is a draft')

    if release.get('prerelease') is not False:
        raise UpdateError('Latest release is a prerelease')

    tag = release.get('tag_name')

    if not isinstance(tag, str) or not tag.startswith('v'):
        raise UpdateError('Invalid GitHub release tag')

    version = tag[1:]

    _version_parts(version)

    return version


# מוציא את הערות ה-Release ומחזיר טקסט ריק אם אין הערות.
def _release_notes(release):
    notes = release.get('body')

    if notes is None:
        return ''

    if not isinstance(notes, str):
        raise UpdateError('Invalid GitHub release notes')

    return notes


# בודק שכתובת ההורדה של המתקין היא כתובת HTTPS תקינה.
def _valid_download_url(url):
    if not isinstance(url, str):
        return False

    try:
        parsed = urlsplit(url)
    except ValueError:
        return False

    return parsed.scheme == 'https' and bool(parsed.netloc)


# מחפש קובץ נדרש יחיד ב-Release ומאמת את כתובת ההורדה שלו.
def _asset_url(release, expected_name):
    assets = release.get('assets')

    if not isinstance(assets, list):
        raise UpdateError('Invalid GitHub release assets')

    matches = [
        asset
        for asset in assets
        if isinstance(asset, dict)
        and asset.get('name') == expected_name
    ]

    if len(matches) != 1:
        raise UpdateError(
            f'Release is missing a unique required asset: {expected_name}'
        )

    url = matches[0].get('browser_download_url')

    if not _valid_download_url(url):
        raise UpdateError(f'Invalid download URL for asset: {expected_name}')

    return url


# מחזיר את נתיב המתקין בתיקיית העדכונים הזמנית של מערכת ההפעלה.
def _installer_path(version):
    directory = Path(tempfile.gettempdir()) / 'PySnips' / 'updates'
    return directory / INSTALLER_NAME.format(version=version)


# מוריד את המתקין לקובץ חלקי במקטעים כדי להגביל את השימוש בזיכרון.
def _download_installer(url, partial_path):
    request = Request(url, headers={'User-Agent': 'PySnips-Updater'})

    with urlopen(request, timeout=30) as response:
        with partial_path.open('wb') as file:
            while chunk := response.read(CHUNK_SIZE):
                file.write(chunk)


# מוריד checksum קטן ומאמת שהוא מכיל רק גיבוב SHA-256 תקין.
def _fetch_checksum(url):
    request = Request(url, headers={'User-Agent': 'PySnips-Updater'})
    with urlopen(request, timeout=30) as response:
        # מגביל את התשובה כדי לא לקרוא קובץ גדול בטעות.
        content = response.read(1025)
    if len(content) > 1024:
        raise UpdateError('Checksum response is too large')
    checksum = content.decode('ascii').strip()
    if not re.fullmatch(r'[0-9a-fA-F]{64}', checksum):
        raise UpdateError('Invalid SHA-256 checksum')
    return checksum.lower()


# מחשב SHA-256 מתוכן הקובץ במקטעים בלי לטעון את כולו לזיכרון.
def _file_sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as file:
        while chunk := file.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


class Updater:

    # יוצר Updater ומשתמש בקובץ שמכיל את הגרסה המקומית של האפליקציה.
    def __init__(self, version_file=VERSION_FILE):
        self.version_file = Path(version_file)

    # קורא ומאמת את הגרסה הנוכחית שמותקנת במחשב.
    @property
    def current_version(self):
        try:
            metadata = read_json(self.version_file)
        except (OSError, ValueError) as error:
            raise UpdateError(
                'Unable to read local version metadata'
            ) from error

        if not isinstance(metadata, dict):
            raise UpdateError('Invalid local version metadata')

        version = metadata.get('version')

        _version_parts(version)

        return version

    # בודק ב-GitHub אם קיימת גרסה חדשה ומחזיר עליה מידע אם נמצאה.
    def check(self):
        local_version = _version_parts(self.current_version)

        release = _fetch_latest_release()
        version = _release_version(release)

        if _version_parts(version) <= local_version:
            return None

        return UpdateInfo(
            version=version,
            download_url=_asset_url(release, INSTALLER_NAME.format(version=version)),
            checksum_url=_asset_url(release, INSTALLER_NAME.format(version=version) + '.sha256'),
            release_notes=_release_notes(release),
        )

    # מוריד עדכון ומחזיר את נתיב המתקין רק לאחר השלמת ההורדה בהצלחה.
    def download(self, update):
        if not isinstance(update, UpdateInfo):
            raise UpdateError('Invalid update information')

        _version_parts(update.version)
        if not _valid_download_url(update.download_url):
            raise UpdateError('Invalid installer download URL')
        if not _valid_download_url(update.checksum_url):
            raise UpdateError('Invalid checksum download URL')

        partial_path = None
        try:
            installer_path = _installer_path(update.version)
            partial_path = installer_path.with_suffix('.exe.part')
            installer_path.parent.mkdir(parents=True, exist_ok=True)
            _download_installer(update.download_url, partial_path)
            expected_checksum = _fetch_checksum(update.checksum_url)
            if _file_sha256(partial_path) != expected_checksum:
                raise UpdateError('Installer SHA-256 checksum mismatch')
            partial_path.replace(installer_path)
        except (OSError, ValueError, HTTPException, UpdateError) as error:
            try:
                if partial_path is not None:
                    partial_path.unlink(missing_ok=True)
            except OSError:
                # שגיאת ניקוי אינה מסתירה את הסיבה המקורית לכישלון ההורדה.
                pass
            if isinstance(error, UpdateError):
                raise
            raise UpdateError('Unable to download the installer') from error

        return installer_path

    # מאמת את נתיב המתקין ומפעיל אותו בתהליך נפרד ללא המתנה לסיומו.
    def install(self, installer_path):
        try:
            installer_path = Path(installer_path).resolve()
            if not installer_path.is_file() or installer_path.suffix.lower() != '.exe':
                raise UpdateError('Installer must be an existing .exe file')

            subprocess.Popen([str(installer_path)])
        except (TypeError, ValueError, OSError) as error:
            raise UpdateError('Unable to launch the installer') from error
