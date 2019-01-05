
from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QTabWidget,
)
from PyQt5.QtCore import pyqtSlot as Slot, pyqtSignal as Signal

from .threads_widget import ThreadsWidget
from .thread_widget import ThreadWidget


def get_thread_by_id(db, id):
    q = db.create_query('thread:%s' % id)
    it = q.search_threads()
    thr = list(it)[0]
    return thr


class TabWidget(QTabWidget):
    def __init__(self, *args, **kwargs):
        super(TabWidget, self).__init__(*args, **kwargs)
        self.setMovable(True)
        self.setTabsClosable(True)

        self.tabCloseRequested.connect(self._closeTabRequested)

        self.addThreads()

    def addThreads(self):
        w = ThreadsWidget()
        idx = self._addTab(w)
        w.threadActivated.connect(self.addThread)
        w.tagActivated.connect(self._addThreadsTag)
        self.setCurrentIndex(idx)
        return w

    def _addThreadsTag(self, tag):
        w = self.addThreads()
        w.setQueryAndSearch('tag:%s' % tag)

    @Slot(str)
    def addThread(self, tid):
        app = QApplication.instance()
        thr = get_thread_by_id(app.db, tid)
        w = ThreadWidget(thr)
        idx = self._addTab(w)
        self.setCurrentIndex(idx)
        return w

    def _addTab(self, widget):
        idx = self.addTab(widget, widget.windowTitle())
        widget.windowTitleChanged.connect(self._tabTitleChanged)
        return idx

    @Slot(int)
    def _closeTabRequested(self, idx):
        if self.count() > 1:
            self.removeTab(idx)

    @Slot(str)
    def _tabTitleChanged(self, title):
        widget = self.sender()
        idx = self.indexOf(widget)
        if idx < 0:
            return

        self.setTabText(idx, title)
        self.someTabTitleChanged.emit()

    someTabTitleChanged = Signal()


class Window(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(Window, self).__init__(*args, **kwargs)

        self.setCentralWidget(TabWidget())
        self.setWindowTitle(self.tr('Lierre'))

        self.centralWidget().currentChanged.connect(self._tabChanged)
        self.centralWidget().someTabTitleChanged.connect(self._tabChanged)

    @Slot()
    def _tabChanged(self):
        self.setWindowTitle(self.centralWidget().currentWidget().windowTitle())

