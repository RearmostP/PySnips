from PySide6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget

# ייבוא המסכים שלך (בהנחה שזה המבנה שלהם)
from core.screens.ui_logic.home_screen import HomeScreen

from core.common.error_manager import AppDebugger


class ScreenManager(QWidget):
    """
    מנהל המסכים הראשי של האפליקציה.
    אחראי על טעינת כל המסכים לזיכרון וניווט ביניהם.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # 1. יצירת קונטיינר "הערימה" של Qt
        self.stacked_widget = QStackedWidget(self)

        # 2. סידור ה-Layout של המנהל עצמו כדי שהערימה תתפוס את כל הגודל
        layout = QVBoxLayout(self)
        layout.addWidget(self.stacked_widget)
        layout.setContentsMargins(0, 0, 0, 0)  # בלי שוליים מיותרים

        # דיקשנרי שיעזור לנו לנווט לפי שם (סטרינג) במקום לפי מספר אינדקס
        self._screens = {}

        # 3. טעינת המסכים הראשונית
        self._init_screens()

    def _init_screens(self):
        """מייצר את כל המסכים ומכניס אותם לערימה"""
        AppDebugger.log("מנהל המסכים: מתחיל לטעון את כל המסכים לזיכרון...")

        # יצירת המופעים של המסכים (שים לב: אנחנו מעבירים את self בתור ה-parent!)
        home_screen = HomeScreen(parent=self)

        # רישום והוספה לערימה
        self._add_screen("home", home_screen)

        # הגדרת מסך ברירת המחדל שיופיע כשהתוכנה עולה
        self.switch_to("home")

    def _add_screen(self, name: str, screen_widget: QWidget):
        """פונקציית עזר פנימית לרישום מסך בערימה"""
        self._screens[name] = screen_widget
        self.stacked_widget.addWidget(screen_widget)

    def switch_to(self, name: str):
        """הפונקציה הראשית שקוראים לה כדי להחליף מסך"""
        if name in self._screens:
            AppDebugger.log(f"🔄 מנהל המסכים: מעביר למסך '{name}'")
            target_widget = self._screens[name]
            self.stacked_widget.setCurrentWidget(target_widget)
        else:
            AppDebugger.log(f"❌ שגיאה: ניסיון לעבור למסך לא קיים: '{name}'")