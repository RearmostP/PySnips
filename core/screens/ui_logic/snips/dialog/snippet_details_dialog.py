from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit


class SnippetDetailsDialog(QDialog):
    def __init__(self, snippet_meta: dict, categories: list[str], metadata_manager, parent=None):
        super().__init__(parent)
        self.snippet_meta = snippet_meta
        self.metadata_manager = metadata_manager
        self.original_category = str(snippet_meta.get("category") or "")
        self.updated_meta: dict | None = None

        self.setWindowTitle("פרטי שליף")
        self.resize(460, 220)

        layout = QFormLayout(self)
        self.title_input = QLineEdit(str(snippet_meta.get("title") or ""))
        self.tags_input = QLineEdit(", ".join(metadata_manager.normalize_tags(snippet_meta.get("tags"))))
        self.created_at_input = QLineEdit(metadata_manager.get_created_at(snippet_meta))
        self.category_input = QComboBox()

        categories = list(categories)
        if self.original_category and self.original_category not in categories:
            categories.append(self.original_category)
        self.category_input.addItems(categories)
        if self.original_category:
            self.category_input.setCurrentText(self.original_category)

        self.title_label = QLabel(self.title_input.text())
        self.tags_label = QLabel(self.tags_input.text())
        self.created_at_label = QLabel(self.created_at_input.text())
        self.category_label = QLabel(self.original_category)

        self.detail_fields = [
            (self.title_label, self.title_input),
            (self.tags_label, self.tags_input),
            (self.created_at_label, self.created_at_input),
            (self.category_label, self.category_input),
        ]
        for value_label, value_input in self.detail_fields:
            value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            value_label.setWordWrap(True)
            value_input.hide()

        layout.addRow("כותרת:", self.title_label)
        layout.addRow("", self.title_input)
        layout.addRow("תגיות:", self.tags_label)
        layout.addRow("", self.tags_input)
        layout.addRow("תאריך יצירה:", self.created_at_label)
        layout.addRow("", self.created_at_input)
        layout.addRow("קטגוריה:", self.category_label)
        layout.addRow("", self.category_input)

        for field in self._editable_text_inputs():
            field.setReadOnly(True)

        self.buttons = QDialogButtonBox()
        self.edit_button = self.buttons.addButton("ערוך", QDialogButtonBox.ButtonRole.ActionRole)
        self.save_button = self.buttons.addButton(QDialogButtonBox.StandardButton.Save)
        self.close_button = self.buttons.addButton(QDialogButtonBox.StandardButton.Close)
        self.cancel_button = self.buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.save_button.hide()
        self.cancel_button.hide()

        self.original_values = {
            "title": self.title_input.text(),
            "tags": self.tags_input.text(),
            "created_at": self.created_at_input.text(),
            "category": self.original_category,
        }

        self.edit_button.clicked.connect(lambda: self.set_edit_mode(True))
        self.save_button.clicked.connect(self._accept_with_updates)
        self.close_button.clicked.connect(self.reject)
        self.cancel_button.clicked.connect(self.cancel_edit)
        layout.addRow(self.buttons)

    def set_edit_mode(self, enabled: bool) -> None:
        for field in self._editable_text_inputs():
            field.setReadOnly(not enabled)
        for value_label, value_input in self.detail_fields:
            value_label.setVisible(not enabled)
            value_input.setVisible(enabled)
        self.edit_button.setVisible(not enabled)
        self.close_button.setVisible(not enabled)
        self.save_button.setVisible(enabled)
        self.cancel_button.setVisible(enabled)

    def cancel_edit(self) -> None:
        self.title_input.setText(self.original_values["title"])
        self.tags_input.setText(self.original_values["tags"])
        self.created_at_input.setText(self.original_values["created_at"])
        self.category_input.setCurrentText(self.original_values["category"])
        self.set_edit_mode(False)

    def _accept_with_updates(self) -> None:
        self.updated_meta = {
            **self.snippet_meta,
            "title": self.title_input.text().strip() or "ללא כותרת",
            "tags": self.metadata_manager.normalize_tags(self.tags_input.text()),
            "created_at": self.created_at_input.text().strip(),
            "category": self.category_input.currentText().strip() or self.original_category,
        }
        self.accept()

    def _editable_text_inputs(self) -> list[QLineEdit]:
        return [self.title_input, self.tags_input, self.created_at_input]
