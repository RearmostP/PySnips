"""Local version metadata and stable GitHub Release checks."""

from dataclasses import dataclass
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from core.common.file_io import read_json
from core.common.paths import VERSION_FILE


LATEST_RELEASE_URL = 'https://api.github.com/repos/RearmostP/PySnips/releases/latest'
INSTALLER_NAME = 'PySnips-{version}-Setup.exe'


class UpdateError(Exception):
    """Raised when update metadata cannot be read or validated."""


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    download_url: str
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


# מחפש בתוך קבצי ה-Release את קובץ ההתקנה המתאים של PySnips.
def _installer_url(release, version):
    assets = release.get('assets')

    if not isinstance(assets, list):
        raise UpdateError('Invalid GitHub release assets')

    expected_name = INSTALLER_NAME.format(version=version)

    matches = [
        asset
        for asset in assets
        if isinstance(asset, dict)
        and asset.get('name') == expected_name
    ]

    if len(matches) != 1:
        raise UpdateError(
            f'Release is missing a unique installer asset: {expected_name}'
        )

    url = matches[0].get('browser_download_url')

    if not _valid_download_url(url):
        raise UpdateError('Invalid installer download URL')

    return url


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
            download_url=_installer_url(release, version),
            release_notes=_release_notes(release),
        )