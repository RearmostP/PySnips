# ui file
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QHBoxLayout, QPushButton
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt, Signal # Added Signal

from core.screens.ui_logic.snips.widget.snippet_card import (
    get_snippet_title,
    read_snippet_content,
)


class SnippetCardWidget(QWidget):
    # הגדרת סיגנל מותאם אישית שישדר את מטא-הנתונים של השליף
    edit_requested = Signal(dict)
    details_requested = Signal(dict) # Signal for details button

    def __init__(self, snippet_meta: dict, parent=None):
        super().__init__(parent)
        self.snippet_meta = snippet_meta
        self.full_content = ""

        # פתרון ברמת ה-C++: אכיפת החלפת פונטים גלובלית עבור מנוע הרינדור הפנימי של התיבה
        QFont.insertSubstitution("monospace", "JetBrains Mono")
        QFont.insertSubstitution("Courier", "JetBrains Mono")
        QFont.insertSubstitution("Courier New", "JetBrains Mono")

        self.init_ui()
        self.load_content()
        self.setup_styles()

    def init_ui(self):
        """בניית מבנה הרכיבים הפנימיים ללא כפתורים צפים."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(6)

        # כותרת
        self.title_label = QLabel(get_snippet_title(self.snippet_meta))
        self.title_label.setObjectName("SnippetTitle")
        main_layout.addWidget(self.title_label)

        # כפתור פרטים וכפתור עריכה ב-QHBoxLayout
        details_edit_layout = QHBoxLayout()
        details_edit_layout.setContentsMargins(0, 0, 0, 0)
        details_edit_layout.setSpacing(5)

        # כפתור פרטים
        self.btn_details = QPushButton("פרטים")
        self.btn_details.setObjectName("DetailsButton")
        self.btn_details.setFixedSize(60, 25) # גודל קבוע לכפתור
        self.btn_details.setCursor(Qt.CursorShape.PointingHandCursor) # סמן יד
        self.btn_details.clicked.connect(self._on_details_button_clicked) # Connect details button
        details_edit_layout.addWidget(self.btn_details)

        # Spacer כדי לדחוף את כפתור העריכה לשמאל
        details_edit_layout.addStretch(1)

        # כפתור עריכה
        self.btn_edit = QPushButton("ערוך")
        self.btn_edit.setObjectName("EditButton")
        self.btn_edit.setFixedSize(60, 25) # גודל קבוע לכפתור
        self.btn_edit.setCursor(Qt.CursorShape.PointingHandCursor) # סמן יד
        self.btn_edit.clicked.connect(self._on_edit_button_clicked) # Connect edit button
        details_edit_layout.addWidget(self.btn_edit)

        main_layout.addLayout(details_edit_layout)

        # תיבת תצוגה מקדימה של הקוד (Markdown)
        self.content_preview = QTextEdit()
        self.content_preview.setReadOnly(True)
        self.content_preview.setMinimumHeight(300)
        self.content_preview.setMaximumHeight(450)
        main_layout.addWidget(self.content_preview)

    def load_content(self):
        """טעינת הקוד מתוך הקובץ הפיזי ורינדור כ-Markdown נקי."""
        snippet_content = read_snippet_content(self.snippet_meta)
        self.full_content = snippet_content.text

        if snippet_content.is_markdown:
            self.content_preview.setMarkdown(snippet_content.text)
        else:
            self.content_preview.setText(snippet_content.text)

    def _on_edit_button_clicked(self):
        """מתודה הנקראת בלחיצה על כפתור העריכה, ומשדרת את הסיגנל."""
        self.edit_requested.emit(self.snippet_meta)

    def _on_details_button_clicked(self):
        """מתודה הנקראת בלחיצה על כפתור הפרטים, ומשדרת את הסיגנל."""
        self.details_requested.emit(self.snippet_meta)

    def setup_styles(self):
        """הגדרת עיצוב כהה מורחב התומך באלמנטים של Markdown וגופן קוד מותאם אישית."""
        self.setStyleSheet("""
            SnippetCardWidget {
                background-color: #202020;
                border: 1px solid #2d2d2d;
                border-radius: 6px;
            }
            QLabel#SnippetTitle {
                font-weight: bold;
                font-size: 14px;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            /* הסרנו את QLabel#SnippetTags */

            QTextEdit {
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

            /* עיצוב המעטפת והגופן של הבלוקים של הקוד */
            QTextEdit code, QTextEdit pre {
                background-color: #282828;
                color: #f8f8f2;
                font-family: 'JetBrains Mono', monospace; 
                font-size: 12px;
                border-radius: 3px;
            }
            QPushButton#EditButton {
                background-color: #007bff; /* כחול */
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#EditButton:hover {
                background-color: #0056b3; /* כחול כהה יותר בריחוף */
            }
            QPushButton#EditButton:pressed {
                background-color: #004085; /* כחול כהה בלחיצה */
            }
            QPushButton#DetailsButton {
                background-color: #6c757d; /* אפור */
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton#DetailsButton:hover {
                background-color: #5a6268; /* אפור כהה יותר בריחוף */
            }
            QPushButton#DetailsButton:pressed {
                background-color: #495057; /* אפור כהה בלחיצה */
            }
        """)