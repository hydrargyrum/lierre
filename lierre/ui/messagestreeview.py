
from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot, QModelIndex
from PyQt5.QtWidgets import QTreeView
from lierre.ui.models import ThreadMessagesModel


class MessagesTreeView(QTreeView):
    def __init__(self, *args, **kwargs):
        super(MessagesTreeView, self).__init__(*args, **kwargs)

        self.setSelectionBehavior(QTreeView.SelectRows)
        self.setSelectionMode(QTreeView.SingleSelection)

        self.activated.connect(self.on_activated)

    @Slot(QModelIndex)
    def on_activated(self, qidx):
        filename = qidx.data(ThreadMessagesModel.MessageFilenameRole)
        self.messageActivated.emit(filename)

    messageActivated = Signal(str)

