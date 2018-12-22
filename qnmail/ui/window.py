
from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QLineEdit, QWidget, QApplication,
)

from .threadslist import ThreadsView, threads_to_model
from .threads_window_ui import Ui_Form


class MainWidget(QWidget, Ui_Form):
    def __init__(self, *args, **kwargs):
        super(MainWidget, self).__init__(*args, **kwargs)
        self.setupUi(self)


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

