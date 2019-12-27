# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

from PyQt5.QtWidgets import QTreeView, QStyledItemDelegate, QHeaderView
from PyQt5.QtCore import (
    pyqtSlot as Slot, pyqtSignal as Signal, QModelIndex,
)


class TagDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, qidx):
        super(TagDelegate, self).initStyleOption(option, qidx)
        if qidx.sibling(qidx.row(), 1).data(qidx.model().UnreadRole):
            option.font.setBold(True)


class TagsListView(QTreeView):
    def __init__(self, *args, **kwargs):
        super(TagsListView, self).__init__(*args, **kwargs)
        self.setItemDelegate(TagDelegate())

        self.activated.connect(self._tagActivated)
        self.setAcceptDrops(True)

    def setModel(self, mdl):
        super(TagsListView, self).setModel(mdl)
        self.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)

    @Slot(QModelIndex)
    def _tagActivated(self, qidx):
        qidx = qidx.siblingAtColumn(0)
        self.tagActivated.emit(qidx.data())

    tagActivated = Signal(str)
