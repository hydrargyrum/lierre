
from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QLineEdit, QWidget, QApplication,
)

from .threadslist import ThreadsView, threads_to_model


class Window(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(Window, self).__init__(*args, **kwargs)

        self.setCentralWidget(QWidget())

        layout = QVBoxLayout()
        self.centralWidget().setLayout(layout)

        self.searchLine = QLineEdit()
        self.searchLine.setText('tag:inbox')
        self.searchLine.returnPressed.connect(self.doSearch)
        layout.addWidget(self.searchLine)

        self.threads = ThreadsView()
        layout.addWidget(self.threads)

    def doSearch(self):
        app = QApplication.instance()
        q = app.db.create_query(self.searchLine.text())
        threads = q.search_threads()
        threads._query = q
        self.threads.setModel(threads_to_model(threads))

