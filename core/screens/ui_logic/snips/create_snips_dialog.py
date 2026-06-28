from PySide6.QtWidgets import QDialog, QWidget, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, QPoint

import json

from core.common.app_paths import AppPaths
from core.common.dynamic_ui_loader import create_dynamic_ui_loader
from core.common.error_manager import AppDebugger, AppErrorHandler


class CreateSnipsDialog(create_dynamic_ui_loader(AppPaths.CREATE_SNIPS_DIALOG)):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.drag_pos = None


    def setup_events(self):
        """
        פונקציה שמחברת את האירועים והכפתורים.
        נקראת רק לאחר שקובץ ה-UI נטען במלואו לזיכרון.
        """
        AppDebugger.log("CreateSnipsDialog:מחבר אירועים ורכיבי ממשק וחיבור כפתורים לפונקציות...")

        self.btn_save.clicked.connect(self.save_snippet)
        self.btn_cancel.clicked.connect(self.close)



        # טען קטגוריות וצרף כפתורים דינמיים + עדכן את ה-combo
        self._load_category_buttons()

    def save_snippet(self):
        """
        שמירת שליף חדש לתיקייה
        
        קורא את הנתונים משדות הדיאלוג, מעבדם ושומר
        """
        try:
            title = self.inp_title_input.text()
            category = self.cmb_category_spinner.currentText()
            tags = self.inp_tags_input.text()
            content = self.txt_content_input.toPlainText()

            if not title or not content:
                AppErrorHandler.handle_error(user_message="שם ותוכן הם שדות חובה", severity="INFO",show_terminal=False,show_log=False, show_gui=True)
                return False

            tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()]

            snippet_data = {
                'title': title,
                'category': category,
                'tags': tags_list,
                'content': content
            }

            AppDebugger.log(f" CreateSnipsDialog: שמירת שליף חדש: {title}")

            self.accept()
            return True

        except Exception as e:
            AppErrorHandler.handle_error(error_obj=e, user_message="שגיאה בשמירת השליף", dev_message=str(e), severity="ERROR")
            return False

    def _load_category_buttons(self):
        """טוען קטגוריות מקובץ JSON לתוך ה-combobox"""
        try:
            categories_file = AppPaths.CATEGORYS_JSON
            categories = []
            with open(categories_file, 'r', encoding='utf-8') as f:
                categories = json.load(f)

            # עדכון ה-combobox בלבד (ללא כפתורים דינמיים)
            try:
                self.cmb_category_spinner.clear()
                self.cmb_category_spinner.addItems(categories)
            except Exception:
                AppDebugger.log("CreateSnipsDialog: לא ניתן לעדכן את ה-combobox")

        except Exception as e:
            AppErrorHandler.handle_error(error_obj=e, user_message="שגיאה בטעינת קטגוריות", dev_message=str(e), severity="ERROR", show_gui=False)

    @staticmethod
    def mousePressEvent(self, event):
        """תפיסת לחיצת העכבר על הדיאלוג לצורך גרירה"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    @staticmethod
    def mouseMoveEvent(self, event):
        """הזעת הדיאלוג כשהעכבר נלחץ"""
        if self.drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
        super().mouseMoveEvent(event)

    @staticmethod
    def mouseReleaseEvent(self, event):
        """שחרור העכבר"""
        self.drag_pos = None
        super().mouseReleaseEvent(event)


