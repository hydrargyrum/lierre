
from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QTabWidget,
)
from PyQt5.QtCore import pyqtSlot as Slot

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
        self._addTab(w)
        w.threadActivated.connect(self.addThread)

    @Slot(str)
    def addThread(self, tid):
        app = QApplication.instance()
        thr = get_thread_by_id(app.db, tid)
        w = ThreadWidget(thr)
        idx = self._addTab(w)
        self.setCurrentIndex(idx)

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


class Window(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(Window, self).__init__(*args, **kwargs)

        self.setCentralWidget(TabWidget())
        self.setWindowTitle(self.tr('QNMail'))

