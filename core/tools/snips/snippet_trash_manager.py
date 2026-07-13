# תפקיד הקובץ:
# מנהל את אשפת השליפים.
# אחראי על העברת שליף לאשפה, שחזור שליף, מחיקה לצמיתות, קריאת פריטי אשפה,
# וניקוי אוטומטי של פריטים שעברו את זמן השמירה שהוגדר.

import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from core.tools.common.app_paths import AppPaths
from core.tools.common.error_manager import AppDebugger, AppErrorHandler
from core.tools.settings.snips_settings import DEFAULT_TRASH_RETENTION_DAYS, load_snips_trash_settings


TRASH_RETENTION_DAYS = DEFAULT_TRASH_RETENTION_DAYS


def move_snippet_to_trash(snippet_meta: dict) -> bool:
    """מעביר את קובץ התוכן והמטא-דאטה של שליף לאשפת המשתמש."""
    try:
        snippet_id = str(snippet_meta.get("id") or "").strip()
        if not snippet_id:
            AppDebugger.log("מנהל אשפת שליפים: חסר מזהה שליף.")
            return False

        content_file = Path(str(snippet_meta.get("content_file") or ""))
        if not content_file.exists():
            AppDebugger.log(f"מנהל אשפת שליפים: קובץ התוכן חסר: {content_file}")
            return False

        trash_settings = load_snips_trash_settings()
        if trash_settings.delete_permanently:
            return _delete_snippet_permanently(snippet_meta, content_file)

        category = str(snippet_meta.get("category") or "")
        deleted_at = datetime.now().isoformat(timespec="seconds")
        trash_dir = _create_trash_dir(snippet_id)
        trash_content_file = trash_dir / content_file.name
        trash_meta_file = trash_dir / "snippet.json"

        trash_dir.mkdir(parents=True, exist_ok=False)
        shutil.move(str(content_file), str(trash_content_file))

        trash_record = {
            "deleted_at": deleted_at,
            "original_category": category,
            "original_content_file": str(content_file),
            "trash_content_file": str(trash_content_file),
            "snippet": {
                **snippet_meta,
                "content_file": str(content_file),
            },
        }

        with open(trash_meta_file, "w", encoding="utf-8") as f:
            json.dump(trash_record, f, ensure_ascii=False, indent=2)

        if not _remove_snippet_from_category_index(snippet_meta):
            AppDebugger.log(f"מנהל אשפת שליפים: התוכן הועבר, אבל עדכון snips.json נכשל עבור {snippet_id}")
            return False

        AppDebugger.log(f"מנהל אשפת שליפים: השליף הועבר לאשפה: {snippet_id}")
        return True

    except Exception as e:
        AppErrorHandler.handle_error(
            error_obj=e,
            user_message="שגיאה בהעברת השליף לאשפה",
            dev_message=f"מנהל אשפת שליפים: העברת השליף לאשפה נכשלה: {str(e)}",
            severity="ERROR",
        )
        return False


def cleanup_old_trash_items(retention_days: int | None = None) -> int:
    """מוחק לצמיתות פריטי אשפה שעברו את זמן השמירה שהוגדר."""
    deleted_count = 0
    try:
        if retention_days is None:
            retention_days = load_snips_trash_settings().retention_days

        trash_root = AppPaths.SNIPS_TRASH_DIR
        if not trash_root.exists():
            return deleted_count

        cutoff = datetime.now() - timedelta(days=retention_days)
        for trash_item_dir in trash_root.iterdir():
            if not trash_item_dir.is_dir():
                continue

            deleted_at = _read_deleted_at(trash_item_dir)
            if deleted_at is None or deleted_at >= cutoff:
                continue

            shutil.rmtree(trash_item_dir)
            deleted_count += 1
            AppDebugger.log(f"מנהל אשפת שליפים: פריט אשפה ישן נמחק לצמיתות: {trash_item_dir}")

        return deleted_count

    except Exception as e:
        AppErrorHandler.handle_error(
            error_obj=e,
            user_message="שגיאה בניקוי אשפת השליפים",
            dev_message=f"מנהל אשפת שליפים: ניקוי פריטי אשפה ישנים נכשל: {str(e)}",
            severity="WARNING",
            show_gui=False,
        )
        return deleted_count


def list_deleted_snippets() -> list[dict]:
    """מחזיר רשומות אשפה של שליפים, ממוינות מהמחיקה החדשה לישנה."""
    trash_root = AppPaths.SNIPS_TRASH_DIR
    if not trash_root.exists():
        return []

    trash_items = []
    for trash_item_dir in trash_root.iterdir():
        if not trash_item_dir.is_dir():
            continue

        trash_record = _read_trash_record(trash_item_dir)
        if not trash_record:
            continue

        trash_record["trash_dir"] = str(trash_item_dir)
        trash_items.append(trash_record)

    return sorted(
        trash_items,
        key=lambda item: str(item.get("deleted_at") or ""),
        reverse=True,
    )


def restore_trash_item(trash_item_dir: str | Path) -> bool:
    """משחזר שליף יחיד מהאשפה בחזרה לקטגוריה המקורית שלו."""
    trash_item_path = Path(trash_item_dir)
    trash_record = _read_trash_record(trash_item_path)
    if not trash_record:
        return False

    try:
        snippet_meta = dict(trash_record.get("snippet") or {})
        original_content_file = Path(str(trash_record.get("original_content_file") or ""))
        trash_content_file = Path(str(trash_record.get("trash_content_file") or ""))
        if not trash_content_file.exists():
            AppDebugger.log(f"מנהל אשפת שליפים: קובץ התוכן באשפה חסר: {trash_content_file}")
            return False

        restore_target = _resolve_restore_target(original_content_file)
        restore_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(trash_content_file), str(restore_target))

        snippet_meta["content_file"] = str(restore_target)
        snippet_meta["category"] = str(trash_record.get("original_category") or snippet_meta.get("category") or "")

        if not _add_snippet_to_category_index(snippet_meta):
            AppDebugger.log(f"מנהל אשפת שליפים: התוכן שוחזר, אבל עדכון snips.json נכשל: {trash_item_path}")
            return False

        shutil.rmtree(trash_item_path)
        AppDebugger.log(f"מנהל אשפת שליפים: פריט אשפה שוחזר: {trash_item_path}")
        return True

    except Exception as e:
        AppErrorHandler.handle_error(
            error_obj=e,
            user_message="שגיאה בשחזור השליף",
            dev_message=f"מנהל אשפת שליפים: שחזור פריט מהאשפה נכשל: {str(e)}",
            severity="ERROR",
        )
        return False


def permanently_delete_trash_item(trash_item_dir: str | Path) -> bool:
    """מוחק לצמיתות תיקיית פריט אשפה יחיד."""
    try:
        trash_item_path = Path(trash_item_dir)
        if not trash_item_path.exists():
            return True
        if not trash_item_path.is_dir() or trash_item_path.parent != AppPaths.SNIPS_TRASH_DIR:
            AppDebugger.log(f"מנהל אשפת שליפים: נתיב מחיקה לא בטוח באשפה: {trash_item_path}")
            return False

        shutil.rmtree(trash_item_path)
        AppDebugger.log(f"מנהל אשפת שליפים: פריט אשפה נמחק לצמיתות: {trash_item_path}")
        return True
    except Exception as e:
        AppErrorHandler.handle_error(
            error_obj=e,
            user_message="שגיאה במחיקת השליף לצמיתות",
            dev_message=f"מנהל אשפת שליפים: מחיקת פריט אשפה לצמיתות נכשלה: {str(e)}",
            severity="ERROR",
        )
        return False


def _delete_snippet_permanently(snippet_meta: dict, content_file: Path) -> bool:
    snippet_id = str(snippet_meta.get("id") or "").strip()
    try:
        content_file.unlink()
    except FileNotFoundError:
        pass

    if not _remove_snippet_from_category_index(snippet_meta):
        AppDebugger.log(f"מנהל אשפת שליפים: התוכן נמחק, אבל עדכון snips.json נכשל עבור {snippet_id}")
        return False

    AppDebugger.log(f"מנהל אשפת שליפים: השליף נמחק לצמיתות: {snippet_id}")
    return True


def _read_trash_record(trash_item_dir: Path) -> dict | None:
    trash_meta_file = trash_item_dir / "snippet.json"
    if not trash_meta_file.exists():
        return None

    try:
        with open(trash_meta_file, "r", encoding="utf-8") as f:
            trash_record = json.load(f)
        if not isinstance(trash_record, dict):
            return None
        return trash_record
    except (OSError, json.JSONDecodeError):
        return None


def _read_deleted_at(trash_item_dir: Path) -> datetime | None:
    try:
        trash_record = _read_trash_record(trash_item_dir)
        if not trash_record:
            return None
        deleted_at = trash_record.get("deleted_at")
        if not deleted_at:
            return None
        return datetime.fromisoformat(str(deleted_at))
    except ValueError:
        return None


def _create_trash_dir(snippet_id: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_id = "".join(c for c in snippet_id if c.isalnum() or c in ("-", "_"))
    return AppPaths.SNIPS_TRASH_DIR / f"{timestamp}_{safe_id}"


def _remove_snippet_from_category_index(snippet_meta: dict) -> bool:
    category = str(snippet_meta.get("category") or "").strip()
    snippet_id = str(snippet_meta.get("id") or "").strip()
    if not category or not snippet_id:
        return False

    snips_json_path = AppPaths.SNIPS_FILES / _sanitize(category) / "snips.json"
    if not snips_json_path.exists():
        return False

    with open(snips_json_path, "r", encoding="utf-8") as f:
        snippets = json.load(f)

    if not isinstance(snippets, list):
        return False

    updated_snippets = [
        item for item in snippets
        if not (isinstance(item, dict) and item.get("id") == snippet_id)
    ]

    with open(snips_json_path, "w", encoding="utf-8") as f:
        json.dump(updated_snippets, f, ensure_ascii=False, indent=2)

    return len(updated_snippets) != len(snippets)


def _add_snippet_to_category_index(snippet_meta: dict) -> bool:
    category = str(snippet_meta.get("category") or "").strip()
    snippet_id = str(snippet_meta.get("id") or "").strip()
    if not category or not snippet_id:
        return False

    snips_json_path = AppPaths.SNIPS_FILES / _sanitize(category) / "snips.json"
    snips_json_path.parent.mkdir(parents=True, exist_ok=True)

    snippets = []
    if snips_json_path.exists():
        with open(snips_json_path, "r", encoding="utf-8") as f:
            snippets = json.load(f)

    if not isinstance(snippets, list):
        snippets = []

    snippets = [
        item for item in snippets
        if not (isinstance(item, dict) and item.get("id") == snippet_id)
    ]
    snippets.append(snippet_meta)

    with open(snips_json_path, "w", encoding="utf-8") as f:
        json.dump(snippets, f, ensure_ascii=False, indent=2)

    return True


def _resolve_restore_target(original_content_file: Path) -> Path:
    if not original_content_file.exists():
        return original_content_file

    parent = original_content_file.parent
    stem = original_content_file.stem
    suffix = original_content_file.suffix
    counter = 1
    while True:
        candidate = parent / f"{stem}-restored-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _sanitize(name: str) -> str:
    safe = "".join(c for c in (name or "") if c.isalnum() or c in (" ", "_", "-")).strip()
    if not safe:
        return "uncategorized"
    return safe.replace(" ", "_")
