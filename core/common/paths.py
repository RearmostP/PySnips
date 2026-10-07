import os
import sys
from pathlib import Path

FROZEN = getattr(sys, 'frozen', False)
PROJECT_ROOT = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parents[2]
RESOURCE_ROOT = Path(getattr(sys, '_MEIPASS', PROJECT_ROOT)) if FROZEN else PROJECT_ROOT
ASSETS_DIR = RESOURCE_ROOT / 'assets'

# DATA_DIR הוא שורש הנתונים הניתנים לכתיבה, בנפרד מנתוני ההתקנה.
if os.environ.get('PYSNIPS_DATA_DIR'):
    DATA_DIR = Path(os.environ['PYSNIPS_DATA_DIR']).resolve()
elif FROZEN and sys.platform == 'win32':
    local_app_data = Path(os.environ.get('LOCALAPPDATA') or Path.home() / 'AppData' / 'Local')
    DATA_DIR = (local_app_data / 'PySnips').resolve()
else:
    DATA_DIR = PROJECT_ROOT / 'data'

USER_DATA_DIR = DATA_DIR / 'user_data'
SYSTEM_DATA_DIR = (RESOURCE_ROOT / 'data' if FROZEN else DATA_DIR) / 'system_data'
VERSION_FILE = SYSTEM_DATA_DIR / 'version.json'
CACHE_DIR = DATA_DIR / 'cache'
SNIPS_DIR = USER_DATA_DIR / 'snips'
TRASH_DIR = USER_DATA_DIR / 'trash' / 'snips'
SETTINGS_DIR = USER_DATA_DIR / 'settings'
SEARCH_INDEX_DIR = CACHE_DIR / 'search_index'
LANGUAGES_DIR = ASSETS_DIR / 'languages'
THEMES_DIR = ASSETS_DIR / 'themes'
