from core.common.paths import LANGUAGES_DIR


# מקבל קובץ שפה, ומחזיר מילון ברור של מפתח והמילה
def parse_language(text):
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        if key.strip() and value.strip():
            result[key.strip()] = value.strip().replace('\\n', '\n')
    return result


class Localization:
    def __init__(self, language='en', directory=LANGUAGES_DIR):
        self.directory = directory
        self.english = self.load('en')
        self.set_language(language)

        # היצירה של המשתנים האלא ב __init__ לא חובה, אח ככה יותר ברור
        self.language = language # זו נוצר נטו בשביל ההזהרה המציקה של PyCharm על כך שלא הוכרז המשתנה ב init ...
        self.strings = {} # זה הטקסט של השפה

    def load(self, language):
        path = self.directory / (language + '.lang')
        if not path.is_file():
            raise FileNotFoundError(f'Language file not found: {path}')
        return parse_language(path.read_text(encoding='utf-8-sig'))

    def available_languages(self):
        languages = []
        for p in self.directory.glob('*.lang'):
            languages.append(p.stem)
        return sorted(languages)

    def language_name(self, language):
        return self.load(language).get('language.name', language)

    def set_language(self, language):
        self.language = language if language in self.available_languages() else 'en'
        self.strings = self.load(self.language)

    @property
    def rtl(self):
        return self.strings.get('language.direction', 'ltr').lower() == 'rtl'

# כאן יש שתי פונקצייות שמציעות פעולות שונות במקראה שחסר בקובץ הלוקליזצייה מפתח כל שהוא או את הערך שלו
    def resolve(self, key, fallback=None): #מחזיר מפתח ריק
        return self.strings.get(key, fallback)

    def text(self, key, **values): # מחזיר את המילה באנגלית של המפתח
        return self.strings.get(key, self.english.get(key, key)).format(**values)
