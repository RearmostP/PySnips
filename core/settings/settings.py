from dataclasses import asdict, dataclass
from core.common.file_io import read_json, write_json_atomic
from core.common.paths import SETTINGS_DIR


@dataclass
class Settings:
    language: str = 'en'
    theme: str = 'dark'
    start_on_snips: bool = False


def load_settings(path=SETTINGS_DIR / 'settings.json'):
    if not path.exists():
        return Settings()

    raw = read_json(path)
    if not isinstance(raw, dict):
        raise ValueError('Invalid settings file')

    language = raw.get('language', 'en')
    if not isinstance(language, str):
        language = 'en'

    theme = raw.get('theme', 'dark')
    if not isinstance(theme, str):
        theme = 'dark'

    start_on_snips = raw.get('start_on_snips') is True

    return Settings(
        language=language,
        theme=theme,
        start_on_snips=start_on_snips)


def save_settings(settings, localization, path=SETTINGS_DIR / 'settings.json'):
    localization.load(settings.language) # בודק שהטעינה של הקובץ שפה הכן הצליחה ורק אחרי זה שומר את השינוי להגדרות
    write_json_atomic(path, asdict(settings))
