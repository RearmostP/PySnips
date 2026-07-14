# תפקיד הקובץ:
# מנהל את אשפת השליפים והקטגוריות.
# הקובץ מפריד בין לוגיקת אשפה של שליף יחיד לבין לוגיקת אשפה של קטגוריה,
# תוך שמירה על פונקציות מעטפת קיימות כדי שקוד שכבר משתמש במודול לא יישבר.

import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from core.tools.common.app_paths import AppPaths
from core.tools.common.error_manager import AppDebugger, AppErrorHandler
from core.tools.settings.snips_settings import DEFAULT_TRASH_RETENTION_DAYS, load_snips_trash_settings


# ----------------------------------------------------------------------
# קבועים כלליים
# ----------------------------------------------------------------------
TRASH_RETENTION_DAYS = DEFAULT_TRASH_RETENTION_DAYS


# ----------------------------------------------------------------------
# ניהול אשפה של שליפים בודדים
# ----------------------------------------------------------------------
class SnippetTrashManager:
    """מנהל מחיקה, שחזור וניקוי אשפה של שליפים בודדים."""

    # ------------------------------------------------------------------
    # פעולות ציבוריות על שליף יחיד
    # ------------------------------------------------------------------
    def move_to_trash(self, snippet_meta: dict) -> bool:
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
                return self.delete_snippet_permanently(snippet_meta, content_file)

            category = str(snippet_meta.get("category") or "")
            deleted_at = datetime.now().isoformat(timespec="seconds")
            trash_dir = self._create_trash_dir(snippet_id)
            trash_content_file = trash_dir / content_file.name
            trash_meta_file = trash_dir / "snippet.json"

            trash_dir.mkdir(parents=True, exist_ok=False)
            shutil.move(str(content_file), str(trash_content_file))

            trash_record = {
                "type": "snippet",
                "deleted_at": deleted_at,
                "original_category": category,
                "original_content_file": str(content_file),
                "trash_content_file": str(trash_content_file),
                "snippet": {
                    **snippet_meta,
                    "content_file": str(content_file),
                },
            }

            self._write_json(trash_meta_file, trash_record)

            if not self._remove_snippet_from_category_index(snippet_meta):
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

    def restore_trash_item(self, trash_item_dir: str | Path) -> bool:
        trash_item_path = Path(trash_item_dir)
        trash_record = self._read_trash_record(trash_item_path)
        if not trash_record or trash_record.get("type", "snippet") != "snippet":
            return False

        try:
            snippet_meta = dict(trash_record.get("snippet") or {})
            original_content_file = Path(str(trash_record.get("original_content_file") or ""))
            trash_content_file = Path(str(trash_record.get("trash_content_file") or ""))
            if not trash_content_file.exists():
                AppDebugger.log(f"מנהל אשפת שליפים: קובץ התוכן באשפה חסר: {trash_content_file}")
                return False

            restore_target = self._resolve_restore_target(original_content_file)
            restore_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(trash_content_file), str(restore_target))

            snippet_meta["content_file"] = str(restore_target)
            snippet_meta["category"] = str(trash_record.get("original_category") or snippet_meta.get("category") or "")

            if not self._add_snippet_to_category_index(snippet_meta):
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

    def list_deleted_snippets(self) -> list[dict]:
        trash_items = []
        for trash_item_dir in self._iter_snippet_trash_dirs():
            trash_record = self._read_trash_record(trash_item_dir)
            if not trash_record or trash_record.get("type", "snippet") != "snippet":
                continue

            trash_record["trash_dir"] = str(trash_item_dir)
            trash_items.append(trash_record)

        return self._sort_trash_items(trash_items)

    def cleanup_old_trash_items(self, retention_days: int | None = None) -> int:
        deleted_count = 0
        try:
            if retention_days is None:
                retention_days = load_snips_trash_settings().retention_days

            cutoff = datetime.now() - timedelta(days=retention_days)
            for trash_item_dir in self._iter_all_trash_item_dirs():
                deleted_at = self._read_deleted_at(trash_item_dir)
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

    def permanently_delete_trash_item(self, trash_item_dir: str | Path) -> bool:
        try:
            trash_item_path = Path(trash_item_dir)
            if not trash_item_path.exists():
                return True
            if not self._is_safe_trash_path(trash_item_path):
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

    def delete_snippet_permanently(self, snippet_meta: dict, content_file: Path) -> bool:
        snippet_id = str(snippet_meta.get("id") or "").strip()
        try:
            content_file.unlink()
        except FileNotFoundError:
            pass

        if not self._remove_snippet_from_category_index(snippet_meta):
            AppDebugger.log(f"מנהל אשפת שליפים: התוכן נמחק, אבל עדכון snips.json נכשל עבור {snippet_id}")
            return False

        AppDebugger.log(f"מנהל אשפת שליפים: השליף נמחק לצמיתות: {snippet_id}")
        return True

    # ------------------------------------------------------------------
    # איתור וניווט בתוך תיקיות האשפה
    # ------------------------------------------------------------------
    def _iter_snippet_trash_dirs(self) -> list[Path]:
        trash_root = AppPaths.SNIPS_TRASH_DIR
        if not trash_root.exists():
            return []

        return [
            trash_item_dir for trash_item_dir in trash_root.iterdir()
            if trash_item_dir.is_dir() and trash_item_dir != self._category_trash_root()
        ]

    def _iter_all_trash_item_dirs(self) -> list[Path]:
        trash_dirs = self._iter_snippet_trash_dirs()
        category_trash_root = self._category_trash_root()
        if category_trash_root.exists():
            trash_dirs.extend(path for path in category_trash_root.iterdir() if path.is_dir())
        return trash_dirs

    def _category_trash_root(self) -> Path:
        return AppPaths.SNIPS_TRASH_DIR / "categories"

    def _is_safe_trash_path(self, trash_item_path: Path) -> bool:
        trash_item_path = trash_item_path.resolve()
        allowed_parents = [
            AppPaths.SNIPS_TRASH_DIR.resolve(),
            self._category_trash_root().resolve(),
        ]
        return trash_item_path.is_dir() and trash_item_path.parent in allowed_parents

    # ------------------------------------------------------------------
    # קריאת רשומות אשפה וזמני מחיקה
    # ------------------------------------------------------------------
    def _read_trash_record(self, trash_item_dir: Path) -> dict | None:
        for meta_name in ("snippet.json", "category.json"):
            trash_meta_file = trash_item_dir / meta_name
            if not trash_meta_file.exists():
                continue
            try:
                with open(trash_meta_file, "r", encoding="utf-8") as f:
                    trash_record = json.load(f)
                if isinstance(trash_record, dict):
                    return trash_record
            except (OSError, json.JSONDecodeError):
                return None
        return None

    def _read_deleted_at(self, trash_item_dir: Path) -> datetime | None:
        try:
            trash_record = self._read_trash_record(trash_item_dir)
            if not trash_record:
                return None
            deleted_at = trash_record.get("deleted_at")
            if not deleted_at:
                return None
            return datetime.fromisoformat(str(deleted_at))
        except ValueError:
            return None

    def _create_trash_dir(self, item_id: str) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_id = self._sanitize(item_id)
        return AppPaths.SNIPS_TRASH_DIR / f"{timestamp}_{safe_id}"

    # ------------------------------------------------------------------
    # עדכון אינדקס השליפים של קטגוריה
    # ------------------------------------------------------------------
    def _remove_snippet_from_category_index(self, snippet_meta: dict) -> bool:
        category = str(snippet_meta.get("category") or "").strip()
        snippet_id = str(snippet_meta.get("id") or "").strip()
        if not category or not snippet_id:
            return False

        snips_json_path = AppPaths.SNIPS_FILES / self._sanitize(category) / "snips.json"
        snippets = self._read_snippets_file(snips_json_path)
        if snippets is None:
            return False

        updated_snippets = [
            item for item in snippets
            if not (isinstance(item, dict) and item.get("id") == snippet_id)
        ]

        self._write_json(snips_json_path, updated_snippets)
        return len(updated_snippets) != len(snippets)

    def _add_snippet_to_category_index(self, snippet_meta: dict) -> bool:
        category = str(snippet_meta.get("category") or "").strip()
        snippet_id = str(snippet_meta.get("id") or "").strip()
        if not category or not snippet_id:
            return False

        snips_json_path = AppPaths.SNIPS_FILES / self._sanitize(category) / "snips.json"
        snippets = self._read_snippets_file(snips_json_path) or []

        snippets = [
            item for item in snippets
            if not (isinstance(item, dict) and item.get("id") == snippet_id)
        ]
        snippets.append(snippet_meta)

        self._write_json(snips_json_path, snippets)
        return True

    def _read_snippets_file(self, snips_json_path: Path) -> list[dict] | None:
        if not snips_json_path.exists():
            return None

        with open(snips_json_path, "r", encoding="utf-8") as f:
            snippets = json.load(f)

        if not isinstance(snippets, list):
            return None
        return snippets

    # ------------------------------------------------------------------
    # שחזור נתיבים ומיון רשומות
    # ------------------------------------------------------------------
    def _resolve_restore_target(self, original_content_file: Path) -> Path:
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

    def _sort_trash_items(self, trash_items: list[dict]) -> list[dict]:
        return sorted(
            trash_items,
            key=lambda item: str(item.get("deleted_at") or ""),
            reverse=True,
        )

    # ------------------------------------------------------------------
    # קריאה וכתיבה של קבצי קטגוריות ו-JSON
    # ------------------------------------------------------------------
    def _read_categories_index(self) -> list[str]:
        if not AppPaths.CATEGORYS_JSON.exists():
            return []
        with open(AppPaths.CATEGORYS_JSON, "r", encoding="utf-8") as f:
            categories = json.load(f)
        return categories if isinstance(categories, list) else []

    def _write_categories_index(self, categories: list[str]) -> None:
        AppPaths.CATEGORYS_JSON.parent.mkdir(parents=True, exist_ok=True)
        self._write_json(AppPaths.CATEGORYS_JSON, categories)

    def _write_json(self, path: Path, data: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _sanitize(self, name: str) -> str:
        safe = "".join(c for c in (name or "") if c.isalnum() or c in (" ", "_", "-")).strip()
        if not safe:
            return "uncategorized"
        return safe.replace(" ", "_")


# ----------------------------------------------------------------------
# ניהול אשפה של קטגוריות
# ----------------------------------------------------------------------
class CategoryTrashManager(SnippetTrashManager):
    """מנהל מחיקה, שחזור וניקוי אשפה של קטגוריות שליפים."""

    # ------------------------------------------------------------------
    # פעולות ציבוריות על קטגוריה
    # ------------------------------------------------------------------
    def move_category_to_trash(self, category_name: str) -> bool:
        try:
            category_name = str(category_name or "").strip()
            if not category_name:
                AppDebugger.log("מנהל אשפת קטגוריות: חסר שם קטגוריה.")
                return False

            category_dir = AppPaths.SNIPS_FILES / self._sanitize(category_name)
            if not category_dir.exists() or not category_dir.is_dir():
                AppDebugger.log(f"מנהל אשפת קטגוריות: תיקיית הקטגוריה חסרה: {category_dir}")
                return False

            trash_settings = load_snips_trash_settings()
            if trash_settings.delete_permanently:
                return self.delete_category_permanently(category_name)

            deleted_at = datetime.now().isoformat(timespec="seconds")
            trash_dir = self._create_category_trash_dir(category_name)
            trash_category_dir = trash_dir / category_dir.name
            trash_record_path = trash_dir / "category.json"
            snippets = self._read_snippets_file(category_dir / "snips.json") or []

            trash_dir.mkdir(parents=True, exist_ok=False)
            shutil.move(str(category_dir), str(trash_category_dir))

            trash_record = {
                "type": "category",
                "deleted_at": deleted_at,
                "original_category": category_name,
                "original_category_dir": str(category_dir),
                "trash_category_dir": str(trash_category_dir),
                "snippets": snippets,
            }
            self._write_json(trash_record_path, trash_record)
            self._remove_category_from_index(category_name)

            AppDebugger.log(f"מנהל אשפת קטגוריות: הקטגוריה הועברה לאשפה: {category_name}")
            return True

        except Exception as e:
            AppErrorHandler.handle_error(
                error_obj=e,
                user_message="שגיאה בהעברת הקטגוריה לאשפה",
                dev_message=f"מנהל אשפת קטגוריות: העברת קטגוריה לאשפה נכשלה: {str(e)}",
                severity="ERROR",
            )
            return False

    def restore_category_trash_item(self, trash_item_dir: str | Path) -> bool:
        trash_item_path = Path(trash_item_dir)
        trash_record = self._read_trash_record(trash_item_path)
        if not trash_record or trash_record.get("type") != "category":
            return False

        try:
            original_category = str(trash_record.get("original_category") or "").strip()
            trash_category_dir = Path(str(trash_record.get("trash_category_dir") or ""))
            if not original_category or not trash_category_dir.exists():
                AppDebugger.log(f"מנהל אשפת קטגוריות: חסר מידע לשחזור קטגוריה: {trash_item_path}")
                return False

            restored_category_name, restore_target = self._resolve_category_restore_target(original_category)
            restore_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(trash_category_dir), str(restore_target))
            self._normalize_restored_category_files(restore_target, restored_category_name)
            self._add_category_to_index(restored_category_name)

            shutil.rmtree(trash_item_path)
            AppDebugger.log(f"מנהל אשפת קטגוריות: הקטגוריה שוחזרה: {restored_category_name}")
            return True

        except Exception as e:
            AppErrorHandler.handle_error(
                error_obj=e,
                user_message="שגיאה בשחזור הקטגוריה",
                dev_message=f"מנהל אשפת קטגוריות: שחזור קטגוריה נכשל: {str(e)}",
                severity="ERROR",
            )
            return False

    def list_deleted_categories(self) -> list[dict]:
        trash_items = []
        category_trash_root = self._category_trash_root()
        if not category_trash_root.exists():
            return []

        for trash_item_dir in category_trash_root.iterdir():
            if not trash_item_dir.is_dir():
                continue
            trash_record = self._read_trash_record(trash_item_dir)
            if not trash_record or trash_record.get("type") != "category":
                continue

            trash_record["trash_dir"] = str(trash_item_dir)
            trash_items.append(trash_record)

        return self._sort_trash_items(trash_items)

    def delete_category_permanently(self, category_name: str) -> bool:
        category_name = str(category_name or "").strip()
        if not category_name:
            return False

        category_dir = AppPaths.SNIPS_FILES / self._sanitize(category_name)
        if category_dir.exists() and category_dir.is_dir():
            shutil.rmtree(category_dir)
        self._remove_category_from_index(category_name)
        AppDebugger.log(f"מנהל אשפת קטגוריות: הקטגוריה נמחקה לצמיתות: {category_name}")
        return True

    # ------------------------------------------------------------------
    # פעולות עזר ייעודיות לקטגוריות
    # ------------------------------------------------------------------
    def _create_category_trash_dir(self, category_name: str) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return self._category_trash_root() / f"{timestamp}_{self._sanitize(category_name)}"

    def _remove_category_from_index(self, category_name: str) -> None:
        category_key = category_name.strip()
        categories = self._read_categories_index()
        updated_categories = [
            category for category in categories
            if str(category).strip() != category_key
        ]
        self._write_categories_index(updated_categories)

    def _add_category_to_index(self, category_name: str) -> None:
        categories = self._read_categories_index()
        if not any(str(category).strip() == category_name.strip() for category in categories):
            categories.append(category_name)
        self._write_categories_index(categories)

    def _resolve_category_restore_target(self, original_category: str) -> tuple[str, Path]:
        base_name = original_category.strip()
        base_target = AppPaths.SNIPS_FILES / self._sanitize(base_name)
        if not base_target.exists():
            return base_name, base_target

        counter = 1
        while True:
            restored_category_name = f"{base_name} restored {counter}"
            candidate = AppPaths.SNIPS_FILES / self._sanitize(restored_category_name)
            if not candidate.exists():
                return restored_category_name, candidate
            counter += 1

    def _normalize_restored_category_files(self, category_dir: Path, category_name: str) -> None:
        snips_json_path = category_dir / "snips.json"
        snippets = self._read_snippets_file(snips_json_path) or []
        normalized_snippets = []

        for snippet in snippets:
            if not isinstance(snippet, dict):
                continue
            updated_snippet = dict(snippet)
            content_file = Path(str(updated_snippet.get("content_file") or ""))
            updated_snippet["category"] = category_name
            updated_snippet["content_file"] = str(category_dir / content_file.name)
            normalized_snippets.append(updated_snippet)

        self._write_json(snips_json_path, normalized_snippets)


# ----------------------------------------------------------------------
# מופעי ברירת מחדל לשימוש דרך פונקציות המודול
# ----------------------------------------------------------------------
_snippet_trash_manager = SnippetTrashManager()
_category_trash_manager = CategoryTrashManager()


# ----------------------------------------------------------------------
# API ציבורי קיים - שליפים
# ----------------------------------------------------------------------
def move_snippet_to_trash(snippet_meta: dict) -> bool:
    return _snippet_trash_manager.move_to_trash(snippet_meta)


def cleanup_old_trash_items(retention_days: int | None = None) -> int:
    return _snippet_trash_manager.cleanup_old_trash_items(retention_days)


def list_deleted_snippets() -> list[dict]:
    return _snippet_trash_manager.list_deleted_snippets()


def restore_trash_item(trash_item_dir: str | Path) -> bool:
    return _snippet_trash_manager.restore_trash_item(trash_item_dir)


def permanently_delete_trash_item(trash_item_dir: str | Path) -> bool:
    return _snippet_trash_manager.permanently_delete_trash_item(trash_item_dir)


# ----------------------------------------------------------------------
# API ציבורי חדש - קטגוריות
# ----------------------------------------------------------------------
def move_category_to_trash(category_name: str) -> bool:
    return _category_trash_manager.move_category_to_trash(category_name)


def restore_category_trash_item(trash_item_dir: str | Path) -> bool:
    return _category_trash_manager.restore_category_trash_item(trash_item_dir)


def list_deleted_categories() -> list[dict]:
    return _category_trash_manager.list_deleted_categories()


def permanently_delete_category_trash_item(trash_item_dir: str | Path) -> bool:
    return _category_trash_manager.permanently_delete_trash_item(trash_item_dir)
