# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

from datetime import datetime
from logging import getLogger, Handler, ERROR
from weakref import ref

from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QLabel, QDialog, QTableWidgetItem

from .ui_loader import load_ui_class


LOGS = []
WIDGETS = []


class ErrorKeeper(Handler):
    def emit(self, record):
        LOGS.append(record)

        for w in WIDGETS:
            w = w()
            if w:
                w.add_log(record)


class ErrorIndicator(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        WIDGETS.append(ref(self))

    def add_log(self, _):
        icon = QIcon.fromTheme('dialog-error').pixmap(16, 16)
        self.setPixmap(icon)

    def mousePressEvent(self, event):
        self.setPixmap(QPixmap())

        for widget in WIDGETS:
            widget = widget()
            if isinstance(widget, ErrorListDialog):
                widget.raise_()
                widget.activateWindow()
                break
        else:
            ErrorListDialog(parent=self.window()).show()


Ui_Dialog = load_ui_class('error_logs', 'Ui_Dialog')


class ErrorListDialog(QDialog, Ui_Dialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setupUi(self)

        WIDGETS.append(ref(self))

        for record in LOGS:
            self.add_log(record)

    def add_log(self, record):
        self.logsTable.setRowCount(self.logsTable.rowCount() + 1)

        dt = datetime.fromtimestamp(record.created)
        self.logsTable.setItem(self.logsTable.rowCount() - 1, 0, QTableWidgetItem(dt.strftime('%Y-%m-%d %H:%M:%S')))
        self.logsTable.setItem(self.logsTable.rowCount() - 1, 1, QTableWidgetItem(record.module))
        self.logsTable.setItem(self.logsTable.rowCount() - 1, 2, QTableWidgetItem(record.getMessage()))


def install():
    handler = ErrorKeeper()
    handler.setLevel(ERROR)
    getLogger().addHandler(handler)
