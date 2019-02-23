

from PyQt5.QtWidgets import QWidget, QStyledItemDelegate, QStyle
from PyQt5.QtGui import QFontMetrics, QPen
from PyQt5.QtCore import (
    pyqtSignal as Signal, pyqtSlot as Slot, Qt, QSize,
)
from lierre.utils.db_ops import open_db
from lierre.config import CONFIG

from .models import ThreadListModel, TagsListModel, MaildirFlags, tag_to_colors
from .threads_widget_ui import Ui_Form


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

        for col, sz in enumerate(CONFIG.get('ui', 'threads_view', 'columns', default=[])):
            self.threadsView.setColumnWidth(col, sz)

        self.threadsView.header().sectionResized.connect(self._saveColumnSizes)

        self.searchLine.returnPressed.connect(self.doSearch)
        self.searchButton.clicked.connect(self.doSearch)

        self.splitter.setStretchFactor(1, 1)

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
