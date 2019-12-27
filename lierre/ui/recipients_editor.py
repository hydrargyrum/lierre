# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

from logging import getLogger
import re

from PyQt5.QtCore import (
    pyqtSlot as Slot, pyqtSignal as Signal, QSize, Qt, QRegExp,
)
from PyQt5.QtGui import (
    QStandardItemModel, QStandardItem, QRegExpValidator,
)
from PyQt5.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QStyledItemDelegate,
    QItemEditorFactory, QLineEdit, QComboBox, QCompleter,
)
from lierre.plugin_manager import PLUGINS


LOGGER = getLogger(__name__)


class RecipientCompleter(QCompleter):
    def __init__(self, *, others, message, **kwargs):
        super().__init__(**kwargs)
        self.activated.connect(self.insertActivated)

        self.others = others
        self.message = message

    def install_on(self, lineedit):
        self.setWidget(lineedit)
        self.setFilterMode(Qt.MatchContains)

        lineedit.textEdited.connect(self.setCompletionPrefix)
        lineedit.textEdited.connect(self.complete)

    def getCompletions(self, s):
        completions = []
        for pname, plugin in PLUGINS['addressbook'].iter_enabled_plugins().items():
            try:
                results = plugin.search_contacts(
                    s,
                    others=self.others,
                    message=self.message
                )
                completions.extend(results)
            except Exception:
                LOGGER.exception('plugin %r could not list completions', pname)
        return completions

    def update(self, s):
        mdl = QStandardItemModel()

        for name, addr in self.getCompletions(s):
            mdl.appendRow(QStandardItem(f'{name} <{addr}>'))

        self.setModel(mdl)

    def splitPath(self, s):
        # QCompleter is built around the idea its model has ALL the completions
        # at hand, but we can't assume this.
        # This method is called almost everytime so this is the best place
        # to rebuilt the completion model as often as possible.
        self.update(s)
        return []

    @Slot(str)
    def insertActivated(self, s):
        self.widget().setText(s)


class TypeFactory(QItemEditorFactory):
    def __init__(self, rcpts, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def createEditor(self, type, parent):
        ret = QComboBox(parent=parent)
        ret.addItem(ret.tr('To'), 'to')
        ret.addItem(ret.tr('Cc'), 'cc')
        ret.addItem(ret.tr('Bcc'), 'bcc')
        return ret


class EditorFactory(QItemEditorFactory):
    def __init__(self, rcpts, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rcpts = rcpts

    def createEditor(self, type, parent):
        ret = QLineEdit(parent=parent)

        pattern = r'\s*[^<\s]+@[^>\s]+\s*|.*<\S+@\S+>\s*'
        validator = QRegExpValidator(QRegExp(pattern), parent=ret)
        ret.setValidator(validator)

        completer = RecipientCompleter(
            parent=ret,
            message=self.rcpts.msg,
            others=self.rcpts.get_recipients(),
        )
        completer.install_on(ret)

        self.rcpts.editStarted.emit(ret)
        return ret


class RecipientsEditor(QTableWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setRowCount(1)
        self.setColumnCount(2)

        self.verticalHeader().hide()
        self.horizontalHeader().hide()
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        self.tdelegate = QStyledItemDelegate()
        self.tdelegate.setItemEditorFactory(TypeFactory(self))
        self.setItemDelegateForColumn(0, self.tdelegate)

        self.edelegate = QStyledItemDelegate()
        self.edelegate.setItemEditorFactory(EditorFactory(self))
        self.setItemDelegateForColumn(1, self.edelegate)

        self.itemChanged.connect(self._updateColumnCount)

        self.setItem(0, 0, QTableWidgetItem('To'))

        self.msg = None

    def set_message(self, msg):
        self.msg = msg

    @Slot(QTableWidgetItem)
    def _updateColumnCount(self, qitem):
        if qitem.column() == 0:
            return

        if not qitem.text().strip():
            if self.rowCount() > 1:
                self.removeRow(qitem.row())
        elif qitem.row() + 1 == self.rowCount():
            cur = self.rowCount()
            self.setRowCount(cur + 1)
            self.setItem(cur, 0, QTableWidgetItem('To'))

    def sizeHint(self):
        return QSize(0, self.sizeHintForRow(0))

    def set_recipients(self, *, to=None, cc=None, bcc=None):
        by_type = {
            'To': to or (),
            'Cc': cc or (),
            'Bcc': bcc or (),
        }

        self.setRowCount(sum(len(addrs) for addrs in by_type.values()) + 1)
        row = 0
        for type_, pairs in by_type.items():
            for name, addr in pairs:
                self.setItem(row, 0, QTableWidgetItem(type_))
                if name:
                    self.setItem(row, 1, QTableWidgetItem(f'{name} <{addr}>'))
                else:
                    self.setItem(row, 1, QTableWidgetItem(addr))
                row += 1

    def get_recipients(self):
        by_type = {
            'To': [],
            'Cc': [],
            'Bcc': [],
        }

        for row in range(self.rowCount() - 1):  # last line is supposed to be empty
            text = self.item(row, 1).text()
            mtc = re.fullmatch(r'(.*)\s*<([^>]+)>\s*', text)
            if mtc:
                name = mtc[1].strip()
                addr = mtc[2]
            else:
                name = ''
                addr = text

            by_type[self.item(row, 0).text()].append((name, addr))

        return by_type

    editStarted = Signal(QLineEdit)
