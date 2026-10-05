from core.common.paths import THEMES_DIR


class ThemeManager:
    def __init__(self, app, directory=THEMES_DIR):
        self.app = app
        self.directory = directory
        self.current = 'dark'

    def available_themes(self):
        return sorted(p.parent.name for p in self.directory.glob('*/style.qss'))

    def apply(self, name):
        self.current = name if name in self.available_themes() else 'dark'
        self.app.setStyleSheet((self.directory / self.current / 'style.qss').read_text(encoding='utf-8'))
