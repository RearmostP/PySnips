from pathlib import Path
from urllib.parse import quote
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLineEdit, QComboBox, QPlainTextEdit, QTextBrowser, QFileDialog, QStackedWidget
from core.localization.ui_translator import translate_ui
from core.markdown.renderer import render_markdown
from core.snips.models import LibraryError


class CreateSnippet(QDialog):
    """Creation and editing share one form. Storage stays behind the library."""
    def __init__(self, library, localization, messages, snippet=None, parent=None):
        super().__init__(parent)
        self.library, self.localization, self.messages = library, localization, messages
        self.snippet = snippet
        self.pending_media = []
        self.setWindowTitle(localization.text('snips.edit' if snippet else 'snips.create'))
        self.resize(600, 699)
        self.ui = QUiLoader().load(str(Path(__file__).with_suffix('.ui')), self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)
        self.title = self.ui.findChild(QLineEdit, 'title')
        self.tags = self.ui.findChild(QLineEdit, 'tags')
        self.disk_name = self.ui.findChild(QLineEdit, 'disk_name')
        self.category = self.ui.findChild(QComboBox, 'category')
        self.content = self.ui.findChild(QPlainTextEdit, 'content')
        self.preview = self.ui.findChild(QTextBrowser, 'preview_browser')
        self.content_stack = self.ui.findChild(QStackedWidget, 'contentStack')
        self.content_stack.setCurrentIndex(0)
        self.disk_name.hide()
        self.category.addItems(library.categories())
        if snippet:
            self.title.setText(snippet.title)
            self.tags.setText(', '.join(snippet.tags))
            self.disk_name.setText(snippet.disk_name)
            self.disk_name.setReadOnly(True)
            self.category.setCurrentText(snippet.category)
            self.content.setPlainText(snippet.content)
        self.ui.findChild(QPushButton, 'media').clicked.connect(self.attach_media)
        self.ui.findChild(QPushButton, 'preview').clicked.connect(self.show_preview)
        self.ui.findChild(QPushButton, 'save').clicked.connect(self.save)
        self.ui.findChild(QPushButton, 'cancel').clicked.connect(self.reject)
        self.ui.findChild(QPushButton, 'advanced').clicked.connect(
            lambda: self.disk_name.setVisible(not self.disk_name.isVisible()))
        self.ui.findChild(QPushButton, 'bold').clicked.connect(lambda: self.format_selection('**', '**'))
        self.ui.findChild(QPushButton, 'heading').clicked.connect(lambda: self.format_selection('# '))
        self.ui.findChild(QPushButton, 'list').clicked.connect(lambda: self.format_selection('- '))
        self.ui.findChild(QPushButton, 'code_block').clicked.connect(
            lambda: self.format_selection('```\n', '\n```'))
        translate_ui(self, localization)

    def save(self):
        try:
            title, content, tags = self.title.text(), self.content.toPlainText(), self.tags.text()
            if not title.strip() or not content.strip():
                raise LibraryError('required')
            if self.snippet:
                # Check move conflicts before committing the edited content.
                self.snippet = self.library.move(self.snippet.id, self.category.currentText())
                self.snippet = self.library.update(self.snippet.id, title=title, content=content, tags=tags)
            else:
                self.snippet = self.library.create(title, self.category.currentText(), content, tags,
                                                   disk_name=self.disk_name.text().strip() or None,
                                                   media=self.pending_media)
        except (LibraryError, OSError) as error:
            self.messages.error_key('errors.' + (str(error) if isinstance(error, LibraryError) else 'io'))
            return
        self.accept()

    def attach_media(self):
        source, _ = QFileDialog.getOpenFileName(self, self.localization.text('snips.attach'))
        if not source:
            return
        try:
            if self.snippet:
                relative = self.library.add_media(self.snippet.id, source)
            else:
                if Path(source).name.casefold() in {Path(p).name.casefold() for p in self.pending_media}:
                    raise LibraryError('name_exists')
                relative = self.library.media_reference(source)
                self.pending_media.append(source)
            name = Path(source).name.replace('[', '').replace(']', '')
            image = Path(source).suffix.lower() in {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg'}
            self.content.insertPlainText(('!' if image else '') + f'[{name}]({quote(relative)})')
        except (LibraryError, OSError) as error:
            self.messages.error_key('errors.' + (str(error) if isinstance(error, LibraryError) else 'io'))

    def show_preview(self):
        try:
            base = self.library.media_base(self.snippet.id) if self.snippet else None
            render_markdown(self.preview, self.content.toPlainText(), base)
            self.content_stack.setCurrentIndex(1 - self.content_stack.currentIndex())
        except (LibraryError, OSError) as error:
            self.messages.error_key('errors.' + (str(error) if isinstance(error, LibraryError) else 'io'))

    def format_selection(self, before, after=''):
        cursor = self.content.textCursor()
        selected = cursor.selectedText().replace('\u2029', '\n')
        cursor.insertText(before + selected + after)
        self.content.setTextCursor(cursor)
        self.content.setFocus()
