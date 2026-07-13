# תפקיד הקובץ:
# שכבת עבודה כללית מול קבצי הגדרות JSON.
# הקובץ לא מכיר הגדרות ספציפיות של מסך או פיצ'ר, אלא מספק טעינה, שמירה,
# מיזוג עם ערכי ברירת מחדל, וטיפול בסיסי בקבצים חסרים או לא תקינים.

import json
from pathlib import Path
from typing import Any

from core.tools.common.error_manager import AppErrorHandler


def load_json_settings(settings_path: Path, defaults: dict[str, Any]) -> dict[str, Any]:
    if not settings_path.exists():
        return dict(defaults)

    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)

        if not isinstance(settings, dict):
            return dict(defaults)

        return _merge_defaults(defaults, settings)
    except Exception as e:
        AppErrorHandler.handle_error(
            error_obj=e,
            user_message="שגיאה בטעינת קובץ הגדרות",
            dev_message=f"מאגר ההגדרות: טעינת ההגדרות נכשלה מהנתיב {settings_path}: {str(e)}",
            severity="WARNING",
            show_gui=False,
        )
        return dict(defaults)


def save_json_settings(settings_path: Path, settings: dict[str, Any]) -> bool:
    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        AppErrorHandler.handle_error(
            error_obj=e,
            user_message="שגיאה בשמירת קובץ הגדרות",
            dev_message=f"מאגר ההגדרות: שמירת ההגדרות נכשלה לנתיב {settings_path}: {str(e)}",
            severity="ERROR",
        )
        return False


def _merge_defaults(defaults: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    merged = dict(defaults)
    for key, value in settings.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_defaults(merged[key], value)
        else:
            merged[key] = value
    return merged
