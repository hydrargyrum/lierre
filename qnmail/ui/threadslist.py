
from PyQt5.QtWidgets import QTreeView
from PyQt5.QtGui import QStandardItemModel, QStandardItem


def threads_to_model(threads):
    mdl = QStandardItemModel()
    mdl.setHorizontalHeaderLabels(['ID', 'Subject'])

    for thr in threads:
        row = []
        row.append(QStandardItem(thr.get_thread_id()))
        row.append(QStandardItem(thr.get_subject()))

        for item in row:
            item.setEditable(False)

        mdl.appendRow(row)

    return mdl


class ThreadsView(QTreeView):
    pass

