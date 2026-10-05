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
    return Settings(language=raw.get('language', 'en') if isinstance(raw.get('language', 'en'), str) else 'en',
                    theme=raw.get('theme', 'dark') if isinstance(raw.get('theme', 'dark'), str) else 'dark',
                    start_on_snips=raw.get('start_on_snips') is True)


def save_settings(settings, path=SETTINGS_DIR / 'settings.json'):
    write_json_atomic(path, asdict(settings))
