

from PyQt5.QtWidgets import QWidget, QStyledItemDelegate
from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
from lierre.utils.db_ops import open_db

from .models import ThreadListModel, TagsListModel
from .threads_widget_ui import Ui_Form


class ThreadDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, qidx):
        super(ThreadDelegate, self).initStyleOption(option, qidx)
        if qidx.sibling(qidx.row(), 0).data(qidx.model().ThreadHasUnreadRole):
            option.font.setBold(True)


class ThreadsWidget(QWidget, Ui_Form):
    def __init__(self, *args, **kwargs):
        super(ThreadsWidget, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.threadsView.activated.connect(self._openThread)

        with open_db() as db:
            self.tagsView.setModel(TagsListModel(db))
        self.tagsView.tagActivated.connect(self.tagActivated)

        self.threadsView.setModel(ThreadListModel())
        self.threadsView.setItemDelegate(ThreadDelegate())
        self.threadsView.setDragEnabled(True)

        self.searchLine.returnPressed.connect(self.doSearch)
        self.searchButton.clicked.connect(self.doSearch)

    def _openThread(self, qidx):
        tid = qidx.data(ThreadListModel.ThreadIdRole)
        self.threadActivated.emit(tid)

    threadActivated = Signal(str)
    tagActivated = Signal(str)

    @Slot()
    def doSearch(self):
        query_text = self.searchLine.text()
        with open_db() as db:
            q = db.create_query(query_text)
            self.threadsView.model().setQuery(q)
        self.setWindowTitle(self.tr('Query: %s') % query_text)

    def setQueryAndSearch(self, text):
        self.searchLine.setText(text)
        self.doSearch()

