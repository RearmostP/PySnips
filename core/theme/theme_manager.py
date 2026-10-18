import json
import re
from pathlib import Path
from string import Template

from core.common.paths import THEMES_DIR


#פונקציית עזר מחוץ למחלקה, שמזהה מפתחות צבע כפולים בזמן קריאת JSON.
def _unique_colors(pairs):
    colors = {}
    for key, value in pairs:
        if key in colors:
            raise ValueError(f'Duplicate color key: {key!r}')
        colors[key] = value
    return colors


class ThemeManager:
    def __init__(self, app, directory=THEMES_DIR):
        self.app = app # זה אוביקט מסוג QApplication בשביל שאחרכך דרכו יהיה אפשר לשנות את העיצוב
        self.directory = Path(directory)
        self.current = 'dark'

    def available_themes(self):
        themes = []
        for path in self.directory.glob('*/colors.json'):
            if path.is_file():
                theme_name = path.parent.name
                themes.append(theme_name)
        return sorted(themes)

#  --------------  קוד נכתב עם AI ולא עבר מיפוי של יד אדם  ----------------
    def _load(self, name):
        palette_path = self.directory / name / 'colors.json'
        stylesheet_path = self.directory / 'style.qss'
        try:
            colors = json.loads(palette_path.read_text(encoding='utf-8'), object_pairs_hook=_unique_colors)
            if not isinstance(colors, dict):
                raise ValueError('colors.json must contain an object')
            for key, value in colors.items():
                if not isinstance(value, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}|transparent', value):
                    raise ValueError(f'Invalid color for {key!r}: expected #RRGGBB or transparent')
            template = Template(stylesheet_path.read_text(encoding='utf-8'))
            if not template.is_valid():
                raise ValueError('Invalid color placeholder in style.qss')
            missing = set(template.get_identifiers()) - colors.keys()
            if missing:
                raise ValueError('Missing colors: ' + ', '.join(sorted(missing)))
            return template.substitute(colors), colors
        except (OSError, ValueError) as error:
            raise ValueError(f'Cannot load theme {name!r} ({palette_path}; {stylesheet_path}): {error}') from error

    def apply(self, name):
        selected = name if name in self.available_themes() else 'dark'
        # Validate before applying: a broken palette leaves the active theme intact.
        stylesheet, colors = self._load(selected)
        self.app.setStyleSheet(stylesheet)
        # QSS does not update QApplication.palette(); ownerless SVG icons use
        # these already-validated colors as their application-wide fallback.
        self.app.setProperty('themeColors', colors)
        self.current = selected
