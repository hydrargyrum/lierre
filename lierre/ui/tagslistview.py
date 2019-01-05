
from PyQt5.QtWidgets import QTreeView, QStyledItemDelegate
from PyQt5.QtCore import (
    pyqtSlot as Slot, pyqtSignal as Signal, QModelIndex,
)


class TagDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, qidx):
        super(TagDelegate, self).initStyleOption(option, qidx)
        if qidx.sibling(qidx.row(), 1).data():
            option.font.setBold(True)


class TagsListView(QTreeView):
    def __init__(self, *args, **kwargs):
        super(TagsListView, self).__init__(*args, **kwargs)
        self.setItemDelegate(TagDelegate())

        self.activated.connect(self._tagActivated)
        self.setAcceptDrops(True)

    @Slot(QModelIndex)
    def _tagActivated(self, qidx):
        qidx = qidx.siblingAtColumn(0)
        self.tagActivated.emit(qidx.data())

    tagActivated = Signal(str)
