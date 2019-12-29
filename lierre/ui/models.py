# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

from copy import deepcopy
from hashlib import sha1
import json
import logging
from enum import IntFlag, auto as enum_auto
import re

from PyQt5.QtCore import (
    QModelIndex, QVariant, QAbstractItemModel, Qt, QMimeData, pyqtSlot as Slot,
)
from PyQt5.QtGui import QBrush, QColor
from lierre.config import CONFIG
from lierre.utils.date import short_datetime
from lierre.utils.addresses import get_sender
from lierre.utils.db_ops import (
    iter_thread_messages, get_thread_by_id, EXCERPT_BUILDER, open_db_rw,
    open_db,
)
from lierre.change_watcher import WATCHER, diff_sorted


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


def flatten_depth_first(tree_dict):
    def _build(msg):
        for sub in tree_dict.get(msg, ()):
            ret.append(sub)
            _build(sub)

    ret = []
    _build(None)
    return ret


class BasicTreeModel(QAbstractItemModel):
    def __init__(self, *args, **kwargs):
        super(BasicTreeModel, self).__init__(*args, **kwargs)

        self.objs = {}
        self.tree = {None: []}
        self.parents = {}

    # QAbstractItemModel
    def index(self, row, col, parent_qidx=QModelIndex()):
        oparent = parent_qidx.internalPointer()
        children = self.tree.get(self._to_key(oparent), ())
        if row >= len(children) or col >= len(self.columns):
            return QModelIndex()
        # column
        return self.createIndex(row, col, self.objs[children[row]])

    def parent(self, qidx):
        item = qidx.internalPointer()
        if item is None:
            return QModelIndex()

        parent = self.parents[self._to_key(item)]
        if parent is None:
            return QModelIndex()

        gparent = self.parents[parent]
        row = self.tree[gparent].index(parent)
        return self.createIndex(row, 0, self.objs[parent])

    def flags(self, qidx):
        obj = qidx.internalPointer()
        if obj is None:
            return Qt.NoItemFlags
        else:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def rowCount(self, qidx=QModelIndex()):
        if qidx.column() != 0 and qidx.isValid():
            return 0
        item = qidx.internalPointer()
        return len(self.tree.get(self._to_key(item), ()))

    def columnCount(self, qidx=QModelIndex()):
        if qidx.column() != 0 and qidx.isValid():
            return 0
        return len(self.columns)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return QVariant()
        elif section >= len(self.columns):
            return QVariant()
        return self.columns[section][0]

    def hasChildren(self, qidx=QModelIndex()):
        item = qidx.internalPointer()
        return bool(len(self.tree.get(self._to_key(item), ())))

    def canFetchMore(self, qidx):
        return False

    def fetchMore(self, qidx):
        pass

    # custom
    def _to_key(self, obj):
        return obj['key'] if obj else None

    def _setTree(self, tree, objs):
        self.modelAboutToBeReset.emit()

        self.objs = objs
        self.tree = tree
        self.parents = {}
        for msg in self.tree:
            for sub in self.tree[msg]:
                self.parents[sub] = msg

        self.modelReset.emit()


class BasicListModel(QAbstractItemModel):
    def __init__(self, *args, **kwargs):
        super(BasicListModel, self).__init__(*args, **kwargs)

        self.objs = []

    # QAbstractItemModel
    def index(self, row, col, parent_qidx=QModelIndex()):
        parent = parent_qidx.internalPointer()
        if parent:
            return QModelIndex()

        if row >= len(self.objs) or col >= len(self.columns):
            return QModelIndex()
        # column
        return self.createIndex(row, col, self.objs[row])

    def parent(self, qidx):
        return QModelIndex()

    def flags(self, qidx):
        obj = qidx.internalPointer()
        if obj is None:
            return Qt.NoItemFlags
        else:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def rowCount(self, qidx=QModelIndex()):
        if qidx.column() != 0 and qidx.isValid():
            return 0
        item = qidx.internalPointer()
        if item:
            return 0
        else:
            return len(self.objs)

    def columnCount(self, qidx=QModelIndex()):
        if qidx.column() != 0 and qidx.isValid():
            return 0
        return len(self.columns)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return QVariant()
        elif section >= len(self.columns):
            return QVariant()
        return self.columns[section][0]

    def hasChildren(self, qidx=QModelIndex()):
        item = qidx.internalPointer()
        return not item

    def canFetchMore(self, qidx):
        return False

    def fetchMore(self, qidx):
        pass

    # custom
    def _setObjs(self, objs):
        self.modelAboutToBeReset.emit()
        self.objs = objs
        self.modelReset.emit()

    def _sort_key(self, d):
        raise NotImplementedError()

    def _updateObjs(self, new_objs):
        old_keys = [self._sort_key(d) for d in self.objs]
        new_keys = [self._sort_key(d) for d in new_objs]

        n = 0
        for old, new in diff_sorted(old_keys, new_keys):
            if old is None:
                self.beginInsertRows(QModelIndex(), n, n)
                self.objs.insert(n, new_objs[n])
                self.endInsertRows()
                n += 1
            elif new is None:
                self.beginRemoveRows(QModelIndex(), n, n)
                del self.objs[n]
                self.endRemoveRows()
            else:
                assert old == new
                # warning: letting self.objs[n] to another object will lead
                # to crashes as a view can keep an old QModelIndex with an
                # old dict that we would be freeing right now.
                # thus we need to mutate the existing dict
                self.objs[n].clear()
                self.objs[n].update(new_objs[n])

                qidx1 = self.index(n, 0)
                qidx2 = qidx1.siblingAtColumn(self.columnCount() - 1)
                self.dataChanged.emit(qidx1, qidx2, [])
                n += 1


class MaildirFlags(IntFlag):
    Unread = enum_auto()
    Flagged = enum_auto()
    Replied = enum_auto()
    Passed = enum_auto()
    Draft = enum_auto()
    Trashed = enum_auto()

    @classmethod
    def tags_to_flags(cls, tags):
        flags = cls(0)

        # these are special notmuch tags: https://notmuchmail.org/special-tags/
        mapping = {member.name.lower(): member for member in cls}
        for tag in tags:
            if tag in mapping:
                flags |= mapping[tag]

        return flags


class ThreadMessagesModel(BasicTreeModel):
    MessageIdRole = register_role()
    MessageFilenameRole = register_role()
    MessageFileRole = register_role()
    MessageObjectRole = register_role()
    MessageFlagsRole = register_role()

    columns = (
        ('Sender', 'sender'),
        ('Excerpt', 'excerpt'),
        ('Date', 'date'),
    )

    def __init__(self, thread_id, *args, **kwargs):
        super(ThreadMessagesModel, self).__init__(*args, **kwargs)

        EXCERPT_BUILDER.builtExcerpt.connect(self._builtExcerpt)

        with open_db() as db:
            thread = get_thread_by_id(db, thread_id)
            tree = build_thread_tree(thread)

            objs = {
                obj.get_message_id(): self._dict_from_obj(obj)
                for obj in flatten_depth_first(tree)
            }

            tree = {
                msg.get_message_id() if msg else None: [sub.get_message_id() for sub in tree[msg]]
                for msg in tree
            }

        self._setTree(tree, objs)
        # if building the tree here and it's built somewhere else too -> crash
        # self.tree = build_thread_tree(thread)

    def _dict_from_obj(self, msg):
        excerpt = EXCERPT_BUILDER.getOrBuild(msg.get_message_id())

        return {
            'filename': msg.get_filename(),
            'key': msg.get_message_id(),
            'sender': msg.get_header('From'),
            'date': msg.get_date(),
            'excerpt': excerpt,
            'tags': list(msg.get_tags()),
        }

    def data(self, qidx, role=Qt.DisplayRole):
        item = qidx.internalPointer()
        if item is None:
            return QVariant()

        if role == self.MessageIdRole:
            return QVariant(item['key'])
        elif role == self.MessageFilenameRole:
            return QVariant(item['filename'])
        elif role == self.MessageObjectRole:
            raise NotImplementedError()
            return QVariant(item)
        elif role == self.MessageFlagsRole:
            return QVariant(MaildirFlags.tags_to_flags(item['tags']))
        elif role == Qt.DisplayRole:
            name = self.columns[qidx.column()][1]
            data = item[name]
            if name == 'sender':
                data = get_sender(data)
            elif name == 'date':
                data = short_datetime(data)
            return QVariant(data)

        return QVariant()

    @Slot(str, str)
    def _builtExcerpt(self, msg_id, text):
        self.objs[msg_id]['excerpt'] = text

        parent = self.parents[msg_id]
        row = self.tree[parent].index(msg_id)

        qidx = self.createIndex(row, 2, self.objs[msg_id])
        self.dataChanged.emit(qidx, qidx)

    def _itemToIndex(self, key):
        parent = self.parents[key]
        row = self.tree[parent].index(key)
        return self.createIndex(row, 0, self.objs[key])

    def findById(self, msg_id):
        return self._itemToIndex(msg_id)


def tag_to_colors(tag):
    ancestors = [tag[:match.start()] for match in re.finditer('/', tag)]
    ancestors.append(tag)
    ancestors.reverse()
    ancestors.append('*')

    bg = None
    for ancestor in ancestors:
        bg = CONFIG.get('ui', 'tag_colors', ancestor, default=None)
        if bg is not None:
            break

    if bg is not None:
        bg = QColor(bg)
    else:
        r, g, b = sha1(tag.encode('utf-8')).digest()[:3]
        bg = QColor(r, g, b)

    return QBrush(_fg_from_bg_color(bg)), QBrush(bg)


def _fg_from_bg_color(qcolor):
    if qcolor.red() + qcolor.green() + qcolor.blue() < 128 * 3:
        return QColor('white')
    else:
        return QColor('black')


class TagsListModel(BasicListModel):
    UnreadRole = register_role()
    TotalRole = register_role()

    columns = (
        ('Name', 'display_name'),
        ('Unread', 'unread_text'),
    )

    def __init__(self, db, *args, **kwargs):
        super(TagsListModel, self).__init__(*args, **kwargs)
        objs = self._build_objs(db)
        self._setObjs(objs)

        WATCHER.globalRefresh.connect(self.refresh, Qt.QueuedConnection)
        WATCHER.tagMailAdded.connect(self.refresh, Qt.QueuedConnection)
        WATCHER.tagMailRemoved.connect(self.refresh, Qt.QueuedConnection)

    def _build_objs(self, db):
        return [
            {
                'name': tag,
                'unread': db.create_query('tag:%s AND tag:unread' % tag).count_messages(),
                'total': db.create_query('tag:%s' % tag).count_messages(),
            }
            for tag in db.get_all_tags()
        ]

    def supportedDropActions(self):
        return Qt.LinkAction

    def _get_name(self, item):
        return QVariant(item['name'])

    def _get_display_name(self, item):
        return QVariant(item.get('display_name') or item['name'])

    def _get_unread_text(self, item):
        return QVariant(f'{item["unread"]}/{item["total"]}')

    def data(self, qidx, role=Qt.DisplayRole):
        item = qidx.internalPointer()
        if item is None:
            return QVariant()

        if role == Qt.DisplayRole:
            name = self.columns[qidx.column()][1]
            cb = getattr(self, '_get_%s' % name)
            return cb(item)
        elif role == Qt.ForegroundRole:
            return QVariant(tag_to_colors(item['name'])[0])
        elif role == Qt.BackgroundRole:
            return QVariant(tag_to_colors(item['name'])[1])
        elif role == self.UnreadRole:
            return QVariant(item['unread'])
        elif role == self.TotalRole:
            return QVariant(item['total'])

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

        with open_db_rw() as db:
            for id in ids:
                thread = get_thread_by_id(db, id)
                for message in iter_thread_messages(thread):
                    message.add_tag(tag)

        return True

    @Slot()
    def refresh(self):
        with open_db() as db:
            new_objs = self._build_objs(db)
        self._updateObjs(new_objs)

    def _sort_key(self, d):
        return d['name']


class CheckableTagsListModel(TagsListModel):
    def __init__(self, db, *args, **kwargs):
        super(CheckableTagsListModel, self).__init__(db, *args, **kwargs)
        self.checked = {}

    def get_checked(self):
        checked = set(tag for tag in self.checked if self.checked[tag] == Qt.Checked)
        semi = set(tag for tag in self.checked if self.checked[tag] == Qt.PartiallyChecked)
        return checked, semi

    def set_checked(self, new, semi=()):
        self.checked.clear()
        self.checked.update((t, Qt.Checked) for t in new)
        self.checked.update((t, Qt.PartiallyChecked) for t in semi)

        self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, 0), [Qt.CheckStateRole])

    def flags(self, qidx):
        flags = super(CheckableTagsListModel, self).flags(qidx)
        if flags & Qt.ItemIsEnabled:
            flags |= Qt.ItemIsUserCheckable

        return flags

    def data(self, qidx, role=Qt.DisplayRole):
        if role != Qt.CheckStateRole:
            return super(CheckableTagsListModel, self).data(qidx, role)

        item = qidx.internalPointer()
        if item is None:
            return QVariant()

        return QVariant(self.checked.get(item['name'], Qt.Unchecked))

    def setData(self, qidx, value, role):
        item = qidx.internalPointer()
        if item is None or role != Qt.CheckStateRole:
            return False

        item.pop('_gap', None)
        self.checked[item['name']] = value

        self.dataChanged.emit(qidx, qidx, [role])
        return True

    @Slot(str)
    def setNewTagItem(self, tag):
        def to_label():
            return self.tr('New tag: %s') % tag

        new = deepcopy(self.objs)

        if tag in set(obj['name'] for obj in self.objs):
            tag = ''

        if new and new[-1].get('_gap'):
            if tag:
                new[-1]['display_name'] = to_label()
                new[-1]['name'] = tag
                new[-1]['_gap'] = tag
            else:
                del new[-1]
        else:
            if tag:
                new.append({
                    'display_name': to_label(),
                    'unread': 0,
                    'name': tag,
                    '_gap': True,
                })
        self._updateObjs(new)


class ThreadListModel(BasicListModel):
    ThreadIdRole = register_role()
    ThreadFlagsRole = register_role()
    ThreadTagsRole = register_role()

    columns = (
        ('Subject', 'subject'),
        ('Authors', 'authors'),
        ('Messages', 'messages_count'),
        ('Last update', 'last_update'),
    )

    def __init__(self, *args, **kwargs):
        super(ThreadListModel, self).__init__(*args, **kwargs)
        self.query_text = None
        self.indexes = {}
        WATCHER.globalRefresh.connect(self.refresh, Qt.QueuedConnection)
        WATCHER.mailAdded.connect(self.refresh, Qt.QueuedConnection)
        WATCHER.tagMailAdded.connect(self.refreshOneMail, Qt.QueuedConnection)
        WATCHER.tagMailRemoved.connect(self.refreshOneMail, Qt.QueuedConnection)

    def setQuery(self, db, query_text):
        self.query_text = query_text
        objs = self._build_objs(db)
        self._setObjs(objs)
        # TODO: generalise this "indexes" mechanism to other models?
        self.indexes = {obj['id']: n for n, obj in enumerate(objs)}

    def _build_objs(self, db):
        query = db.create_query(self.query_text)
        return [self._thread_to_dict(thread) for thread in query.search_threads()]

    def _thread_to_dict(self, thread):
        return {
            'id': thread.get_thread_id(),
            'authors': thread.get_authors(),
            'subject': thread.get_subject(),
            'messages_count': thread.get_total_messages(),
            'last_update': thread.get_newest_date(),
            'tags': list(thread.get_tags()),
        }

    def _get_messages_count(self, thread):
        return QVariant(str(()))

    def _get_last_update(self, thread):
        return QVariant(short_datetime(()))

    def data(self, qidx, role=Qt.DisplayRole):
        item = qidx.internalPointer()
        if item is None:
            return QVariant()

        if role == self.ThreadFlagsRole:
            return QVariant(MaildirFlags.tags_to_flags(item['tags']))
        elif role == self.ThreadTagsRole:
            return QVariant(item['tags'])
        elif role == Qt.DisplayRole:
            name = self.columns[qidx.column()][1]
            data = item[name]
            if name == 'last_update':
                data = short_datetime(data)
            elif name == 'messages_count':
                data = str(data)
            return QVariant(data)
        elif role == self.ThreadIdRole:
            return item['id']

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

    @Slot()
    def refresh(self):
        if not self.query_text:
            return
        with open_db() as db:
            objs = self._build_objs(db)
        self._updateObjs(objs)
        self.indexes = {obj['id']: n for n, obj in enumerate(objs)}

    @Slot(str, str)
    def refreshOneMail(self, _, msgid):
        with open_db() as db:
            query = db.create_query(f'id:{msgid}')
            if hasattr(query, 'set_omit_excluded'):
                # FIXME remove condition when function is integrated in notmuch bindings
                query.set_omit_excluded(query.EXCLUDE.FALSE)
            thread = next(iter(query.search_threads()))
            tid = thread.get_thread_id()

            try:
                row = self.indexes[tid]
            except KeyError:
                return

            new_obj = self._thread_to_dict(thread)

        self.objs[row].clear()
        self.objs[row].update(new_obj)

        qidx1 = self.index(row, 0)
        qidx2 = qidx1.siblingAtColumn(self.columnCount() - 1)
        self.dataChanged.emit(qidx1, qidx2, [])

    def _sort_key(self, d):
        return (-d['last_update'], d['id'])
