
from hashlib import sha1

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QApplication,
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QBrush, QColor

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
    it._query = q
    thr = list(it)[0]
    thr._parent = it
    return thr


class MainWidget(QWidget, Ui_Form):
    def __init__(self, *args, **kwargs):
        super(MainWidget, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.threadsView.activated.connect(self._openThread)

    def _openThread(self, qidx):
        app = QApplication.instance()

        tid = qidx.siblingAtColumn(0).data()
        thr = get_thread_by_id(app.db, tid)

        self.t = ThreadWidget(thr)
        self.t.show()


class Window(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(Window, self).__init__(*args, **kwargs)

        self.setCentralWidget(MainWidget())

        self.centralWidget().searchLine.returnPressed.connect(self.doSearch)
        self.centralWidget().searchButton.clicked.connect(self.doSearch)

        self.setWindowTitle(self.tr('QNMail'))

        app = QApplication.instance()
        self.centralWidget().tagsView.setModel(all_tags_to_model(app.db))

    def doSearch(self):
        app = QApplication.instance()

        query_text = self.centralWidget().searchLine.text()
        q = app.db.create_query(query_text)
        threads = q.search_threads()
        threads._query = q
        self.centralWidget().threadsView.setModel(threads_to_model(threads))

