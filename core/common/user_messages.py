from PySide6.QtWidgets import QMessageBox


class UserMessageManager:
    """GUI messages only. No hooks, traceback processing or routine logging."""
    def __init__(self, parent, localization):
        self.parent = parent
        self.localization = localization

    def info(self, text):
        QMessageBox.information(self.parent, self.localization.text('messages.info'), text)

    def warning(self, text):
        QMessageBox.warning(self.parent, self.localization.text('messages.warning'), text)

    def error(self, text):
        QMessageBox.critical(self.parent, self.localization.text('messages.error'), text)

    def confirm(self, text):
        box = QMessageBox(self.parent)
        box.setWindowTitle(self.localization.text('messages.confirm'))
        box.setText(text)
        box.setIcon(QMessageBox.Icon.Question)
        yes = box.addButton(self.localization.text('common.yes'), QMessageBox.ButtonRole.YesRole)
        no = box.addButton(self.localization.text('common.no'), QMessageBox.ButtonRole.NoRole)
        box.setDefaultButton(no)
        box.exec()
        return box.clickedButton() == yes

    def error_key(self, key):
        self.error(self.localization.text(key))
