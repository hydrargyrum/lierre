# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

from itertools import chain
import json
from logging import getLogger
from pathlib import Path

from PyQt5.QtCore import (
    QModelIndex, QVariant, Qt, QMimeData, QSortFilterProxyModel,
)
from PyQt5.QtCore import pyqtSlot as Slot, pyqtSignal as Signal
from PyQt5.QtWidgets import QWidget
from lierre.utils.db_ops import open_db
from lierre.utils.maildir_ops import MaildirPP
from lierre.utils.date import short_datetime
from lierre.utils.addresses import get_sender

from .ui_loader import load_ui_class
from .models import BasicTreeModel, BasicListModel, register_role


LOGGER = getLogger(__name__)

Ui_Form = load_ui_class('folders_widget', 'Ui_Form')


class FoldersModel(BasicTreeModel):
    FolderFilenameRole = register_role()
    FolderObjectRole = register_role()

    columns = (
        ('Box', 'box'),
    )

    messageMoved = Signal()

    def __init__(self, *args, **kwargs):
        super(FoldersModel, self).__init__(*args, **kwargs)
        self.refresh()

    def refresh(self):
        root = MaildirPP()

        tree = {}
        objs = {}
        for folder in sorted(root.list_folders()):
            if folder.parts:
                objs[folder.parts] = {
                    'key': folder.parts,
                    'box': folder.parts[-1],
                    'obj': folder,
                }
                tree.setdefault(folder.parts[:-1], []).append(folder.parts)
            else:  # INBOX
                objs[folder.parts] = {
                    'key': folder.parts,
                    'box': 'INBOX',
                    'obj': folder,
                }
                tree.setdefault(None, []).append(folder.parts)

        self._setTree(tree, objs)

    def data(self, qidx, role=Qt.DisplayRole):
        item = qidx.internalPointer()
        if item is None:
            return QVariant()

        if role == self.FolderFilenameRole:
            return QVariant(item['obj'].dir)
        elif role == self.FolderObjectRole:
            return QVariant(item['obj'])
        elif role == Qt.DisplayRole:
            name = self.columns[qidx.column()][1]
            data = item[name]
            return QVariant(data)

        return QVariant()

    def flags(self, qidx):
        flags = super(FoldersModel, self).flags(qidx)
        if flags & Qt.ItemIsEnabled:
            flags |= Qt.ItemIsDropEnabled
        return flags

    def supportedDropActions(self):
        return Qt.MoveAction

    def mimeTypes(self):
        return ['text/x-lierre-messages']

    def dropMimeData(self, mime, action, row, column, parent_qidx):
        root = MaildirPP()

        data = bytes(mime.data('text/x-lierre-messages')).decode('ascii')
        if not data:
            return False

        try:
            paths = json.loads(data)
        except ValueError:
            LOGGER.warning('failed to decode dropped data')
            return False

        if row == column == -1:
            qidx = parent_qidx.siblingAtColumn(0)
        else:
            qidx = parent_qidx.child(row, 0)

        folder = qidx.data(self.FolderObjectRole)
        for msg_path in paths:
            root.move_message(msg_path, folder)
            self.messageMoved.emit()

        return True


class FolderMessagesModel(BasicListModel):
    MessageFileRole = register_role()

    columns = (
        ('Date', 'date'),
        ('Author', 'sender'),
        ('Subject', 'subject'),
    )

    path = None

    def setPath(self, path):
        self.path = path
        self.refresh()

    @Slot()
    def refresh(self):
        objs = []
        with open_db() as db:
            sub_iter = chain(
                self.path.joinpath('new').iterdir(),
                self.path.joinpath('cur').iterdir(),
            )
            for msg_path in sub_iter:
                msg = db.find_message_by_filename(str(msg_path))
                if msg is None:
                    continue

                objs.append({
                    'date': msg.get_date(),
                    'tags': frozenset(msg.get_tags()),
                    'subject': msg.get_header('subject'),
                    'sender': msg.get_header('From'),
                    'message_id': msg.get_message_id(),
                    'thread_id': msg.get_thread_id(),
                    'path': msg_path,
                })

        self._setObjs(objs)

    def data(self, qidx, role=Qt.DisplayRole):
        item = qidx.internalPointer()
        if item is None:
            return QVariant()

        if role == self.MessageFileRole:
            return QVariant(str(item['path']))
        elif role == Qt.DisplayRole:
            name = self.columns[qidx.column()][1]
            data = item[name]

            if name == 'sender':
                data = get_sender(data)
            elif name == 'date':
                data = short_datetime(data)

            return QVariant(data)

        return QVariant()

    def supportedDragActions(self):
        return Qt.MoveAction

    def flags(self, qidx):
        flags = super(FolderMessagesModel, self).flags(qidx)
        if flags & Qt.ItemIsEnabled:
            flags |= Qt.ItemIsDragEnabled
        return flags

    def mimeTypes(self):
        return ['text/x-lierre-messages']

    def mimeData(self, qidxs):
        paths = [qidx.data(self.MessageFileRole) for qidx in qidxs if qidx.column() == 0]
        mime = QMimeData()
        mime.setData('text/x-lierre-messages', json.dumps(paths).encode('ascii'))
        return mime


class MessageSorter(QSortFilterProxyModel):
    def lessThan(self, a, b):
        assert a.column() == b.column()

        if a.column() == 0:
            return a.internalPointer()['date'] < b.internalPointer()['date']
        return super(MessageSorter, self).lessThan(a, b)


class FoldersWidget(QWidget, Ui_Form):
    def __init__(self, *args, **kwargs):
        super(FoldersWidget, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.folderTree.setModel(FoldersModel(parent=self))
        self.folderTree.expandAll()
        self.folderTree.activated.connect(self._folderActivated)

        self.messageModel = FolderMessagesModel(parent=self)
        sorter = MessageSorter(parent=self)
        sorter.setSourceModel(self.messageModel)
        self.messageList.setModel(sorter)

        self.folderTree.model().messageMoved.connect(self.messageModel.refresh)

    @Slot(QModelIndex)
    def _folderActivated(self, qidx):
        dir = qidx.data(FoldersModel.FolderFilenameRole)
        self.messageModel.setPath(Path(dir))
