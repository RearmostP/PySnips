from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QLineEdit, QPlainTextEdit, QTextEdit


def translate_ui(root, localization):
    root.setLayoutDirection(Qt.LayoutDirection.RightToLeft if localization.rtl else Qt.LayoutDirection.LeftToRight)
    properties = [('i18nKey', 'text', 'setText'),
                  ('i18nPlaceholderKey', 'placeholderText', 'setPlaceholderText'),
                  ('i18nTooltipKey', 'toolTip', 'setToolTip'),
                  ('i18nTitleKey', 'windowTitle', 'setWindowTitle')]
    for widget in [root, *root.findChildren(QWidget)]:
        for key_property, getter, setter in properties:
            key = widget.property(key_property)
            if key and hasattr(widget, setter):
                fallback_property = '_english_' + getter
                fallback = widget.property(fallback_property)
                if fallback is None:
                    fallback = getattr(widget, getter)()
                    widget.setProperty(fallback_property, fallback)
                getattr(widget, setter)(localization.resolve(key, fallback))
        # Code stays LTR. This explicit semantic property is set in Designer.
        if widget.property('codeEditor'):
            widget.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            if isinstance(widget, (QLineEdit, QPlainTextEdit, QTextEdit)):
                if hasattr(widget, 'setAlignment'):
                    widget.setAlignment(Qt.AlignmentFlag.AlignLeft)
