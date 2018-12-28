
import datetime

from PyQt5.QtWidgets import QTreeView
from PyQt5.QtGui import QStandardItemModel, QStandardItem


def threads_to_model(threads):
    mdl = QStandardItemModel()
    mdl.setHorizontalHeaderLabels(['ID', 'Subject', 'Last update'])

    for thr in threads:
        row = []
        row.append(QStandardItem(thr.get_thread_id()))
        row.append(QStandardItem(thr.get_subject()))

        last_update = thr.get_newest_date()
        last_update = datetime.datetime.fromtimestamp(last_update)
        row.append(QStandardItem(last_update.strftime('%c')))

        for item in row:
            item.setEditable(False)

        mdl.appendRow(row)

    return mdl


class ThreadsView(QTreeView):
    pass

