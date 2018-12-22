
from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QLineEdit, QWidget, QApplication,
)

from .threadslist import ThreadsView, threads_to_model
from .threads_window_ui import Ui_Form
from .threadview import ThreadWidget


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

        mdl = self.threadsView.model()
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

    def doSearch(self):
        app = QApplication.instance()

        query_text = self.centralWidget().searchLine.text()
        q = app.db.create_query(query_text)
        threads = q.search_threads()
        threads._query = q
        self.centralWidget().threadsView.setModel(threads_to_model(threads))

