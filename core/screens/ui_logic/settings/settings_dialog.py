# תפקיד הקובץ:
# לוגיקת חלון ההגדרות הראשי.
# הקובץ מנהל את הניווט בין עמודי ההגדרות, את פתיחת תתי-העמודים של שליפים,
# ואת טעינת עמודי ההגדרות לתוך ה-QStackedWidget.

from PySide6.QtCore import QEvent, QSize
from PySide6.QtGui import QIcon

from core.screens.ui_logic.settings.pages.general import GeneralSettingsPage
from core.screens.ui_logic.settings.pages.ready_code import ReadyCodeSettingsPage
from core.screens.ui_logic.settings.pages.snips import (
    SnipsCategoriesPage,
    SnipsOverviewPage,
    SnipsRestorePage,
)
from core.tools.common.app_paths import AppPaths
from core.tools.common.dynamic_ui_loader import create_dynamic_ui_loader


class SettingsDialog(create_dynamic_ui_loader(AppPaths.SETTINGS_DIALOG)):
    SNIPS_TEXT = "snips"
    SNIPS_ICON_CLICK_WIDTH = 32

    def __init__(self, parent=None):
        super().__init__(parent)
        self.chevron_right_icon = QIcon(str(AppPaths.ICONS_DIR / "chevron-right.svg"))
        self.chevron_down_icon = QIcon(str(AppPaths.ICONS_DIR / "chevron-down.svg"))

        self.general_page = GeneralSettingsPage(parent=self.wdg_settings_pages)
        self.snips_overview_page = SnipsOverviewPage(parent=self.wdg_settings_pages)
        self.snips_restore_page = SnipsRestorePage(parent=self.wdg_settings_pages)
        self.snips_categories_page = SnipsCategoriesPage(parent=self.wdg_settings_pages)
        self.ready_code_page = ReadyCodeSettingsPage(parent=self.wdg_settings_pages)

        self._register_pages()
        self.setup_events()
        self._setup_navigation_style()
        self.btn_settings_snips.installEventFilter(self)
        self._show_general_page()

    def _register_pages(self):
        self.wdg_settings_pages.addWidget(self.general_page.get_view())
        self.wdg_settings_pages.addWidget(self.snips_overview_page.get_view())
        self.wdg_settings_pages.addWidget(self.snips_restore_page.get_view())
        self.wdg_settings_pages.addWidget(self.snips_categories_page.get_view())
        self.wdg_settings_pages.addWidget(self.ready_code_page.get_view())

    def setup_events(self):
        self.btn_settings_general.clicked.connect(self._show_general_page)
        self.btn_settings_snips.clicked.connect(self._show_snips_page)
        self.snips_overview_page.restore_requested.connect(self._show_snips_restore_page)
        self.snips_overview_page.categories_requested.connect(self._show_snips_categories_page)
        self.btn_snips_restore.clicked.connect(self._show_snips_restore_page)
        self.btn_snips_manage_categories.clicked.connect(self._show_snips_categories_page)
        self.btn_settings_ready_code.clicked.connect(self._show_ready_code_page)

    def eventFilter(self, watched, event):
        if watched is self.btn_settings_snips and event.type() == QEvent.Type.MouseButtonPress:
            if event.position().x() <= self.SNIPS_ICON_CLICK_WIDTH:
                self._toggle_snips_submenu()
                return True
        return super().eventFilter(watched, event)

    def _show_general_page(self):
        self._set_snips_expanded(False)
        self._set_active_button(self.btn_settings_general)
        self.wdg_settings_pages.setCurrentWidget(self.general_page.get_view())

    def _show_snips_page(self):
        self._set_active_button(self.btn_settings_snips)
        self.wdg_settings_pages.setCurrentWidget(self.snips_overview_page.get_view())

    def _show_snips_restore_page(self):
        self._set_snips_expanded(True)
        self._set_active_button(self.btn_snips_restore)
        self.wdg_settings_pages.setCurrentWidget(self.snips_restore_page.get_view())

    def _show_snips_categories_page(self):
        self._set_snips_expanded(True)
        self._set_active_button(self.btn_snips_manage_categories)
        self.wdg_settings_pages.setCurrentWidget(self.snips_categories_page.get_view())

    def _show_ready_code_page(self):
        self._set_snips_expanded(False)
        self._set_active_button(self.btn_settings_ready_code)
        self.wdg_settings_pages.setCurrentWidget(self.ready_code_page.get_view())

    def _toggle_snips_submenu(self):
        self._set_snips_expanded(not self.wdg_snips_submenu.isVisible())

    def _set_snips_expanded(self, expanded: bool):
        self.wdg_snips_submenu.setVisible(expanded)
        self.btn_settings_snips.setText(self.SNIPS_TEXT)
        self.btn_settings_snips.setIcon(self.chevron_down_icon if expanded else self.chevron_right_icon)

    def _set_active_button(self, active_button):
        for button in (
            self.btn_settings_general,
            self.btn_settings_snips,
            self.btn_snips_restore,
            self.btn_snips_manage_categories,
            self.btn_settings_ready_code,
        ):
            button.setProperty("active", button is active_button)
            button.style().unpolish(button)
            button.style().polish(button)

    def _setup_navigation_style(self):
        self.btn_settings_snips.setText(self.SNIPS_TEXT)
        self.btn_settings_snips.setIcon(self.chevron_right_icon)
        self.btn_settings_snips.setIconSize(QSize(14, 14))
        self.setStyleSheet("""
            QDialog#SettingsDialog {
                background-color: #1e1e1e;
                color: #e8e8e8;
            }
            QWidget#wdg_settings_sidebar {
                background-color: #242424;
                border-right: 1px solid #343434;
            }
            QPushButton#btn_settings_general,
            QPushButton#btn_settings_snips,
            QPushButton#btn_settings_ready_code,
            QPushButton#btn_snips_restore,
            QPushButton#btn_snips_manage_categories {
                background-color: transparent;
                color: #d8d8d8;
                border: none;
                border-radius: 4px;
                padding: 7px 10px;
                text-align: left;
                font-size: 13px;
            }
            QPushButton#btn_snips_restore,
            QPushButton#btn_snips_manage_categories {
                color: #c8c8c8;
                padding-left: 18px;
                font-size: 12px;
            }
            QPushButton#btn_settings_general:hover,
            QPushButton#btn_settings_snips:hover,
            QPushButton#btn_settings_ready_code:hover,
            QPushButton#btn_snips_restore:hover,
            QPushButton#btn_snips_manage_categories:hover {
                background-color: #303030;
            }
            QPushButton[active="true"] {
                background-color: #36506b;
                color: #ffffff;
            }
            QStackedWidget#wdg_settings_pages {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #eeeeee;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton#btn_restore_link,
            QPushButton#btn_categories_link {
                background-color: transparent;
                color: #4da3ff;
                border: none;
                text-align: left;
                padding: 5px 0;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton#btn_restore_link:hover,
            QPushButton#btn_categories_link:hover {
                color: #7bbcff;
                text-decoration: underline;
            }
        """)
