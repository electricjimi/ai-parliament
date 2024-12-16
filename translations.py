import json
import os


class Translator:
    def __init__(self, language='en'):
        self.language = language
        self.translations = self._load_translations()

    def _load_translations(self):
        locale_path = os.path.join('locales', f'{self.language}.json')
        try:
            with open(locale_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            with open(os.path.join('locales', 'en.json'), 'r', encoding='utf-8') as f:
                return json.load(f)

    def get(self, key, *args):
        keys = key.split('.')
        value = self.translations
        for k in keys:
            value = value.get(k, key)
            if not isinstance(value, dict):
                break

        if isinstance(value, str) and args:
            return value.format(*args)
        return value
