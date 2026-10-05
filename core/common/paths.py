import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = PROJECT_ROOT / 'assets'
DATA_DIR = Path(os.environ.get('PYSNIPS_DATA_DIR', PROJECT_ROOT / 'data')).resolve()
USER_DATA_DIR = DATA_DIR / 'user_data'
SYSTEM_DATA_DIR = DATA_DIR / 'system_data'
SNIPS_DIR = USER_DATA_DIR / 'snips'
TRASH_DIR = USER_DATA_DIR / 'trash' / 'snips'
SETTINGS_DIR = SYSTEM_DATA_DIR / 'settings'
SEARCH_INDEX_DIR = SYSTEM_DATA_DIR / 'search_index'
LANGUAGES_DIR = ASSETS_DIR / 'languages'
THEMES_DIR = ASSETS_DIR / 'themes'
