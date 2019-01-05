
from PyQt5.QtWidgets import QTreeView, QStyledItemDelegate
from PyQt5.QtCore import (
    pyqtSlot as Slot, pyqtSignal as Signal,
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
        self.activated.connect(self._activatedTag)
        self.setAcceptDrops(True)

    @Slot()
    def _activatedTag(self, qidx):
        qidx = qidx.sibling(qidx.row(), 0)
        self.activatedTag.emit(qidx.data())

    activatedTag = Signal()
