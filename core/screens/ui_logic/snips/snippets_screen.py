"""
מטרת הקובץ: לוגיקה למסך השליפים (Snippets Screen Logic)
--------------------------------------------------------
קובץ זה מכיל את הלוגיקה העסקית והאינטראקציה עם ממשק המשתמש עבור מסך השליפים הראשי.
הוא אחראי על הצגת קטגוריות השליפים, טעינת שליפים ספציפיים, ניהול אירועי UI
ופתיחת דיאלוגים רלוונטיים.

תפקידים עיקריים:
1.  **טעינה דינמית של UI**:
    *   הכיתה `SnippetsScreen` יורשת מ-`create_dynamic_ui_loader`, מה שמאפשר לה לטעון
        את מבנה ה-UI מקובץ `snippets_screen.ui` בזמן ריצה.

2.  **ניהול אירועי UI (setup_events)**:
    *   מחבר את כפתורי הניווט (תפריט, הוספת קטגוריה, הוספת שליף) לפונקציות הלוגיות המתאימות.
    *   מאתחל את תפריט ההמבורגר.

3.  **ניהול קטגוריות**:
    *   `load_category_buttons`: טוען את רשימת הקטגוריות הקיימות ומייצר עבורן כפתורים דינמיים.
    *   `_add_new_category`: מטפל ביצירת קטגוריה חדשה באמצעות דיאלוג קלט, כולל סניטציה ושמירה.
    *   `on_category_selected`: מגיב לבחירת קטגוריה על ידי המשתמש וטוען את השליפים המתאימים.

4.  **ניהול שליפים**:
    *   `_load_snips_to_content_box`: טוען את השליפים (snippets) של הקטגוריה הנבחרת ומציג אותם באמצעות `SnippetCardWidget`.
    *   `_create_snippet_widget`: פונקציית עזר ליצירת מופע של `SnippetCardWidget` עבור כל שליף.

5.  **ניווט ודיאלוגים**:
    *   `go_back_home`: מחזיר את המשתמש למסך הבית.
    *   `open_create_snips_dialog`: פותח את דיאלוג יצירת השליף החדש (`CreateSnipsDialog`).
    *   `open_settings`, `show_about`: פונקציות לטיפול בפתיחת חלונות הגדרות ו"אודות".

קובץ זה מהווה את הלב הפועם של ניהול השליפים באפליקציה, ומאפשר למשתמש אינטראקציה מלאה
עם השליפים והקטגוריות שלו.
"""

import json
from PySide6.QtWidgets import QMenu, QPushButton, QLabel, QSpacerItem, QSizePolicy, QInputDialog, QMessageBox
from PySide6.QtCore import Qt

from core.common.app_paths import AppPaths
from core.screens.ui_logic.snips.create_snips_dialog import CreateSnipsDialog

from core.screens.ui.snips.widgets.snippet_card import SnippetCardWidget
from core.common.dynamic_ui_loader import create_dynamic_ui_loader
from core.common.error_manager import AppDebugger, AppErrorHandler
from core.boot import get_categories, update_categories_file


def _sanitize(name: str) -> str:
    """הפוך שם קטגוריה לשם קובץ בטוח לשימוש במערכת קבצים."""
    safe = ''.join(c for c in (name or '') if c.isalnum() or c in (' ', '_', '-')).strip()
    if not safe:
        return 'uncategorized'
    return safe.replace(' ', '_')


class SnippetsScreen(create_dynamic_ui_loader(AppPaths.SNIPPETS_SCREEN)):
    def __init__(self, parent=None):
        super().__init__(parent)

    def setup_events(self):
        """
        פונקציה שמחברת את האירועים והכפתורים.
        נקראת רק לאחר שקובץ ה-UI נטען במלואו לזיכרון.
        """
        AppDebugger.log("SnippetsScreen: Connecting UI events and elements...")

        # בניית תפריט ההמבורגר
        self.setup_hamburger_menu()

        # טעינת כפתורי קטגוריות דינמיים
        self.load_category_buttons()

        # חיבור כפתור הוספת קטגוריה
        self.btn_add_category.clicked.connect(self._add_new_category)

        # חיבור כפתור הוספת שליף (אם קיים)
        self.btn_new_snippet.clicked.connect(self.open_create_snips_dialog) # This was commented out in the original

        # טעינת שליפים אחרונים או קטגוריה ראשונה כברירת מחדל
        self.on_category_selected("Recent Snippets")

    def setup_hamburger_menu(self):
        """מגדיר ומצמיד תפריט קופץ עבור כפתור התפריט"""
        self.hamburger_menu = QMenu(self)

        action_home = self.hamburger_menu.addAction("Home")
        action_settings = self.hamburger_menu.addAction("Settings")
        action_about = self.hamburger_menu.addAction("About")

        action_home.triggered.connect(self.go_back_home)
        action_settings.triggered.connect(self.open_settings)
        action_about.triggered.connect(self.show_about)

        self.btn_menu.setMenu(self.hamburger_menu)

    def load_category_buttons(self):
        """טעינת כפתורי קטגוריות דינמיים לתוך ה-scroll area"""
        try:
            AppDebugger.log("Loading category buttons to memory...")
            categories = get_categories()
            AppDebugger.log(f"Loaded {len(categories)} categories")

            layout = self.scl_categories.widget().layout()
            if not layout:
                AppDebugger.log("Error: Layout not found for categories")
                return

            # ניקוי כפתורים קיימים כדי למנוע כפילויות בריענון
            while layout.count() > 1:
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()

            # הוספת הכפתורים החדשים לפני ה-Spacer הנוכחי
            for category in categories:
                btn = QPushButton(f"Folder: {category}")
                btn.setMinimumHeight(35)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)

                # קיבוע משתנה ה-category בתוך הלמדא
                btn.clicked.connect(lambda checked, cat=category: self.on_category_selected(cat))

                layout.insertWidget(layout.count() - 1, btn)
                AppDebugger.log(f"Added button for category: {category}")

            AppDebugger.log(f"SnippetsScreen: Successfully loaded {len(categories)} categories")

        except Exception as e:
            AppErrorHandler.handle_error(
                error_obj=e,
                user_message="שגיאה בטעינת כפתורי קטגוריות",
                dev_message=f"SnippetsScreen: Error loading category buttons: {str(e)}",
                severity="ERROR"
            )

    def _add_new_category(self):
        """פתיחת דיאלוג ליצירת קטגוריה חדשה ושמירתה."""
        AppDebugger.log("SnippetsScreen: Opening dialog for new category...")
        category_name, ok = QInputDialog.getText(self, "New Category", "Enter category name:")

        if ok and category_name:
            sanitized_name = _sanitize(category_name)
            if not sanitized_name:
                QMessageBox.warning(self, "Invalid Name", "Category name cannot be empty or contain only special characters.")
                return

            try:
                # בדוק אם הקטגוריה כבר קיימת
                current_categories = get_categories()
                if sanitized_name in current_categories:
                    QMessageBox.information(self, "Category Exists", f"The category '{category_name}' already exists.")
                    return

                # יצירת תיקיית הקטגוריה
                category_dir = AppPaths.SNIPS_FILES / sanitized_name
                category_dir.mkdir(parents=True, exist_ok=True)
                AppDebugger.log(f"SnippetsScreen: Created category directory: {category_dir}")

                # עדכון קובץ ה-JSON של הקטגוריות
                update_categories_file(sanitized_name)
                AppDebugger.log(f"SnippetsScreen: Updated categorys.json with category: {sanitized_name}")

                QMessageBox.information(self, "Success", f"Category '{category_name}' created successfully!")
                self.load_category_buttons() # רענן את כפתורי הקטגוריות
                self.on_category_selected(sanitized_name) # בחר את הקטגוריה החדשה
            except Exception as e:
                AppErrorHandler.handle_error(
                    error_obj=e,
                    user_message=f"שגיאה ביצירת קטגוריה חדשה: {category_name}",
                    dev_message=f"SnippetsScreen: Error creating new category: {str(e)}",
                    severity="ERROR",
                    show_gui=True
                )
        elif ok and not category_name:
            QMessageBox.warning(self, "Empty Name", "Category name cannot be empty.")

    def on_category_selected(self, category: str):
        """קריאה כאשר משתמש לוחץ על כפתור קטגוריה"""
        AppDebugger.log(f"SnippetsScreen: Category selected: {category}")
        self.lbl_category_title.setText(f"Folder: {category}")
        self._load_snips_to_content_box(category)

    def _load_snips_to_content_box(self, category: str):
        """טוען את הקודים הקצרים (snippets) של קטגוריה מסוימת לתוך תיבת התוכן"""
        AppDebugger.log(f"SnippetsScreen: Loading snippets for category: {category}")

        layout = self.grid_snippets_layout
        if not layout:
            AppDebugger.log("Error: grid_snippets_layout not found for snippets")
            return

        # תיקון קריטי: ניקוי יסודי של ה-Layout כולל Spacers ישנים למניעת זליגת זיכרון
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            # אם הפריט הוא Spacer או Layout פנימי - נמחק את המשאב שלו מהזיכרון
            elif item.spacerItem():
                del item

        if category == "Recent Snippets":
            placeholder_label = QLabel("הצגת שליפים אחרונים (בפיתוח)")
            placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(placeholder_label, 0, 0)
            return

        safe_cat = _sanitize(category)
        category_dir = AppPaths.SNIPS_FILES / safe_cat
        snips_json_path = category_dir / "snips.json"

        if not snips_json_path.exists():
            AppDebugger.log(f"SnippetsScreen: Missing snips.json for category: {category}")
            no_snips_label = QLabel(f"אין שליפים בקטגוריה '{category}'")
            no_snips_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_snips_label, 0, 0)
            return

        try:
            with open(snips_json_path, 'r', encoding='utf-8') as f:
                snippets_metadata = json.load(f)

            row = 0
            for snippet_meta in snippets_metadata:
                snippet_widget = self._create_snippet_widget(snippet_meta)
                layout.addWidget(snippet_widget, row, 0)
                row += 1

            # הוספת spacer בסוף כדי למנוע מתיחה אנכית של הכרטיסיות
            spacer_item = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
            layout.addItem(spacer_item, row, 0, 1, -1)

            AppDebugger.log(f"SnippetsScreen: Loaded {len(snippets_metadata)} snippets for category: {category}")

        except Exception as e:
            AppErrorHandler.handle_error(
                error_obj=e,
                user_message=f"שגיאה בטעינת שליפים עבור קטגוריה '{category}'",
                dev_message=f"SnippetsScreen: Error loading snippets for category {category}: {str(e)}",
                severity="ERROR"
            )
            error_label = QLabel(f"שגיאה בטעינת שליפים: {str(e)}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label, 0, 0)

    def _create_snippet_widget(self, snippet_meta: dict) -> SnippetCardWidget:
        """פונקציית עזר לייצור מופע חדש של כרטיסיית שליף"""
        return SnippetCardWidget(snippet_meta=snippet_meta, parent=self)

    def open_create_snips_dialog(self):
        """פותח את חלון יצירת שליפים"""
        AppDebugger.log("SnippetsScreen: Opening create snippets dialog...")

        dialog = CreateSnipsDialog(parent=self)
        screen = self.screen()
        screen_center = screen.availableGeometry().center()
        dialog.move(screen_center - dialog.rect().center())

        dialog.exec()



#----------------------------------------------------------------------------------
    def go_back_home(self):
        """חזרה למסך הבית באמצעות מנהל המסכים"""
        if hasattr(self, 'manager') and self.manager:
            AppDebugger.log("SnippetsScreen: Returning to home screen...")
            self.manager.switch_to("home")

    def open_settings(self):
        """פתיחת חלון הגדרות"""
        AppDebugger.log("SnippetsScreen: Opening settings...")

    def show_about(self):
        """הצגת מידע אודות היישום"""
        AppDebugger.log("SnippetsScreen: Showing about dialog...")