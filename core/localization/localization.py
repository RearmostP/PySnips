from core.common.paths import LANGUAGES_DIR


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
        self.english = self._load('en')
        self.set_language(language)

    def _load(self, language):
        path = self.directory / (language + '.lang')
        return parse_language(path.read_text(encoding='utf-8-sig')) if path.is_file() else {}

    def available_languages(self):
        return sorted(p.stem for p in self.directory.glob('*.lang'))

    def language_name(self, language):
        return self._load(language).get('language.name', language)

    def set_language(self, language):
        self.language = language if language in self.available_languages() else 'en'
        self.strings = self._load(self.language)

    @property
    def rtl(self):
        return self.strings.get('language.direction', 'ltr').lower() == 'rtl'

    def resolve(self, key, fallback=None):
        return self.strings.get(key, fallback)

    def text(self, key, **values):
        # Python-created text also has an English fallback in the external file.
        return self.strings.get(key, self.english.get(key, key)).format(**values)
