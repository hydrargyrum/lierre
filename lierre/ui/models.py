
from hashlib import sha1
import json
import logging

from PyQt5.QtCore import (
    QModelIndex, QVariant, QAbstractItemModel, Qt, QMimeData,
)
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import QApplication

from ..utils.date import short_datetime
from ..utils.addresses import get_sender
from ..utils.db_ops import iter_thread_messages, get_thread_by_id


LOGGER = logging.getLogger(__name__)

LAST_ROLE = Qt.UserRole


def register_role():
    global LAST_ROLE

    LAST_ROLE += 1
    return LAST_ROLE


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


class BasicModel(QAbstractItemModel):
    def __init__(self, *args, **kwargs):
        super(BasicModel, self).__init__(*args, **kwargs)

        self.tree = {None: []}
        self.parents = {}

    # QAbstractItemModel
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

    # custom
    def _setTree(self, tree):
        self.modelAboutToBeReset.emit()

        self.tree = tree
        self.parents = {}
        for msg in self.tree:
            for sub in self.tree[msg]:
                self.parents[sub] = msg

        self.modelReset.emit()


class ThreadMessagesModel(BasicModel):
    MessageIdRole = register_role()
    MessageFileRole = register_role()
    MessageObjectRole = register_role()

    columns = (
        ('Sender', 'sender'),
        ('Date', 'date'),
    )

    def __init__(self, tree, *args, **kwargs):
        super(ThreadMessagesModel, self).__init__(*args, **kwargs)
        self._setTree(tree)
        # if building the tree here and it's built somewhere else too -> crash
        # self.tree = build_thread_tree(thread)

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


def tag_to_colors(tag):
    r, g, b = sha1(tag.encode('utf-8')).digest()[:3]
    bg = QBrush(QColor(r, g, b))
    if r + g + b < 128 * 3:
        fg = QBrush(QColor('white'))
    else:
        fg = QBrush(QColor('black'))

    return fg, bg


class TagsListModel(BasicModel):
    columns = (
        ('Name', 'name'),
        ('Unread', 'unread_text'),
    )

    def __init__(self, db, *args, **kwargs):
        super(TagsListModel, self).__init__(*args, **kwargs)
        self.db = db
        tree = {
            None: [
                (tag, self.db.create_query('tag:%s AND tag:unread' % tag).count_threads())
                for tag in db.get_all_tags()
            ],
        }
        self._setTree(tree)

    def supportedDropActions(self):
        return Qt.LinkAction

    def _get_name(self, item):
        return QVariant(item[0])

    def _get_unread_text(self, item):
        text = str(item[1]) if item[1] else ''
        return QVariant(text)

    def data(self, qidx, role):
        item = qidx.internalPointer()
        if item is None:
            return QVariant()

        if role == Qt.DisplayRole:
            name = self.columns[qidx.column()][1]
            cb = getattr(self, '_get_%s' % name)
            return cb(item)
        elif role == Qt.ForegroundRole:
            return QVariant(tag_to_colors(item[0])[0])
        elif role == Qt.BackgroundRole:
            return QVariant(tag_to_colors(item[0])[1])

        return QVariant()

    def flags(self, qidx):
        flags = super(TagsListModel, self).flags(qidx)
        if flags & Qt.ItemIsEnabled:
            flags |= Qt.ItemIsDropEnabled
        return flags

    def mimeTypes(self):
        return ['text/x-lierre-threads']

    def dropMimeData(self, mime, action, row, column, parent_qidx):
        data = bytes(mime.data('text/x-lierre-threads')).decode('ascii')
        if not data:
            return False

        try:
            ids = json.loads(data)
        except ValueError:
            logging.warning('failed to decode dropped data')
            return False

        if row == column == -1:
            qidx = parent_qidx.siblingAtColumn(0)
        else:
            qidx = parent_qidx.child(row, 0)

        tag = qidx.data()

        app = QApplication.instance()
        for id in ids:
            thread = get_thread_by_id(app.db, id)
            for message in iter_thread_messages(thread):
                message.add_tag(tag)

        return True


class ThreadListModel(BasicModel):
    ThreadIdRole = register_role()

    columns = (
        ('Authors', 'authors'),
        ('Subject', 'subject'),
        ('Messages', 'messages_count'),
        ('Last update', 'last_update'),
    )

    def setQuery(self, query):
        tree = {None: list(query.search_threads())}
        self._setTree(tree)

    def _get_authors(self, thread):
        return QVariant(thread.get_authors())

    def _get_subject(self, thread):
        return QVariant(thread.get_subject())

    def _get_messages_count(self, thread):
        return QVariant(str(thread.get_total_messages()))

    def _get_last_update(self, thread):
        return QVariant(short_datetime(thread.get_newest_date()))

    def data(self, qidx, role):
        item = qidx.internalPointer()
        if item is None:
            return QVariant()

        if role == Qt.DisplayRole:
            name = self.columns[qidx.column()][1]
            cb = getattr(self, '_get_%s' % name)
            return cb(item)
        elif role == self.ThreadIdRole:
            return item.get_thread_id()

        return QVariant()

    def supportedDragActions(self):
        return Qt.LinkAction

    def flags(self, qidx):
        flags = super(ThreadListModel, self).flags(qidx)
        if flags & Qt.ItemIsEnabled:
            flags |= Qt.ItemIsDragEnabled
        return flags

    def mimeTypes(self):
        return ['text/x-lierre-threads']

    def mimeData(self, qidxs):
        ids = [qidx.data(self.ThreadIdRole) for qidx in qidxs]
        mime = QMimeData()
        mime.setData('text/x-lierre-threads', json.dumps(ids).encode('ascii'))
        return mime
