# core/common/app_host.py
"""
🖥️ PySnips 0.4 - Application Host (App Host)
==============================================

🤔 מהו תפקיד הקובץ (Role & Responsibility)?
---------------------------------------------
... (התיעוד הקודם שכתבנו) ...

🏷️ למה קוראים לקובץ "App Host" (מארח האפליקציה)?
--------------------------------------------------
... (התיעוד הקודם שכתבנו) ...

📝 הערת המפתח (Developer's Architectural Note):
------------------------------------------------
הארכיטקטורה הנוכחית של ה-Host ומערכת האכיפה האוטומטית נולדו כחלק מתהליך מעבר
מפריימוורק ה-Kivy אל הליבה של PySide6/Qt. ב-Kivy, צורת הניהול והגישה לרכיבים
הייתה שונה, ובעת המעבר ל-Framework החדש, עבודה עם שמות גנריים ומפוזרים של
ווידג'טים יצרה חוסר נוחות, סרבול ורעש בקוד בזמן הפיתוח.

כדי לפתור את כאב הראש הזה ולייצר סביבת עבודה נוחה, קריאה ומאורגנת יותר,
הוחלט להפריד את "קירות" האפליקציה (ה-Host) מהתוכן שלה, ולחייב סנכרון
קשוח ומובנה שמקל על כתיבת הקוד ומונע טעויות הקלדה.
"""

from PySide6.QtWidgets import QMainWindow, QStackedWidget
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile

from core.common.app_paths import AppPaths
from core.common.mapping import HomeScreenElements, SnippetsScreenElements, ReadyCodeScreenElements


class PySnipsHost(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PySnips 0.3 - Prototype")
        self.resize(600, 500)

        # יצירת מנהל המסכים והצבתו במרכז ה-MainWindow
        self.screen_manager = QStackedWidget()
        self.setCentralWidget(self.screen_manager)

        self.loader = QUiLoader()

        # 1. טעינת כל הקבצים ל-Qt (סדר פעולות קשיח)
        self.load_all_ui_files()

        # 2. חיבור מערכת המעברים
        self.setup_navigation()

        # הצגת מסך הבית (אינדקס 0) בעליית האפליקציה
        self.screen_manager.setCurrentIndex(0)

    def _load_single_ui(self, absolute_path: str):
        """פונקציית עזר פנימית לפתיחה וטעינה בטוחה של קובץ UI"""
        file = QFile(absolute_path)
        if not file.open(QFile.ReadOnly):
            raise FileNotFoundError(f"קובץ ה-UI לא נמצא בנתיב: {absolute_path}")
        widget = self.loader.load(file, self)
        file.close()
        return widget

    def load_all_ui_files(self):
        """טוען את 3 המסכים מהנתיבים המוחלטים שבקובץ הקונפיג"""
        self.home_screen = self._load_single_ui(AppPaths.HOME_SCREEN)
        self.snippets_screen = self._load_single_ui(AppPaths.SNIPPETS_SCREEN)
        self.ready_code_screen = self._load_single_ui(AppPaths.READY_CODE_SCREEN)

        # דחיפת המסכים למנהל (קובע את האינדקסים שלהם ב-C++)
        self.screen_manager.addWidget(self.home_screen)  # Index 0
        self.screen_manager.addWidget(self.snippets_screen)  # Index 1
        self.screen_manager.addWidget(self.ready_code_screen)  # Index 2

    def setup_navigation(self):
        """חיבור כפתורי המעבר באמצעות השמות הלקוחים מקובץ המיפוי"""

        # --- חיבורים ממסך הבית ---
        # גישה לכפתור השליפים דרך השם ששמור במפת הרכיבים
        btn_snippets = getattr(self.home_screen, HomeScreenElements.BTN_GO_SNIPPETS)
        btn_snippets.clicked.connect(self.move_to_snippets)

        # גישה לכפתור הקוד המוכן דרך השם ששמור במפת הרכיבים
        btn_ready = getattr(self.home_screen, HomeScreenElements.BTN_GO_READY_CODE)
        btn_ready.clicked.connect(self.move_to_ready_code)

        # --- חיבורי חזרה למסך הבית מהמסכים האחרים ---
        btn_back_snip = getattr(self.snippets_screen, SnippetsScreenElements.BTN_BACK_HOME)
        btn_back_snip.clicked.connect(self.move_to_home)

        btn_back_ready = getattr(self.ready_code_screen, ReadyCodeScreenElements.BTN_BACK_HOME)
        btn_back_ready.clicked.connect(self.move_to_home)

    # --- מערכת המעברים המפורשת (שורות בודדות, הכי קריא שיש) ---
    def move_to_home(self):
        self.screen_manager.setCurrentIndex(0)

    def move_to_snippets(self):
        self.screen_manager.setCurrentIndex(1)

    def move_to_ready_code(self):
        self.screen_manager.setCurrentIndex(2)