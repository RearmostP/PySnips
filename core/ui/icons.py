"""Local SVG icons colored from their owner's live Qt/QSS palette."""
import re
import weakref

from PySide6.QtCore import QByteArray, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QIconEngine, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from core.common.paths import ASSETS_DIR

ICON_SIZE = 18
NAV_ICON_SIZE = 20


class _SvgIconEngine(QIconEngine):
    def __init__(self, source, widget, mirror_rtl):
        super().__init__()
        self.source = source
        self.owner = weakref.ref(widget) if widget is not None else lambda: None
        self.mirror_rtl = mirror_rtl

    def clone(self):
        return _SvgIconEngine(self.source, self.owner(), self.mirror_rtl)

    def paint(self, painter, rect, mode, state):
        widget = self.owner()
        try:
            palette = widget.palette() if widget is not None else QApplication.palette()
            role = widget.foregroundRole() if widget is not None else QPalette.WindowText
            direction = widget.layoutDirection() if widget is not None else QApplication.layoutDirection()
        except RuntimeError:
            # An action/icon may outlive its original widget.
            widget = None
            palette, role, direction = QApplication.palette(), QPalette.WindowText, QApplication.layoutDirection()
        group = QPalette.Disabled if mode == QIcon.Disabled else QPalette.Active
        color = palette.color(group, role).name()
        if widget is None:
            colors = QApplication.instance().property('themeColors') or {}
            color = colors.get('text_disabled' if mode == QIcon.Disabled else 'text', color)
        renderer = QSvgRenderer(QByteArray(self.source.replace(b'currentColor', color.encode('ascii'))))
        painter.save()
        if self.mirror_rtl and direction == Qt.RightToLeft:
            painter.translate(rect.left() + rect.right() + 1, 0)
            painter.scale(-1, 1)
        renderer.render(painter, QRectF(rect))
        painter.restore()

    def pixmap(self, size, mode, state):
        pixmap = QPixmap(size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        self.paint(painter, QRect(0, 0, size.width(), size.height()), mode, state)
        painter.end()
        return pixmap

    def scaledPixmap(self, size, mode, state, scale):
        pixmap = self.pixmap(size * scale, mode, state)
        pixmap.setDevicePixelRatio(scale)
        return pixmap


def icon(name, widget=None, *, mirror_rtl=False):
    """Return icon('actions/delete', button); missing/invalid files give QIcon().

    The optional owner supplies the live text color and layout direction. SVG
    is the default suffix; explicit .svg and the existing .ico logo also work.
    """
    if not isinstance(name, str) or not re.fullmatch(r'[\w-]+(?:/[\w-]+)*(?:\.(?:svg|ico))?', name):
        return QIcon()
    path = ASSETS_DIR / 'icons' / name
    if not path.suffix:
        path = path.with_suffix('.svg')
    if path.suffix == '.ico':
        return QIcon(str(path)) if path.is_file() else QIcon()
    try:
        source = path.read_bytes()
    except OSError:
        return QIcon()
    if not QSvgRenderer(QByteArray(source)).isValid():
        return QIcon()
    return QIcon(_SvgIconEngine(source, widget, mirror_rtl))


def set_button_icon(button, name, *, size=ICON_SIZE, mirror_rtl=False):
    button.setIcon(icon(name, button, mirror_rtl=mirror_rtl))
    button.setIconSize(QSize(size, size))
