"""
מטרת הקובץ: לוגיקה לכרטיסיית שליף (Snippet Card Logic)
-------------------------------------------------------
קובץ זה מכיל את הלוגיקה העסקית עבור כרטיסיית שליף בודדת.
הוא מופרד לחלוטין ממבנה ה-UI של הכרטיסייה, אשר מוגדר בקובץ `snippet_card.ui`.

תפקידים עיקריים:
1.  **טעינה והצגת נתונים**:
    *   `SnippetCard` יורש ישירות מ-`create_dynamic_ui_loader` ומקבל את מופע ה-UI (ה-QWidget שנטען מ-`.ui`).
    *   טוען את מטא-הנתונים של השליף (`snippet_meta`).
    *   אחראי על הצגת כותרת השליף ותוכנו (כולל רינדור Markdown) בתוך רכיבי ה-UI המתאימים.

2.  **ניהול אירועי UI**:
    *   מחבר את כפתורי "ערוך" ו"פרטים" (שב-UI) לפונקציות הלוגיות המתאימות.

3.  **שידור סיגנלים**:
    *   משדר סיגנלים (`edit_requested`, `details_requested`) כאשר המשתמש לוחץ על כפתורי "ערוך" או "פרטים",
        ומעביר את מטא-הנתונים של השליף למאזינים (לרוב מסך השליפים הראשי).

קובץ זה מבטיח הפרדה נקייה בין המראה (UI) להתנהגות (לוגיקה) של כרטיסיית השליף,
ומאפשר ניהול קל יותר של כל אחד מהרכיבים.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal

from core.tools.common.app_paths import AppPaths
from core.tools.common.error_manager import AppDebugger
from core.tools.common.dynamic_ui_loader import create_dynamic_ui_loader # Use dynamic_ui_loader directly


DEFAULT_TITLE = "ללא כותרת"
CONTENT_READ_ERROR = "שגיאה בקריאת תוכן השליף."
CONTENT_FILE_MISSING = "קובץ התוכן לא נמצא."


@dataclass(frozen=True)
class SnippetContent:
    text: str
    is_markdown: bool


class SnippetCard(create_dynamic_ui_loader(AppPaths.SNIPPET_CARD_UI)): # Inherit directly
    # Signals to be emitted by this widget
    edit_requested = Signal(dict)
    details_requested = Signal(dict)

    def __init__(self, snippet_meta: dict, parent: QWidget | None = None):
        super().__init__(parent) # Pass parent to the base class (QWidget loaded from UI)
        self.snippet_meta = snippet_meta
        
        # Initialize UI and logic
        self.init_data()
        self.setup_logic()
        self._setup_styles() # Apply styles

    def init_data(self):
        """טוען את מטא-הנתונים ומציג אותם ב-UI."""
        AppDebugger.log(f"SnippetCard: טוען נתונים עבור שליף ID: {self.snippet_meta.get('id')}")
        
        # Set title
        self.lbl_title_label.setText(self._get_snippet_title(self.snippet_meta)) # Direct access to UI element

        # Load and set content
        snippet_content = self._read_snippet_content(self.snippet_meta)
        if snippet_content.is_markdown:
            self.txt_content_preview.setMarkdown(snippet_content.text) # Direct access to UI element
        else:
            self.txt_content_preview.setPlainText(snippet_content.text) # Direct access to UI element

    def setup_logic(self):
        """מחבר את כפתורי ה-UI לפונקציות הלוגיות."""
        AppDebugger.log("SnippetCard: מחבר אירועים ורכיבי ממשק...")
        self.btn_edit.clicked.connect(self._on_edit_button_clicked) # Direct connect
        self.btn_details.clicked.connect(self._on_details_button_clicked) # Direct connect

    def _get_snippet_title(self, snippet_meta: Mapping[str, object]) -> str:
        title = snippet_meta.get("title", DEFAULT_TITLE)
        return str(title) if title else DEFAULT_TITLE

    def _read_snippet_content(self, snippet_meta: Mapping[str, object]) -> SnippetContent:
        content_file = snippet_meta.get("content_file", "")
        content_file_path = Path(str(content_file))

        if not content_file_path.exists():
            return SnippetContent(CONTENT_FILE_MISSING, is_markdown=False)

        try:
            return SnippetContent(
                content_file_path.read_text(encoding="utf-8"),
                is_markdown=True,
            )
        except OSError:
            return SnippetContent(CONTENT_READ_ERROR, is_markdown=False)

    def _on_edit_button_clicked(self):
        """מתודה הנקראת בלחיצה על כפתור העריכה, ומשדרת את הסיגנל."""
        self.edit_requested.emit(self.snippet_meta)

    def _on_details_button_clicked(self):
        """מתודה הנקראת בלחיצה על כפתור הפרטים, ומשדרת את הסיגנל."""
        self.details_requested.emit(self.snippet_meta)

    def _setup_styles(self):
        """הגדרת עיצוב כהה מורחב התומך באלמנטים של Markdown וגופן קוד מותאם אישית."""
        # This styling should ideally be in the UI file or a separate stylesheet.
        # For now, keeping it here as it was in the original Python UI file.
        self.setStyleSheet("""
            QWidget#SnippetCardWidget { /* Use the objectName from the .ui file */
                background-color: #202020;
                border: 1px solid #2d2d2d;
                border-radius: 6px;
            }
            QLabel#lbl_title_label { /* Use the objectName from the .ui file */
                font-weight: bold;
                font-size: 14px;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QTextEdit#txt_content_preview { /* Use the objectName from the .ui file */
                background-color: #181818;
                color: #d4d4d4;
                border: 1px solid #2d2d2d;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QTextEdit h1 { color: #ffffff; font-weight: bold; font-size: 1.6em; margin-top: 6px; margin-bottom: 4px; }
            QTextEdit h2 { color: #eeeeee; font-weight: bold; font-size: 1.4em; margin-top: 5px; margin-bottom: 3px; }
            QTextEdit h3 { color: #e0e0e0; font-weight: bold; font-size: 1.2em; margin-top: 4px; margin-bottom: 2px; }
            QTextEdit h4 { color: #d0d0d0; font-weight: bold; font-size: 1.05em; margin-top: 4px; margin-bottom: 2px; }
            QTextEdit code, QTextEdit pre {
                background-color: #282828;
                color: #f8f8f2;
                font-family: 'JetBrains Mono', monospace; 
                font-size: 12px;
                border-radius: 3px;
            }
            QPushButton#btn_edit { /* Use the objectName from the .ui file */
                background-color: #007bff; /* כחול */
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#btn_edit:hover {
                background-color: #0056b3; /* כחול כהה יותר בריחוף */
            }
            QPushButton#btn_edit:pressed {
                background-color: #004085; /* כחול כהה בלחיצה */
            }
            QPushButton#btn_details { /* Use the objectName from the .ui file */
                background-color: #6c757d; /* אפור */
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#btn_details:hover {
                background-color: #5a6268; /* אפור כהה יותר בריחוף */
            }
            QPushButton#btn_details:pressed {
                background-color: #495057; /* אפור כהה בלחיצה */
            }
        """)

    def get_view(self) -> QWidget:
        """מחזיר את מופע ה-UI לשימוש בווידג'ט אחר."""
        return self # In this model, the SnippetCard itself is the view.