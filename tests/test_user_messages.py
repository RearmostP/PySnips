import ast
import inspect
import unittest
from unittest.mock import patch

from core.common import user_messages
from core.localization.localization import Localization


class UserMessageTests(unittest.TestCase):
    def test_no_snips_dependency(self):
        tree = ast.parse(inspect.getsource(user_messages))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or '')
        self.assertFalse(any(name == 'core.snips' or name.startswith('core.snips.')
                             for name in imports))

    def test_error_key_displays_translated_message(self):
        for language in ('en', 'he'):
            with self.subTest(language=language):
                localization = Localization(language)
                messages = user_messages.UserMessageManager(None, localization)
                with patch.object(user_messages.QMessageBox, 'critical') as critical:
                    messages.error_key('errors.invalid_data')
                    critical.assert_called_once_with(
                        None, localization.text('messages.error'),
                        localization.text('errors.invalid_data'))
