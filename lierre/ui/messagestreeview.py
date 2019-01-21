
from PyQt5.QtCore import (
    pyqtSignal as Signal, pyqtSlot as Slot, QModelIndex, QItemSelection,
)
from PyQt5.QtWidgets import QTreeView
from lierre.ui.models import ThreadMessagesModel


class MessagesTreeView(QTreeView):
    def __init__(self, *args, **kwargs):
        super(MessagesTreeView, self).__init__(*args, **kwargs)

        self.setSelectionBehavior(QTreeView.SelectRows)
        self.setSelectionMode(QTreeView.ExtendedSelection)

        self.activated.connect(self.on_activated)

    def setModel(self, mdl):
        super(MessagesTreeView, self).setModel(mdl)
        self.selectionModel().selectionChanged.connect(self.on_selection)

    @Slot(QModelIndex)
    def on_activated(self, qidx):
        msg_id = qidx.data(ThreadMessagesModel.MessageIdRole)
        self.messageActivated.emit(msg_id)

    @Slot(QItemSelection, QItemSelection)
    def on_selection(self, added, removed):
        def names(l):
            return [qidx.data(ThreadMessagesModel.MessageIdRole) for qidx in l]

        self.messagesSelected.emit(names(added.indexes()), names(removed.indexes()))

    messageActivated = Signal(str)
    messagesSelected = Signal(list, list)

