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
from PySide6.QtWidgets import QMenu, QPushButton, QLabel, QSpacerItem, QSizePolicy, QInputDialog, QMessageBox, QGridLayout, QWidget, QLayoutItem, QStackedWidget
from PySide6.QtCore import Qt, QSignalBlocker

from core.tools.common.app_paths import AppPaths
from core.screens.ui_logic.snips.create_snips_dialog import CreateSnipsDialog

from core.screens.ui_logic.snips.widget.snippet_card import SnippetCard
from core.screens.ui_logic.snips.widget.edit_card import EditCardWidget
from core.screens.ui_logic.snips.widget.snippet_search_widget import SnippetSearchWidget
from core.screens.ui_logic.settings.settings_dialog import SettingsDialog
from core.tools.common.dynamic_ui_loader import create_dynamic_ui_loader
from core.tools.common.error_manager import AppDebugger, AppErrorHandler
from core.boot import get_categories, rebuild_search_index, update_categories_file
from core.tools.snips import move_snippet_to_trash


def _sanitize(name: str) -> str:
    """הפוך שם קטגוריה לשם קובץ בטוח לשימוש במערכת קבצים."""
    safe = ''.join(c for c in (name or '') if c.isalnum() or c in (' ', '_', '-')).strip()
    if not safe:
        return 'uncategorized'
    return safe.replace(' ', '_')

#----------------------------------------------------------------
# --- מחלקת עזר לפעולות על Layouts ---
#----------------------------------------------------------------
class LayoutHelper:
    @staticmethod
    def replace_widget_in_grid_layout(layout: QGridLayout, old_widget: QWidget, new_widget: QWidget) -> bool:
        """
        מחליף ווידג'ט קיים בווידג'ט חדש בתוך QGridLayout, תוך שמירה על המיקום המקורי.

        Args:
            layout (QGridLayout): ה-layout שבו מתבצעת ההחלפה.
            old_widget (QWidget): הווידג'ט שיש להסיר.
            new_widget (QWidget): הווידג'ט שיש להוסיף.

        Returns:
            bool: True אם ההחלפה בוצעה בהצלחה, False אחרת.
        """
        if not layout or not old_widget or not new_widget:
            AppDebugger.log("Error: ארגומנטים לא חוקיים עבור replace_widget_in_grid_layout.")
            return False

        # מצא את המיקום של הווידג'ט הישן ב-layout
        row, col, rowspan, colspan = -1, -1, -1, -1
        item_to_remove: QLayoutItem | None = None

        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget() == old_widget:
                row, col, rowspan, colspan = layout.getItemPosition(i)
                item_to_remove = item
                break

        if row == -1:  # הווידג'ט הישן לא נמצא ב-layout
            AppDebugger.log(f"Error: old_widget {old_widget} not found in layout for replacement.")
            return False

        # הסר את הווידג'ט הישן
        if item_to_remove:
            layout.removeItem(item_to_remove)  # הסר את ה-item מה-layout
        layout.removeWidget(old_widget)  # הסר את הווידג'ט עצמו
        old_widget.deleteLater()  # נקה את הווידג'ט הישן מהזיכרון

        # הוסף את הווידג'ט החדש באותו מיקום
        layout.addWidget(new_widget, row, col, rowspan, colspan)
        return True
# --- סוף מחלקת עזר ---

#-----------------------------------------------------------------
class SnippetsScreen(create_dynamic_ui_loader(AppPaths.SNIPPETS_SCREEN)):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_editor_widget: EditCardWidget | None = None
        self._active_editor_original_card: SnippetCard | None = None
        self._current_category = "Recent Snippets"
        self.content_stack: QStackedWidget | None = None
        self.category_content_widget: QWidget | None = None
        self.search_widget: SnippetSearchWidget | None = None

    def setup_content_stack(self):
        """Creates the internal content stack used by the snippets area."""
        host_layout = self.grid_snippets_layout
        if not host_layout:
            AppDebugger.log("Error: grid_snippets_layout not found for content stack setup.")
            return

        self.content_stack = QStackedWidget(self)

        self.category_content_widget = QWidget(self.content_stack)
        category_layout = QGridLayout(self.category_content_widget)
        category_layout.setContentsMargins(0, 0, 0, 0)
        category_layout.setSpacing(12)

        self.search_widget = SnippetSearchWidget(parent=self.content_stack)
        self.search_widget.delete_requested.connect(self._handle_delete_snippet_request)

        self.content_stack.addWidget(self.category_content_widget)
        self.content_stack.addWidget(self.search_widget.get_view())

        while host_layout.count():
            item = host_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.spacerItem():
                del item

        host_layout.addWidget(self.content_stack, 0, 0)
        self.grid_snippets_layout = category_layout

    def _set_content_mode(self, mode: str, payload: str | None = None):
        """Switches the snippets content area and passes the required data."""
        if not self.content_stack:
            AppDebugger.log("Error: content_stack is not initialized.")
            return

        if mode == "search":
            if not self.search_widget:
                AppDebugger.log("Error: search_widget is not initialized.")
                return
            self.lbl_category_title.setText("Search")
            self.content_stack.setCurrentWidget(self.search_widget.get_view())
            self.search_widget.set_query(payload or "")
            return

        if mode == "category":
            if not self.category_content_widget:
                AppDebugger.log("Error: category_content_widget is not initialized.")
                return
            category = payload or self._current_category
            self.lbl_category_title.setText(f"Folder: {category}")
            self.content_stack.setCurrentWidget(self.category_content_widget)
            self._load_snips_to_content_box(category)
            return

        AppDebugger.log(f"SnippetsScreen: Unknown content mode: {mode}")

    def _on_search_text_changed(self, text: str):
        query = (text or "").strip()
        if query:
            self._set_content_mode("search", query)
        else:
            self._set_content_mode("category", self._current_category)

    def setup_events(self):
        """
        פונקציה שמחברת את האירועים והכפתורים.
        נקראת רק לאחר שקובץ ה-UI נטען במלואו לזיכרון.
        """
        AppDebugger.log("SnippetsScreen: חיבור אירועי ואלמנטים של ממשק משתמש...")
        self.setup_content_stack()
        # בניית תפריט ההמבורגר
        self.setup_hamburger_menu()
        # טעינת כפתורי קטגוריות דינמיים
        self.load_category_buttons()
        # חיבור כפתור הוספת קטגוריה
        self.btn_add_category.clicked.connect(self._add_new_category)
        # חיבור כפתור הוספת שליף
        self.btn_new_snippet.clicked.connect(self.open_create_snips_dialog)
        self.inp_search_snips.textChanged.connect(self._on_search_text_changed)

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
            categories = get_categories()
            AppDebugger.log(f"Loaded {len(categories)} categories")

            layout = self.scl_categories.widget().layout()
            if not layout:
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

        except Exception as e:
            AppErrorHandler.handle_error(
                error_obj=e,
                user_message="שגיאה בטעינת כפתורי קטגוריות",
                dev_message=f"SnippetsScreen: שגיאה בטעינת כפתורי הקטגוריות: {str(e)}",
                severity="ERROR"
            )

    def on_category_selected(self, category: str):
        """קריאה כאשר משתמש לוחץ על כפתור קטגוריה"""
        AppDebugger.log(f"SnippetsScreen: Category selected: {category}")
        self._current_category = category
        blocker = QSignalBlocker(self.inp_search_snips)
        self.inp_search_snips.clear()
        del blocker
        self._set_content_mode("category", category)

    def _load_snips_to_content_box(self, category: str):
        """טוען את הקודים הקצרים (snippets) של קטגוריה מסוימת לתוך תיבת התוכן"""
        AppDebugger.log(f"SnippetsScreen: Loading snippets for category: {category}")

        layout = self.grid_snippets_layout
        if not layout:
            AppDebugger.log("Error: grid_snippets_layout not found for snippets")
            return

        # ניקוי יסודי של ה-Layout כולל Spacers ישנים למניעת זליגת זיכרון
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            # אם הפריט הוא Spacer או Layout פנימי - נמחק את המשאב שלו מהזיכרון
            elif item.spacerItem():
                del item

        # --- מצבים מיוחדים ---
        if category == "Recent Snippets":
            placeholder_label = QLabel("הצגת שליפים אחרונים (בפיתוח)")
            placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(placeholder_label, 0, 0)
            return
        if category == "Search":
            placeholder_label = QLabel("הצגת שליפים עם התאגים בתצוגה מקדימה (בפיתוח)")
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
                snippet_card_connector = self._create_snippet_widget(snippet_meta)
                layout.addWidget(snippet_card_connector.get_view(), row, 0)
                row += 1

            # הוספת spacer בסוף כדי למנוע מתיחה אנכית של הכרטיסיות
            spacer_item = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
            layout.addItem(spacer_item, row, 0, 1, -1)

        except Exception as e:
            AppErrorHandler.handle_error(
                error_obj=e,
                user_message=f"שגיאה בטעינת שליפים עבור קטגוריה '{category}'",
                dev_message=f"SnippetsScreen: שגיאה בטעינת שליפים עבור קטגוריה  {category}: {str(e)}",
                severity="ERROR"
            )
            error_label = QLabel(f"שגיאה בטעינת שליפים: {str(e)}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label, 0, 0)

    def _create_snippet_widget(self, snippet_meta: dict) -> SnippetCard:
        """פונקציית עזר לייצור מופע חדש של כרטיסיית שליף"""
        snippet_card_connector = SnippetCard(snippet_meta=snippet_meta)
        snippet_card_connector.edit_requested.connect(lambda meta=snippet_meta, card_connector=snippet_card_connector: self._handle_edit_snippet_request(meta, card_connector))
        snippet_card_connector.delete_requested.connect(self._handle_delete_snippet_request)
        return snippet_card_connector

    def _handle_edit_snippet_request(self, snippet_meta: dict, old_snippet_card: SnippetCard):
        """
        מטפל בבקשת עריכה של שליף: מחליף את כרטיסיית השליף בווידג'ט עריכה.
        """
        AppDebugger.log(f"SnippetsScreen: Request to edit snippet ID: {snippet_meta.get('id')}")

        grid_snippets_layout = self.grid_snippets_layout
        if not grid_snippets_layout:
            AppDebugger.log("Error: grid_snippets_layout not found for snippet editing.")
            return

        # אחסון הפניות לעורך הפעיל ולכרטיס המקורי שלו
        self._active_editor_original_card = old_snippet_card

        #  יצירת EditCardWidget חדש
        edit_widget = EditCardWidget(
            snippet_meta=snippet_meta,
            on_save_callback=self._on_edit_save,
            on_cancel_callback=self._on_edit_cancel
        )
        self._active_editor_widget = edit_widget

        # החלפת הכרטיס הישן עם ווידג'ט העריכה
        LayoutHelper.replace_widget_in_grid_layout(grid_snippets_layout, old_snippet_card.get_view(), edit_widget.get_view())

    def _handle_delete_snippet_request(self, snippet_meta: dict):
        title = str(snippet_meta.get("title") or "ללא כותרת")
        answer = QMessageBox.question(
            self,
            "מחיקת שליף",
            f"האם להעביר את השליף '{title}' לאשפה?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        if not move_snippet_to_trash(snippet_meta):
            QMessageBox.warning(self, "מחיקת שליף", "לא ניתן היה להעביר את השליף לאשפה.")
            return

        rebuild_search_index()
        self._refresh_after_snippet_delete()

    def _refresh_after_snippet_delete(self):
        query = self.inp_search_snips.text().strip()
        if query and self.search_widget:
            self.search_widget.clear()
            self._set_content_mode("search", query)
            return

        self._set_content_mode("category", self._current_category)

    def _on_edit_save(self, updated_snippet_meta: dict):
        """
        Callback מ-EditCardWidget כאשר העריכה נשמרה.
        מחליף את ווידג'ט העריכה בחזרה לכרטיסיית שליף מעודכנת.
        """

        grid_snippets_layout = self.grid_snippets_layout
        if not grid_snippets_layout or not self._active_editor_widget or not self._active_editor_original_card:
            AppDebugger.log("Error: לא נשמר העריכה.")
            return

        # יוצר כרטיס קטע חדש ומעודכן
        new_snippet_card = self._create_snippet_widget(updated_snippet_meta)

        # מחליף את העורך בכרטיס החדש
        LayoutHelper.replace_widget_in_grid_layout(grid_snippets_layout, self._active_editor_widget.get_view(), new_snippet_card.get_view())

        # ניקוי מצב העורך הפעיל
        self._active_editor_widget = None
        self._active_editor_original_card = None

        #לחלופין, ניתן לטעון מחדש את כל הקטגוריה כדי להבטיח עקביות, אך בדרך כלל מספיקה החלפת הכרטיס.
        # self.on_category_selected(updated_snippet_meta.get('category'))

    def _on_edit_cancel(self):
        """
        Callback מ-EditCardWidget כאשר העריכה בוטלה.
        מחליף את ווידג'ט העריכה בחזרה לכרטיסיית השליף המקורית.
        """

        grid_snippets_layout = self.grid_snippets_layout
        if not grid_snippets_layout or not self._active_editor_widget or not self._active_editor_original_card:
            AppDebugger.log("Error: Cannot cancel edit, missing layout or active editor info.")
            return

        # יוצר כרטיס קטע חדש באמצעות נתוני המטא מהכרטיס המקורי
        # זה מבטיח שאנו לא מנסים להשתמש באובייקט C++ שנמחק.
        new_snippet_card = self._create_snippet_widget(self._active_editor_original_card.snippet_meta)

        # מחליף את העורך בכרטיס החדש
        LayoutHelper.replace_widget_in_grid_layout(grid_snippets_layout, self._active_editor_widget.get_view(), new_snippet_card.get_view())

        # ניקוי מצב העורך הפעיל
        self._active_editor_widget = None
        self._active_editor_original_card = None

    def _add_new_category(self):
        """פתיחת דיאלוג ליצירת קטגוריה חדשה ושמירתה."""
        AppDebugger.log("SnippetsScreen: Opening dialog for new category...")
        category_name, ok = QInputDialog.getText(self, "קטגוריה חדשה", "הכנס שם קטגוריה:")

        if ok and category_name:
            sanitized_name = _sanitize(category_name)
            if not sanitized_name:
                QMessageBox.warning(self, "שם לא חוקי", "שם הקטגוריה אינו יכול להיות ריק או להכיל תווים מיוחדים בלבד.")
                return

            try:
                # בדוק אם הקטגוריה כבר קיימת
                current_categories = get_categories()
                if sanitized_name in current_categories:
                    if sanitized_name == 'uncategorized':
                        QMessageBox.information(self, "קטגוריה קיימת",
                                                f"השם שהוזן ('{category_name}') מתורגם לקטגוריה 'uncategorized' שכבר קיימת. אנא בחר שם אחר.")
                    else:
                        QMessageBox.information(self, "קטגוריה קיימת",
                                                f"הקטגוריה '{category_name}' כבר קיימת.")
                    return

                # יצירת תיקיית הקטגוריה
                category_dir = AppPaths.SNIPS_FILES / sanitized_name
                category_dir.mkdir(parents=True, exist_ok=True)
                AppDebugger.log(f"SnippetsScreen: נוצר קטגוריה חדשה: {category_dir}")

                # עדכון קובץ ה-JSON של הקטגוריות
                update_categories_file(sanitized_name)

                self.load_category_buttons() # רענן את כפתורי הקטגוריות
                self.on_category_selected(sanitized_name) # בחר את הקטגוריה החדשה
            except Exception as e:
                AppErrorHandler.handle_error(
                    error_obj=e,
                    user_message=f"שגיאה ביצירת קטגוריה חדשה: {category_name}",
                    dev_message=f"SnippetsScreen: שגיאה ביצירת קטגוריה חדשה: {category_name}: {str(e)}",
                    severity="ERROR",
                    show_gui=True
                )
        elif ok and not category_name:
            QMessageBox.warning(self, "שם ריק", "שם הקטגוריה לא יכול להיות ריק.")

    def open_create_snips_dialog(self):
        """פותח את חלון יצירת שליפים"""
        AppDebugger.log("SnippetsScreen: פתיחת create snippets dialog...")

        dialog = CreateSnipsDialog(parent=self)
        dialog.setup_events()
        screen = self.screen()
        screen_center = screen.availableGeometry().center()
        dialog.move(screen_center - dialog.rect().center())

        dialog.exec()

    def go_back_home(self):
        """חזרה למסך הבית באמצעות מנהל המסכים"""
        if hasattr(self, 'manager') and self.manager:
            self.manager.switch_to("home")

    def open_settings(self):
        """פתיחת חלון הגדרות"""
        dialog = SettingsDialog(parent=self)
        dialog.resize(900, 600)
        dialog.exec()

    def show_about(self):
        """הצגת מידע אודות היישום"""
        AppDebugger.log("SnippetsScreen: Showing about dialog...")
