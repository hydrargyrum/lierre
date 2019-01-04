
from PyQt5.QtCore import (
    QModelIndex, QVariant, QAbstractItemModel, Qt,
)

from ..utils.date import short_datetime
from ..utils.addresses import get_sender


def build_thread_tree(thread):
    def _build(msg):
        it = msg.get_replies()
        for sub in it:
            ret.setdefault(msg, []).append(sub)
            _build(sub)

    ret = {}

    for msg in thread.get_toplevel_messages():
        ret.setdefault(None, []).append(msg)
        _build(msg)

    return ret


class ThreadMessagesModel(QAbstractItemModel):
    MessageIdRole = Qt.UserRole + 1
    MessageFileRole = Qt.UserRole + 2
    MessageObjectRole = Qt.UserRole + 3

    columns = (
        ('Sender', 'sender'),
        ('Date', 'date'),
    )

    def __init__(self, thread, tree, *args, **kwargs):
        super(ThreadMessagesModel, self).__init__(*args, **kwargs)
        self.thread = thread
        self.tree = tree
        # if building the tree here and it's built somewhere else too -> crash
        # self.tree = build_thread_tree(thread)

        self.parents = {}
        for msg in self.tree:
            for sub in self.tree[msg]:
                self.parents[sub] = msg

    def index(self, row, col, parent_qidx):
        parent = parent_qidx.internalPointer()
        children = self.tree.get(parent, ())
        if row >= len(children) or col >= len(self.columns):
            return QModelIndex()
        # column
        return self.createIndex(row, col, children[row])

    def parent(self, qidx):
        item = qidx.internalPointer()
        if item is None:
            return QModelIndex()

        parent = self.parents[item]
        if parent is None:
            return QModelIndex()

        gparent = self.parents[parent]
        row = self.tree[gparent].index(parent)
        return self.createIndex(row, 0, parent)

    def flags(self, qidx):
        obj = qidx.internalPointer()
        if obj is None:
            return Qt.NoItemFlags
        else:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def rowCount(self, qidx):
        if qidx.column() != 0 and qidx.isValid():
            return 0
        item = qidx.internalPointer()
        return len(self.tree.get(item, ()))

    def columnCount(self, qidx):
        if qidx.column() != 0 and qidx.isValid():
            return 0
        return len(self.columns)

    def headerData(self, section, orientation, role):
        if role != Qt.DisplayRole:
            return QVariant()
        elif section >= len(self.columns):
            return QVariant()
        return self.columns[section][0]

    def hasChildren(self, qidx):
        item = qidx.internalPointer()
        return bool(len(self.tree.get(item, ())))

    def canFetchMore(self, qidx):
        return False

    def fetchMore(self, qidx):
        pass

    def _get_sender(self, msg):
        return QVariant(get_sender(msg.get_header('From')))

    def _get_date(self, msg):
        return QVariant(short_datetime(msg.get_date()))

    def data(self, qidx, role):
        item = qidx.internalPointer()
        if item is None:
            return QVariant()

        if role == self.MessageIdRole:
            return QVariant(item.get_message_id())
        elif role == self.MessageFileRole:
            return QVariant(item.get_filename())
        elif role == self.MessageObjectRole:
            return QVariant(item)
        elif role == Qt.DisplayRole:
            name = self.columns[qidx.column()][1]
            cb = getattr(self, '_get_%s' % name)
            return cb(item)

        return QVariant()

