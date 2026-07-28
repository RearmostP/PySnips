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

from math import ceil
from pathlib import Path
from typing import Mapping

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QTimer, Signal

from core.tools.common.app_paths import AppPaths
from core.tools.common.error_manager import AppDebugger
from core.tools.common.dynamic_ui_loader import create_dynamic_ui_loader # Use dynamic_ui_loader directly
from core.tools.markdown import MarkdownService
from core.tools.settings.snips_settings import load_snips_settings


DEFAULT_TITLE = "ללא כותרת"
CONTENT_FILE_MISSING = "קובץ התוכן לא נמצא."
MINIMUM_CARD_HEIGHT = 170
CONTENT_HEIGHT_PADDING = 12


class SnippetCard(create_dynamic_ui_loader(AppPaths.SNIPPET_CARD_UI)): # Inherit directly
    # Signals to be emitted by this widget
    edit_requested = Signal(dict)
    details_requested = Signal(dict)
    delete_requested = Signal(dict)

    def __init__(
        self,
        snippet_meta: dict,
        parent: QWidget | None = None,
        markdown_service: MarkdownService | None = None,
        card_height: int | None = None,
    ):
        super().__init__(parent) # Pass parent to the base class (QWidget loaded from UI)
        self.snippet_meta = snippet_meta
        self.markdown_service = markdown_service or MarkdownService()
        self.markdown_warnings: list[str] = []
        self.markdown_repairs: list[str] = []
        self._height_update_pending = False
        self._maximum_card_height = 600
        configured_height = (
            card_height
            if card_height is not None
            else load_snips_settings().display.snippet_card_height
        )
        self.set_card_height(configured_height)
        self.txt_content_preview.document().documentLayout().documentSizeChanged.connect(
            self._schedule_card_height_update
        )
        
        # Initialize UI and logic
        self.init_data()
        self.setup_logic()
        self._setup_styles() # Apply styles

    def init_data(self):
        """טוען את מטא-הנתונים ומציג אותם ב-UI."""
        AppDebugger.log(f"SnippetCard: טוען נתונים עבור שליף ID: {self.snippet_meta.get('id')}")
        
        # Set title
        self.lbl_title_label.setText(self._get_snippet_title(self.snippet_meta)) # Direct access to UI element

        self._render_snippet_content(self.snippet_meta)

    def setup_logic(self):
        """מחבר את כפתורי ה-UI לפונקציות הלוגיות."""
        AppDebugger.log("SnippetCard: מחבר אירועים ורכיבי ממשק...")
        self.btn_edit.clicked.connect(self._on_edit_button_clicked) # Direct connect
        self.btn_details.clicked.connect(self._on_details_button_clicked) # Direct connect
        self.btn_delete.clicked.connect(self._on_delete_button_clicked)

    def _get_snippet_title(self, snippet_meta: Mapping[str, object]) -> str:
        title = snippet_meta.get("title", DEFAULT_TITLE)
        return str(title) if title else DEFAULT_TITLE

    def set_card_height(self, height: int) -> None:
        self._maximum_card_height = max(300, min(int(height), 900))
        self._schedule_card_height_update()

    def _schedule_card_height_update(self, *_args) -> None:
        if self._height_update_pending:
            return
        self._height_update_pending = True
        QTimer.singleShot(0, self._apply_content_aware_height)

    def _apply_content_aware_height(self) -> None:
        self._height_update_pending = False
        document_layout = self.txt_content_preview.document().documentLayout()
        document_height = ceil(document_layout.documentSize().height())
        preview_height = (
            document_height
            + self.txt_content_preview.frameWidth() * 2
            + CONTENT_HEIGHT_PADDING
        )

        margins = self.main_layout.contentsMargins()
        header_height = (
            margins.top()
            + margins.bottom()
            + self.lbl_title_label.sizeHint().height()
            + self.details_edit_layout.sizeHint().height()
            + self.main_layout.spacing() * 2
        )
        desired_height = header_height + preview_height
        target_height = max(
            MINIMUM_CARD_HEIGHT,
            min(desired_height, self._maximum_card_height),
        )
        if self.minimumHeight() != target_height or self.maximumHeight() != target_height:
            self.setFixedHeight(target_height)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "_height_update_pending"):
            self._schedule_card_height_update()

    def _render_snippet_content(self, snippet_meta: Mapping[str, object]) -> None:
        content_file = snippet_meta.get("content_file", "")
        content_file_path = Path(str(content_file))

        if not content_file_path.is_file():
            self.txt_content_preview.setPlainText(CONTENT_FILE_MISSING)
            return

        try:
            snippet_id = str(snippet_meta.get("id") or content_file_path.resolve())
            result = self.markdown_service.load_or_render(
                snippet_id=snippet_id,
                source_path=content_file_path,
            )
            self.txt_content_preview.setHtml(result.html)
            self.markdown_warnings = result.warnings
            self.markdown_repairs = result.repairs
            for diagnostic in self.markdown_warnings:
                AppDebugger.log(f"SnippetCard Markdown diagnostic: {diagnostic}")
            for repair in self.markdown_repairs:
                AppDebugger.log(f"SnippetCard Markdown repair: {repair}")
        except Exception as error:
            AppDebugger.log(f"SnippetCard: רינדור Markdown נכשל: {error}")
            self.txt_content_preview.setPlainText(
                f"שגיאה ברינדור תוכן השליף: {error}"
            )

    def _on_edit_button_clicked(self):
        """מתודה הנקראת בלחיצה על כפתור העריכה, ומשדרת את הסיגנל."""
        self.edit_requested.emit(self.snippet_meta)

    def _on_details_button_clicked(self):
        """מתודה הנקראת בלחיצה על כפתור הפרטים, ומשדרת את הסיגנל."""
        self.details_requested.emit(self.snippet_meta)

    def _on_delete_button_clicked(self):
        self.delete_requested.emit(self.snippet_meta)

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
            QTextBrowser#txt_content_preview {
                background-color: #181818;
                color: #d4d4d4;
                border: 1px solid #2d2d2d;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
                font-family: 'Segoe UI', Arial, sans-serif;
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
            QPushButton#btn_delete {
                background-color: #8c1d18;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#btn_delete:hover {
                background-color: #b3261e;
            }
            QPushButton#btn_delete:pressed {
                background-color: #6f1713;
            }
        """)

    def get_view(self) -> QWidget:
        """מחזיר את מופע ה-UI לשימוש בווידג'ט אחר."""
        return self # In this model, the SnippetCard itself is the view.
