# תפקיד הקובץ:
# מגדיר את מבנה ההגדרות של מערכת השליפים.
# כרגע הוא מנהל את הגדרות אשפת השליפים, כולל מספר ימי שמירה לפני מחיקה
# והאם למחוק שליפים לצמיתות מיד. הקריאה והכתיבה בפועל נעשות דרך settings_store.

from dataclasses import asdict, dataclass
from pathlib import Path

from core.tools.common.app_paths import AppPaths
from core.tools.common.error_manager import AppDebugger
from core.tools.settings.settings_store import load_json_settings, save_json_settings


DEFAULT_TRASH_RETENTION_DAYS = 30


@dataclass
class SnipsTrashSettings:
    retention_days: int = DEFAULT_TRASH_RETENTION_DAYS
    delete_permanently: bool = False


@dataclass
class SnipsCategorySettings:
    pinned_category: str = ""


@dataclass
class SnipsSettings:
    trash: SnipsTrashSettings
    categories: SnipsCategorySettings


DEFAULT_SNIPS_SETTINGS = {
    "trash": {
        "retention_days": DEFAULT_TRASH_RETENTION_DAYS,
        "delete_permanently": False,
    },
    "categories": {
        "pinned_category": "",
    }
}


def load_snips_settings() -> SnipsSettings:
    raw_settings = load_json_settings(AppPaths.SNIPS_SETTINGS_JSON, DEFAULT_SNIPS_SETTINGS)
    raw_settings = _load_legacy_trash_settings(raw_settings)
    trash_settings = raw_settings.get("trash") or {}
    category_settings = raw_settings.get("categories") or {}
    return SnipsSettings(
        trash=SnipsTrashSettings(
            retention_days=_normalize_retention_days(trash_settings.get("retention_days")),
            delete_permanently=bool(trash_settings.get("delete_permanently", False)),
        ),
        categories=SnipsCategorySettings(
            pinned_category=str(category_settings.get("pinned_category") or ""),
        ),
    )


def save_snips_settings(settings: SnipsSettings) -> bool:
    normalized_settings = SnipsSettings(
        trash=SnipsTrashSettings(
            retention_days=_normalize_retention_days(settings.trash.retention_days),
            delete_permanently=bool(settings.trash.delete_permanently),
        ),
        categories=SnipsCategorySettings(
            pinned_category=str(settings.categories.pinned_category or ""),
        ),
    )

    if save_json_settings(AppPaths.SNIPS_SETTINGS_JSON, asdict(normalized_settings)):
        AppDebugger.log("הגדרות שליפים: הגדרות השליפים נשמרו.")
        return True
    return False


def load_snips_trash_settings() -> SnipsTrashSettings:
    return load_snips_settings().trash


def save_snips_trash_settings(settings: SnipsTrashSettings) -> bool:
    current_settings = load_snips_settings()
    current_settings.trash = settings
    return save_snips_settings(current_settings)


def load_pinned_snips_category() -> str:
    return load_snips_settings().categories.pinned_category


def save_pinned_snips_category(category: str) -> bool:
    current_settings = load_snips_settings()
    current_settings.categories.pinned_category = str(category or "")
    return save_snips_settings(current_settings)


def _load_legacy_trash_settings(raw_settings: dict) -> dict:
    if Path(AppPaths.SNIPS_SETTINGS_JSON).exists():
        return raw_settings

    legacy_path = AppPaths.SNIPS_DATA_DIR / "trash_settings.json"
    if not legacy_path.exists():
        return raw_settings

    legacy_settings = load_json_settings(legacy_path, {})
    if not legacy_settings:
        return raw_settings

    migrated_settings = dict(raw_settings)
    migrated_settings["trash"] = {
        "retention_days": legacy_settings.get("retention_days", DEFAULT_TRASH_RETENTION_DAYS),
        "delete_permanently": bool(legacy_settings.get("delete_permanently", False)),
    }
    return migrated_settings


def _normalize_retention_days(value: object) -> int:
    try:
        retention_days = int(value)
    except (TypeError, ValueError):
        retention_days = DEFAULT_TRASH_RETENTION_DAYS

    return max(1, min(retention_days, 365))
