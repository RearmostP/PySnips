# תפקיד הקובץ:
# נקודת ייצוא נוחה לכלי השליפים.
# מרכז ייבואים של פעולות אשפה והגדרות אשפה כדי שמודולים אחרים יוכלו
# להשתמש בהן בלי להכיר את מבנה הקבצים הפנימי.

from core.tools.snips.snippet_trash_manager import (
    CategoryTrashManager,
    SnippetTrashManager,
    cleanup_old_trash_items,
    list_deleted_snippets,
    list_deleted_categories,
    move_category_to_trash,
    move_snippet_to_trash,
    permanently_delete_category_trash_item,
    permanently_delete_trash_item,
    restore_category_trash_item,
    restore_trash_item,
)
from core.tools.snips.snippet_metadata_manager import SnippetMetadataManager
from core.tools.snips.snippet_name_utils import sanitize_snippet_name
from core.tools.settings.snips_settings import (
    SnipsTrashSettings,
    load_snips_trash_settings,
    save_snips_trash_settings,
)

__all__ = [
    "CategoryTrashManager",
    "SnippetTrashManager",
    "SnippetMetadataManager",
    "cleanup_old_trash_items",
    "list_deleted_categories",
    "list_deleted_snippets",
    "move_category_to_trash",
    "move_snippet_to_trash",
    "permanently_delete_category_trash_item",
    "permanently_delete_trash_item",
    "restore_category_trash_item",
    "restore_trash_item",
    "sanitize_snippet_name",
]
