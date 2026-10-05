from PySide6.QtCore import QUrl
from PySide6.QtGui import QPalette
from core.markdown.processor import to_html


def render_markdown(browser, content, base_directory=None):
    """Qt rich text with local relative media and fenced-code highlighting."""
    browser.document().setBaseUrl(QUrl.fromLocalFile(str(base_directory) + '/') if base_directory else QUrl())
    browser.ensurePolished()
    palette = browser.palette()
    color = palette.color(QPalette.ColorRole.Text).name()
    background = palette.color(QPalette.ColorRole.Base).name()
    browser.document().setDefaultStyleSheet(
        f'body {{ color: {color}; background-color: {background}; font-family: "Segoe UI"; font-size: 13px; margin: 0; padding: 4px; }} '
        'pre, code { font-family: "JetBrains Mono", Consolas, monospace; direction: ltr; } '
        'pre { font-size: 12px; padding: 10px; white-space: pre-wrap; } '
        'table { border-collapse: collapse; } td, th { padding: 5px; }')
    style = 'monokai' if palette.color(QPalette.ColorRole.Base).lightness() < 128 else 'default'
    browser.setHtml(to_html(content, style))
