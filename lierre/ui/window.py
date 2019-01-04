
from hashlib import sha1

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QApplication, QTabWidget,
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QBrush, QColor
from PyQt5.QtCore import (
    pyqtSignal as Signal, pyqtSlot as Slot,
)

from .threadslist import threads_to_model
from .threads_window_ui import Ui_Form
from .threadview import ThreadWidget


def all_tags_to_model(db):
    mdl = QStandardItemModel()
    mdl.setHorizontalHeaderLabels(['Tag'])

    tags = db.get_all_tags()
    tags = sorted(tags, key=str.lower)
    for tag in tags:
        item = QStandardItem(tag)

        r, g, b = sha1(tag.encode('utf-8')).digest()[:3]
        item.setBackground(QBrush(QColor(r, g, b)))
        if r + g + b < 128 * 3:
            item.setForeground(QBrush(QColor('white')))
        else:
            item.setForeground(QBrush(QColor('black')))

        mdl.appendRow(item)

    return mdl


def get_thread_by_id(db, id):
    q = db.create_query('thread:%s' % id)
    it = q.search_threads()
    thr = list(it)[0]
    return thr


class ThreadsWidget(QWidget, Ui_Form):
    def __init__(self, *args, **kwargs):
        super(ThreadsWidget, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.threadsView.activated.connect(self._openThread)

        app = QApplication.instance()
        self.tagsView.setModel(all_tags_to_model(app.db))

        self.searchLine.returnPressed.connect(self.doSearch)
        self.searchButton.clicked.connect(self.doSearch)

    def _openThread(self, qidx):
        tid = qidx.siblingAtColumn(0).data()
        self.threadActivated.emit(tid)

    threadActivated = Signal(str)

    def doSearch(self):
        app = QApplication.instance()

        query_text = self.searchLine.text()
        q = app.db.create_query(query_text)
        threads = q.search_threads()
        self.threadsView.setModel(threads_to_model(threads))


class TabWidget(QTabWidget):
    def __init__(self, *args, **kwargs):
        super(TabWidget, self).__init__(*args, **kwargs)
        self.setMovable(True)
        self.setTabsClosable(True)

        self.tabCloseRequested.connect(self._closeTabRequested)

        self.addThreads()

    def addThreads(self):
        w = ThreadsWidget()
        self.addTab(w, 'Default')
        w.threadActivated.connect(self.addThread)

    @Slot(str)
    def addThread(self, tid):
        app = QApplication.instance()
        thr = get_thread_by_id(app.db, tid)
        w = ThreadWidget(thr)
        self.addTab(w, 'Thread')

    @Slot(int)
    def _closeTabRequested(self, idx):
        if self.count() > 1:
            self.removeTab(idx)


class Window(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(Window, self).__init__(*args, **kwargs)

        self.setCentralWidget(TabWidget())
        self.setWindowTitle(self.tr('QNMail'))

