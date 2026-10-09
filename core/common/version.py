"""Read the application's small, shared stable-version metadata file."""
from pathlib import Path
import re

from core.common.file_io import read_json
from core.common.paths import VERSION_FILE


class VersionError(ValueError):
    pass


def version_parts(version):
    if not isinstance(version, str) or not re.fullmatch(
            r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version):
        raise VersionError('Invalid stable version metadata')
    return tuple(int(part) for part in version.split('.'))


def read_version(path=VERSION_FILE):
    try:
        metadata = read_json(Path(path))
    except (OSError, ValueError) as error:
        raise VersionError('Unable to read local version metadata') from error
    if not isinstance(metadata, dict):
        raise VersionError('Invalid local version metadata')
    version = metadata.get('version')
    version_parts(version)
    return version
