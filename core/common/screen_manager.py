from PySide6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget
from core.common.error_manager import AppDebugger, AppErrorHandler


class ScreenManager(QWidget):
    """
    מנהל המסכים הראשי של האפליקציה.
    רכיב תשתיתי "טקטי" בלבד - מנהל את הערימה והחלפת המצבים הפיזית.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # 1. יצירת קונטיינר "הערימה" של Qt
        self.stacked_widget = QStackedWidget(self)

        # 2. סידור ה-Layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.stacked_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # דיקשנרי שמחזיק את המסכים הרשומים
        self._screens = {}

    def register_screen(self, name: str, screen_widget: QWidget):
        """
        רישום מסך חדש במערכת.
        הפונקציה נקראת מבחוץ (על ידי ה-Coordinator) ומזריקה את המסך לערימה.
        """
        self._screens[name] = screen_widget
        self.stacked_widget.addWidget(screen_widget)

        # הצמדת קישור אל המנהל למקרה הצורך
        screen_widget.manager = self
        AppDebugger.log(f" ScreenManager: המסך '{name}' נרשם והוזרק בהצלחה לערימה.")

    def switch_to(self, name: str):
        """הפונקציה הטכנית שמבצעת את החלפת המסך בפועל"""
        if name in self._screens:
            AppDebugger.log(f" ScreenManager: מעביר פיזית למסך '{name}'")
            target_widget = self._screens[name]
            self.stacked_widget.setCurrentWidget(target_widget)
        else:
            AppErrorHandler.handle_error(
                user_message="התרחשה שגיאה בניווט בין המסכים.",
                dev_message=f"ניסיון מעבר למסך לא קיים ברשימה: '{name}'",
                severity="WARNING"
            )

    # בשביל שהיה אפשר לגשת ולבדוק אם קיים מסך מסויים ברשימה
    def has_screen(self, name: str) -> bool:
        return name in self._screens