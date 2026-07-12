import json
from pathlib import Path
import re

from PySide6.QtWidgets import QWidget, QMessageBox
from PySide6.QtCore import Qt, Signal

from core.common.app_paths import AppPaths
from core.common.error_manager import AppDebugger, AppErrorHandler
from core.common.dynamic_ui_loader import create_dynamic_ui_loader # Use dynamic_ui_loader directly


# Helper function from SnippetManager, might be moved to a common utility later
def _sanitize(name: str) -> str:
    """הפוך שם קטגוריה לשם קובץ בטוח לשימוש במערכת קבצים."""
    safe = ''.join(c for c in (name or '') if c.isalnum() or c in (' ', '_', '-')).strip()
    if not safe:
        return 'uncategorized'
    return safe.replace(' ', '_')

# Helper function from SnippetManager, might be moved to a common utility later
def _make_content_filename(title: str, snippet_id: str, maxlen: int = 50) -> str:
    """בנייה של שם קובץ בטוח, קריא - דוגמה: my-snippet-title-7f3a2b1c.md"""
    slug = re.sub(r"[^\w\s-]", "", (title or '').strip(), flags=re.UNICODE)
    slug = re.sub(r"[\s]+", "-", slug).strip("-")[:maxlen].lower()
    if not slug:
        slug = 'snippet'
    short_id = snippet_id.replace('-', '')[:8]
    return f"{slug}-{short_id}.md"

# Helper function from SnippetManager, might be moved to a common utility later
def _save_content_file(file_path: Path, content: str) -> bool:
    """שמירת תוכן ה-snippet לקובץ markdown."""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        AppDebugger.log(f"💾 שומר תוכן snippet לדיסק: {file_path}")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        AppDebugger.log(f"✅ תוכן snippet שומר בהצלחה: {file_path}")
        return True
    except Exception as e:
        AppErrorHandler.handle_error(
            error_obj=e,
            user_message="שגיאה בשמירת תוכן ה-snippet",
            dev_message=str(e),
            severity="ERROR"
        )
        return False

# Helper function to update snips.json, might be moved to a common utility later
def _update_snippets_json(snippet_data: dict, category: str) -> bool:
    """עדכון ה-snips.json של הקטגוריה עם נתוני השליף המעודכנים."""
    try:
        safe_cat = _sanitize(category)
        dir_path = AppPaths.SNIPS_FILES / safe_cat
        dir_path.mkdir(parents=True, exist_ok=True)

        snippets_file = dir_path / "snips.json"
        snippets = []

        if snippets_file.exists():
            with open(snippets_file, 'r', encoding='utf-8') as f:
                try:
                    snippets = json.load(f)
                except json.JSONDecodeError:
                    AppDebugger.log(f"⚠️ נכשל בפענוח snippets.json: {snippets_file}, מתחיל מחדש")
                    snippets = []

        # Find and update the existing snippet or add if new (though this widget is for editing existing)
        updated = False
        for i, snip in enumerate(snippets):
            if snip.get('id') == snippet_data.get('id'):
                snippets[i] = snippet_data
                updated = True
                break
        if not updated: # Should not happen for an edit widget, but as a fallback
            snippets.append(snippet_data)

        with open(snippets_file, 'w', encoding='utf-8') as f:
            json.dump(snippets, f, ensure_ascii=False, indent=2)
        AppDebugger.log(f"✅ אינדקס snippets עודכן בהצלחה: {snippets_file}")
        return True
    except Exception as e:
        AppErrorHandler.handle_error(
            error_obj=e,
            user_message=f"שגיאה בעדכון snips.json של הקטגוריה '{category}'",
            dev_message=str(e),
            severity="ERROR"
        )
        return False


class EditCardWidget(create_dynamic_ui_loader(AppPaths.EDIT_CARD_WIDGET)): # Inherit directly
    """
    מחלקה זו מכילה את הלוגיקה לעריכת שליף קיים.
    היא יורשת מ-create_dynamic_ui_loader ומקבלת את מופע ה-UI.
    """
    def __init__(self, snippet_meta: dict, on_save_callback, on_cancel_callback, parent: QWidget | None = None):
        super().__init__(parent) # Pass parent to the base class (QWidget loaded from UI)
        self.snippet_meta = snippet_meta
        self.on_save_callback = on_save_callback
        self.on_cancel_callback = on_cancel_callback
        
        # Initialize UI and logic
        self.init_data()
        self.setup_logic()

    def init_data(self):
        """טוען את תוכן השליף לתיבת העריכה."""
        AppDebugger.log(f"EditCardWidget: טוען תוכן עבור שליף ID: {self.snippet_meta.get('id')}")
        content_file_path = Path(self.snippet_meta.get('content_file', ''))
        if content_file_path.exists():
            try:
                with open(content_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.txt_snippet_content.setPlainText(content) # Direct access to UI element
            except Exception as e:
                AppErrorHandler.handle_error(
                    error_obj=e,
                    user_message="שגיאה בטעינת תוכן השליף לעריכה.",
                    dev_message=f"EditCardWidget: Error loading snippet content: {str(e)}",
                    severity="ERROR"
                )
        else:
            AppDebugger.log(f"EditCardWidget: קובץ תוכן לא נמצא עבור שליף ID: {self.snippet_meta.get('id')}")
            QMessageBox.warning(self, "שגיאה", "קובץ תוכן השליף לא נמצא.")

    def setup_logic(self):
        """מחבר את כפתורי השמירה והביטול לפונקציות המתאימות."""
        AppDebugger.log("EditCardWidget: מחבר אירועים ורכיבי ממשק...")
        self.btn_save_edit.clicked.connect(self._save_snippet) # Direct connect
        self.btn_cancel_edit.clicked.connect(self._cancel_edit) # Direct connect

    def _save_snippet(self):
        """שומר את תוכן השליף הערוך ומפעיל את ה-callback לשמירה."""
        AppDebugger.log(f"EditCardWidget: שומר שליף ID: {self.snippet_meta.get('id')}")
        new_content = self.txt_snippet_content.toPlainText() # Direct access to UI element
        content_file_path = Path(self.snippet_meta.get('content_file', ''))

        if _save_content_file(content_file_path, new_content):
            # QMessageBox.information(self, "הצלחה", "השליף נשמר בהצלחה!") # Removed this line
            self.on_save_callback(self.snippet_meta) # Pass updated meta back
        else:
            QMessageBox.warning(self, "שגיאה", "נכשלה שמירת השליף.")

    def _cancel_edit(self):
        """מבטל את העריכה ומפעיל את ה-callback לביטול."""
        AppDebugger.log("EditCardWidget: מבטל עריכת שליף.")
        self.on_cancel_callback()

    def get_view(self) -> QWidget:
        """מחזיר את מופע ה-UI לשימוש בווידג'ט אחר."""
        return self # In this model, the EditCardWidget itself is the view.