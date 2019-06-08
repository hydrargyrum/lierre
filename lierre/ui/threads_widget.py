
import logging

from PyQt5.QtWidgets import QWidget, QStyledItemDelegate, QStyle, QToolBar
from PyQt5.QtGui import QFontMetrics, QPen
from PyQt5.QtCore import (
    pyqtSignal as Signal, pyqtSlot as Slot, Qt, QSize,
)
from lierre.utils.db_ops import open_db, open_db_rw, get_thread_by_id
from lierre.config import CONFIG
from lierre.change_watcher import WATCHER

from .models import ThreadListModel, TagsListModel, MaildirFlags, tag_to_colors
from .tag_editor import TagEditor
from .ui_loader import load_ui_class


LOGGER = logging.getLogger(__name__)


Ui_Form = load_ui_class('threads_widget', 'Ui_Form')


class ThreadUnreadDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, qidx):
        super(ThreadUnreadDelegate, self).initStyleOption(option, qidx)
        flags = qidx.sibling(qidx.row(), 0).data(qidx.model().ThreadFlagsRole)
        if flags & MaildirFlags.Unread:
            option.font.setBold(True)


class ThreadSubjectDelegate(ThreadUnreadDelegate):
    xpadding = 2
    xmargin = 5
    ymargin = 0

    def _positions(self, option, tags):
        fm = QFontMetrics(option.font)

        for tag in tags:
            sz = fm.size(Qt.TextSingleLine, tag)
            yield sz, tag

    def paint(self, painter, option, qidx):
        self.initStyleOption(option, qidx)

        tags = qidx.sibling(qidx.row(), 0).data(qidx.model().ThreadTagsRole)

        painter.save()
        try:
            if option.state & QStyle.State_Selected:
                painter.setBackground(option.palette.highlight())
            else:
                painter.setBackground(option.palette.base())
            painter.eraseRect(option.rect)

            painter.setClipRect(option.rect)
            painter.translate(option.rect.topLeft())
            painter.setFont(option.font)

            fm = QFontMetrics(option.font)

            x = self.xmargin
            for sz, tag in self._positions(option, tags):
                fg, bg = tag_to_colors(tag)
                painter.setPen(fg.color())

                painter.fillRect(x, self.ymargin, sz.width() + 2 * self.xpadding, fm.height(), bg.color())
                painter.drawText(x + self.xpadding, self.ymargin + fm.ascent(), tag)
                x += sz.width() + self.xmargin + 2 * self.xpadding

            if option.state & QStyle.State_Selected:
                painter.setPen(QPen(option.palette.highlightedText(), 1))
            else:
                painter.setPen(QPen(option.palette.text(), 1))
            painter.drawText(x + self.xpadding, self.ymargin + fm.ascent(), qidx.data())
        finally:
            painter.restore()

    def sizeHint(self, option, qidx):
        tags = qidx.sibling(qidx.row(), 0).data(qidx.model().ThreadTagsRole)

        fm = QFontMetrics(option.font)

        x = self.xmargin
        y = 0
        for sz, tag in self._positions(option, tags):
            x += sz.width() + self.xmargin + 2 * self.xpadding
            y = self.ymargin * 2 + fm.height()

        x += fm.size(Qt.TextSingleLine, qidx.data()).width()

        return QSize(x, y)


def iter_thread_messages(thread):
    def recurse_list(it):
        for msg in it:
            yield msg
            yield from recurse_list(msg.get_replies())

    yield from recurse_list(thread.get_toplevel_messages())


class ThreadsWidget(QWidget, Ui_Form):
    def __init__(self, *args, **kwargs):
        super(ThreadsWidget, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.threadsView.activated.connect(self._openThread)

        with open_db() as db:
            self.tagsView.setModel(TagsListModel(db))
        self.tagsView.tagActivated.connect(self.tagActivated)

        self.threadsView.setModel(ThreadListModel())
        self.threadsView.setItemDelegate(ThreadUnreadDelegate())
        self.threadsView.setItemDelegateForColumn(0, ThreadSubjectDelegate())
        self.threadsView.setDragEnabled(True)
        self.threadsView.selectionModel().selectionChanged.connect(self.updateToolbarState)

        for col, sz in enumerate(CONFIG.get('ui', 'threads_view', 'columns', default=[])):
            self.threadsView.setColumnWidth(col, sz)

        self.threadsView.header().sectionResized.connect(self._saveColumnSizes)

        self.searchLine.returnPressed.connect(self.doSearch)
        self.searchButton.clicked.connect(self.doSearch)

        self.splitter.setStretchFactor(1, 1)

        self.setupToolbar()

    def setupToolbar(self):
        tb = QToolBar()
        self.verticalLayout.insertWidget(0, tb)

        tb.addAction(self.actionArchive)
        self.actionArchive.triggered.connect(self._archiveThreads)

        tb.addAction(self.actionTags)
        self.actionTags.triggered.connect(self.openTagEditor)

        tb.addSeparator()

        tb.addAction(self.actionDelete)
        self.actionDelete.triggered.connect(self._deleteSelectedThreads)

        self.updateToolbarState()

    def _openThread(self, qidx):
        tid = qidx.data(ThreadListModel.ThreadIdRole)
        self.threadActivated.emit(tid)

    threadActivated = Signal(str)
    tagActivated = Signal(str)

    @Slot()
    def doSearch(self):
        query_text = self.searchLine.text()
        with open_db() as db:
            self.threadsView.model().setQuery(db, query_text)
        self.setWindowTitle(self.tr('Query: %s') % query_text)

    def setQueryAndSearch(self, text):
        self.searchLine.setText(text)
        self.doSearch()

    @Slot()
    def _saveColumnSizes(self):
        cols = []
        CONFIG.set('ui', 'threads_view', 'columns', cols)
        for col in range(self.threadsView.model().columnCount()):
            cols.append(self.threadsView.columnWidth(col))

    @Slot()
    def updateToolbarState(self):
        nb_selected = len([
            qidx for qidx in self.threadsView.selectedIndexes()
            if qidx.column() == 0
        ])

        self.actionTags.setEnabled(bool(nb_selected))
        self.actionDelete.setEnabled(bool(nb_selected))
        self.actionArchive.setEnabled(bool(nb_selected))

    def _getSelectedThreads(self):
        return [
            qidx.data(ThreadListModel.ThreadIdRole)
            for qidx in self.threadsView.selectedIndexes()
            if qidx.column() == 0
        ]

    def _iter_selected_threads(self, db):
        thread_ids = self._getSelectedThreads()
        return (get_thread_by_id(db, thread_id) for thread_id in thread_ids)

    @Slot()
    def _deleteSelectedThreads(self):
        with open_db_rw() as db:
            for thread in self._iter_selected_threads(db):
                for msg in iter_thread_messages(thread):
                    LOGGER.debug('marking message deleted %r', msg.get_message_id())
                    msg.add_tag('deleted')
                    WATCHER.tagMailAdded.emit('deleted', msg.get_message_id())

    @Slot()
    def _archiveThreads(self):
        with open_db_rw() as db:
            for thread in self._iter_selected_threads(db):
                for msg in iter_thread_messages(thread):
                    LOGGER.debug('archiving message %r', msg.get_message_id())
                    msg.remove_tag('inbox')
                    WATCHER.tagMailRemoved.emit('inbox', msg.get_message_id())

    @Slot()
    def openTagEditor(self):
        with open_db() as db:
            union_tags = set()
            common_tags = None
            for thread in self._iter_selected_threads(db):
                for msg in iter_thread_messages(thread):
                    msg_tags = set(msg.get_tags())
                    union_tags |= msg_tags
                    if common_tags is None:
                        common_tags = msg_tags
                    else:
                        common_tags &= msg_tags

            union_tags -= common_tags

        w = TagEditor(parent=self)
        w.setCheckedTags(common_tags, union_tags)

        if not w.exec_():
            return

        checked, partially = w.checkedTags()

        with open_db_rw() as db:
            for thread in self._iter_selected_threads(db):
                for msg in iter_thread_messages(thread):
                    msg_tags = set(msg.get_tags())
                    to_remove = msg_tags - (checked | partially)  # unchecked tags
                    to_add = checked - msg_tags  # newly checked tags

                    LOGGER.debug('changing tags for message %r: +(%s) -(%s)', msg.get_message_id(), to_add, to_remove)
                    msg.freeze()

                    for tag in to_remove:
                        msg.remove_tag(tag)
                    for tag in to_add:
                        msg.add_tag(tag)

                    msg.thaw()
                    msg.tags_to_maildir_flags()
                    LOGGER.debug('changed tags for message %r', msg.get_message_id())

                    for tag in to_remove:
                        WATCHER.tagMailRemoved.emit(tag, msg.get_message_id())
                    for tag in to_add:
                        WATCHER.tagMailAdded.emit(tag, msg.get_message_id())

