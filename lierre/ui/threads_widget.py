

from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot

from .models import ThreadListModel, TagsListModel
from .threads_widget_ui import Ui_Form


class ThreadsWidget(QWidget, Ui_Form):
    def __init__(self, *args, **kwargs):
        super(ThreadsWidget, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.threadsView.activated.connect(self._openThread)

        app = QApplication.instance()
        self.tagsView.setModel(TagsListModel(app.db))
        self.tagsView.tagActivated.connect(self.tagActivated)

        self.threadsView.setModel(ThreadListModel())
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
        app = QApplication.instance()

        query_text = self.searchLine.text()
        q = app.db.create_query(query_text)
        self.threadsView.model().setQuery(q)
        self.setWindowTitle(self.tr('Query: %s') % query_text)

    def setQueryAndSearch(self, text):
        self.searchLine.setText(text)
        self.doSearch()

