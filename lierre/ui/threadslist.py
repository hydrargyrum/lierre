
from PyQt5.QtWidgets import QTreeView
from PyQt5.QtGui import QStandardItemModel, QStandardItem

from ..utils.date import short_datetime

def threads_to_model(threads):
    mdl = QStandardItemModel()
    mdl.setHorizontalHeaderLabels(['ID', 'Subject', 'Last update'])

    for thr in threads:
        row = []
        row.append(QStandardItem(thr.get_thread_id()))
        row.append(QStandardItem(thr.get_subject()))
        row.append(QStandardItem(short_datetime(thr.get_newest_date())))

        for item in row:
            item.setEditable(False)

        mdl.appendRow(row)

    return mdl


class ThreadsView(QTreeView):
    pass

