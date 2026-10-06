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
    """Local version metadata or a release check could not be read or validated."""


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    download_url: str
    release_notes: str


def _version_parts(version):
    # V1 accepts only stable major.minor.patch versions, without leading zeros.
    if not isinstance(version, str) or not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version):
        raise UpdateError('Invalid stable version metadata')
    return tuple(int(part) for part in version.split('.'))


class Updater:
    def __init__(self, version_file=VERSION_FILE):
        self.version_file = Path(version_file)

    @property
    def current_version(self):
        try:
            metadata = read_json(self.version_file)
        except (OSError, ValueError) as error:
            raise UpdateError('Unable to read local version metadata') from error
        if not isinstance(metadata, dict):
            raise UpdateError('Invalid local version metadata')
        version = metadata.get('version')
        _version_parts(version)
        return version

    def check(self):
        local_version = _version_parts(self.current_version)
        request = Request(LATEST_RELEASE_URL, headers={
            'User-Agent': 'PySnips-Updater',
            'Accept': 'application/vnd.github+json',
        })
        try:
            with urlopen(request, timeout=10) as response:
                release = json.load(response)
        except (OSError, ValueError) as error:
            raise UpdateError('Unable to fetch the latest GitHub release') from error

        if (not isinstance(release, dict) or release.get('draft') is not False
                or release.get('prerelease') is not False):
            raise UpdateError('Invalid stable GitHub release response')
        tag = release.get('tag_name')
        if not isinstance(tag, str) or not tag.startswith('v'):
            raise UpdateError('Invalid GitHub release tag')
        version = tag[1:]
        if _version_parts(version) <= local_version:
            return None

        assets = release.get('assets')
        notes = release.get('body')
        if not isinstance(assets, list) or (notes is not None and not isinstance(notes, str)):
            raise UpdateError('Invalid GitHub release metadata')
        expected_name = INSTALLER_NAME.format(version=version)
        matches = [asset for asset in assets if isinstance(asset, dict) and asset.get('name') == expected_name]
        if len(matches) != 1:
            raise UpdateError(f'Release is missing a unique installer asset: {expected_name}')
        url = matches[0].get('browser_download_url')
        try:
            valid_url = isinstance(url, str) and urlsplit(url).scheme == 'https' and bool(urlsplit(url).netloc)
        except ValueError:
            valid_url = False
        if not valid_url:
            raise UpdateError('Invalid installer download URL')
        return UpdateInfo(version, url, notes or '')
