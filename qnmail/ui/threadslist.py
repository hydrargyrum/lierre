
from PyQt5.QtWidgets import QTreeView
from PyQt5.QtGui import QStandardItemModel, QStandardItem
import notmuch


def threads_to_model(threads):
    mdl = QStandardItemModel()
    mdl.setHorizontalHeaderLabels(['ID', 'Subject'])

    for thr in threads:
        thr._parent = threads
        row = []
        row.append(QStandardItem(thr.get_thread_id()))
        row.append(QStandardItem(thr.get_subject()))

        mdl.appendRow(row)

    return mdl


class ThreadsView(QTreeView):
    pass

