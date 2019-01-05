
from hashlib import sha1

from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QBrush, QColor
from PyQt5.QtCore import pyqtSignal as Signal

from .models import ThreadListModel
from .threads_widget_ui import Ui_Form


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


class ThreadsWidget(QWidget, Ui_Form):
    def __init__(self, *args, **kwargs):
        super(ThreadsWidget, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.threadsView.activated.connect(self._openThread)

        app = QApplication.instance()
        self.tagsView.setModel(all_tags_to_model(app.db))

        self.threadsView.setModel(ThreadListModel())

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
        self.threadsView.model().setQuery(q)

