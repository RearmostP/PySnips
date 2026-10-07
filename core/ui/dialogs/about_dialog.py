from pathlib import Path
from platform import python_version

from PySide6 import __version__ as pyside_version
from PySide6.QtCore import QUrl, QSize
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton

from core.common.paths import ASSETS_DIR
from core.localization.ui_translator import translate_ui
from core.updater.updater import Updater, UpdateError


GITHUB_URL = 'https://github.com/RearmostP/PySnips'
FORUM_URL = (
    'https://mitmachim.top/topic/99203/'
    '%D7%A9%D7%99%D7%AA%D7%95%D7%A3-%D7%A4%D7%99%D7%AA%D7%97%D7%AA%D7%99-'
    '%D7%90%D7%A4%D7%9C%D7%99%D7%A7%D7%A6%D7%99%D7%94-%D7%95%D7%90%D7%A0%D7%99-'
    '%D7%A8%D7%95%D7%A6%D7%94-%D7%9C%D7%A9%D7%AA%D7%A3-%D7%90%D7%95%D7%AA%D7%94-pysnips'
)


class AboutDialog(QDialog):
    def __init__(self, localization, parent=None):
        super().__init__(parent)
        self.ui = QUiLoader().load(str(Path(__file__).with_suffix('.ui')), self)
        self.setWindowTitle(self.ui.windowTitle())
        self.setProperty('i18nTitleKey', 'about.title')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)
        icon = QIcon(str(ASSETS_DIR / 'icons' / 'pysnips-multisize.ico'))
        self.setWindowIcon(icon)
        self.ui.findChild(QLabel, 'app_icon').setPixmap(icon.pixmap(QSize(64, 64)))
        translate_ui(self, localization)
        try:
            app_version = Updater().current_version
        except UpdateError:
            app_version = '—'
        for name, key, values in (
            ('version', 'about.version', {'version': app_version}),
            ('python_version', 'about.python', {'version': python_version()}),
            ('pyside_version', 'about.pyside', {'version': pyside_version}),
            ('creator', 'about.created_by', {'creator': 'RearmostP'}),
        ):
            self.ui.findChild(QLabel, name).setText(localization.text(key, **values))
        self.ui.findChild(QPushButton, 'github').clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(GITHUB_URL)))
        self.ui.findChild(QPushButton, 'forum').clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(FORUM_URL)))
        self.ui.findChild(QPushButton, 'close').clicked.connect(self.accept)
        self.resize(374, 230)
