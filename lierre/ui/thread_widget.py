
from functools import reduce

from PyQt5.QtCore import pyqtSlot as Slot
from PyQt5.QtWidgets import QWidget, QToolBar, QMenu
from lierre.utils.db_ops import open_db, open_db_rw, UNTOUCHABLE_TAGS

from . import thread_widget_ui
from .models import ThreadMessagesModel


def build_thread_tree(thread):
    # TODO attach weak tree to thread?

    def _build(msg):
        it = msg.get_replies()
        for sub in it:
            ret.setdefault(msg, []).append(sub)
            _build(sub)

    ret = {}

    for msg in thread.get_toplevel_messages():
        ret.setdefault(None, []).append(msg)
        _build(msg)

    return ret


def flatten_depth_first(tree_dict):
    def _build(msg):
        for sub in tree_dict.get(msg, ()):
            ret.append(sub)
            _build(sub)

    ret = []
    _build(None)
    return ret


class ThreadWidget(QWidget, thread_widget_ui.Ui_Form):
    def __init__(self, thread, *args, **kwargs):
        super(ThreadWidget, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.setupToolbar()

        tree = build_thread_tree(thread)

        mdl = ThreadMessagesModel(tree)
        self.messagesTree.setModel(mdl)
        self.messagesTree.expandAll()

        self.messagesView.setThread(thread, tree)
        self.messagesTree.messageActivated.connect(self.messagesView.showMessage)
        self.messagesTree.messagesSelectionChanged.connect(self.messagesView.selectMessageChanged)
        self.messagesTree.messagesSelectionChanged.connect(self.updateToolbarState)

        self.messagesView.expanded.connect(self.messagesTree.selectMessage)

        self.setWindowTitle(self.tr('Thread: %s') % thread.get_subject())

    def setupToolbar(self):
        tb = QToolBar()
        self.verticalLayout.insertWidget(0, tb)

        tb.addAction(self.actionTagMessage)

        tagMenu = QMenu('Tags')
        tagMenu.aboutToShow.connect(self._prepareTagMenu)
        self.actionTagMessage.setMenu(tagMenu)
        tb.addSeparator()

        tb.addAction(self.actionSelectAll)
        self.actionSelectAll.triggered.connect(self.messagesTree.selectAll)

        self.updateToolbarState()

    def _getSelectedMessages(self):
        return [
            qidx.data(ThreadMessagesModel.MessageIdRole)
            for qidx in self.messagesTree.selectedIndexes()
            if qidx.column() == 0
        ]

    @Slot()
    def _prepareTagMenu(self):
        # TODO much improvement, colored tags, filter tags, sub-tags
        menu = self.sender()
        menu.clear()

        msg_ids = self._getSelectedMessages()

        with open_db() as db:
            msgs = [db.find_message(msg_id) for msg_id in msg_ids]
            msg_tags = reduce(set.__or__, (set(msg.get_tags()) for msg in msgs), set())

            db_tags = set(db.get_all_tags())
            db_tags -= UNTOUCHABLE_TAGS

            for tag in sorted(db_tags):
                action = menu.addAction(tag)
                action.setCheckable(True)
                action.setData(tag)
                if tag in msg_tags:
                    action.setChecked(True)
                action.triggered.connect(self._setMessagesTag)

    @Slot()
    def _setMessagesTag(self):
        action = self.sender()
        add = action.checked()
        tag = action.data()

        msg_ids = self._getSelectedMessages()
        with open_db_rw() as db:
            for msg_id in msg_ids:
                msg = db.find_message(msg_id)
                if add:
                    msg.add_tag(tag)
                else:
                    msg.remove_tag(tag)

    @Slot()
    def updateToolbarState(self):
        nb_selected = len([
            qidx for qidx in self.messagesTree.selectedIndexes()
            if qidx.column() == 0
        ])

        self.actionTagMessage.setEnabled(bool(nb_selected))

