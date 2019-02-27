
from functools import reduce

from PyQt5.QtCore import pyqtSlot as Slot, pyqtSignal as Signal
from PyQt5.QtWidgets import QWidget, QToolBar, QMenu
from lierre.utils.db_ops import open_db, open_db_rw, UNTOUCHABLE_TAGS, get_thread_by_id
from lierre.change_watcher import WATCHER

from .ui_loader import load_ui_class
from .models import ThreadMessagesModel
from .tag_editor import TagEditor


Ui_Form = load_ui_class('thread_widget', 'Ui_Form')


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


class ThreadWidget(QWidget, Ui_Form):
    def __init__(self, thread_id, *args, **kwargs):
        super(ThreadWidget, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.splitter.setStretchFactor(1, 1)

        self.setupToolbar()

        mdl = ThreadMessagesModel(thread_id)
        self.messagesTree.setModel(mdl)
        self.messagesTree.expandAll()

        self.messagesView.setThread(thread_id)
        self.messagesTree.messageActivated.connect(self.messagesView.showMessage)
        self.messagesTree.messagesSelectionChanged.connect(self.messagesView.selectMessageChanged)
        self.messagesTree.messagesSelectionChanged.connect(self.messagesView.scrollToSelected)
        self.messagesTree.messagesSelectionChanged.connect(self.updateToolbarState)

        self.messagesView.expanded.connect(self.messagesTree.selectMessage)

        with open_db() as db:
            thread = get_thread_by_id(db, thread_id)
            self.setWindowTitle(self.tr('Thread: %s') % thread.get_subject())

    def setupToolbar(self):
        tb = QToolBar()
        self.verticalLayout.insertWidget(0, tb)

        tb.addAction(self.actionReplyToAll)
        self.actionReplyToAll.triggered.connect(self._compose)
        tb.addAction(self.actionReplyToSender)
        self.actionReplyToSender.triggered.connect(self._compose)
        tb.addAction(self.actionForward)
        self.actionForward.triggered.connect(self._compose)

        tb.addSeparator()
        tb.addAction(self.actionFlagMessage)
        self.actionFlagMessage.triggered.connect(self._flagMessages)

        tb.addAction(self.actionTagMessage)
        self.actionTagMessage.triggered.connect(self.openTagEditor)

        tagMenu = QMenu('Tags')
        tagMenu.aboutToShow.connect(self._prepareTagMenu)
        self.actionTagMessage.setMenu(tagMenu)
        tb.addSeparator()

        tb.addAction(self.actionSelectAll)
        self.actionSelectAll.triggered.connect(self.messagesTree.selectAll)
        tb.addAction(self.actionDeleteMessage)
        self.actionDeleteMessage.triggered.connect(self._deleteSelectedMessages)

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
        add = action.isChecked()
        tag = action.data()

        msg_ids = self._getSelectedMessages()
        with open_db_rw() as db:
            for msg_id in msg_ids:
                msg = db.find_message(msg_id)
                if add:
                    msg.add_tag(tag)
                    WATCHER.tagMailAdded.emit(tag, msg_id)
                else:
                    msg.remove_tag(tag)
                    WATCHER.tagMailRemoved.emit(tag, msg_id)

    def _toggleTag(self, tag):
        msg_ids = self._getSelectedMessages()
        with open_db_rw() as db:
            for msg_id in msg_ids:
                msg = db.find_message(msg_id)
                if tag in msg.get_tags():
                    msg.remove_tag(tag)
                    WATCHER.tagMailRemoved.emit(tag, msg_id)
                else:
                    msg.add_tag(tag)
                    WATCHER.tagMailAdded.emit(tag, msg_id)

    @Slot()
    def _flagMessages(self):
        self._toggleTag('flagged')

    @Slot()
    def _deleteSelectedMessages(self):
        msg_ids = self._getSelectedMessages()
        with open_db_rw() as db:
            for msg_id in msg_ids:
                msg = db.find_message(msg_id)
                msg.add_tag('deleted')
                WATCHER.tagMailAdded.emit('deleted', msg_id)

    @Slot()
    def updateToolbarState(self):
        nb_selected = len([
            qidx for qidx in self.messagesTree.selectedIndexes()
            if qidx.column() == 0
        ])

        self.actionFlagMessage.setEnabled(bool(nb_selected))
        self.actionTagMessage.setEnabled(bool(nb_selected))
        self.actionReplyToAll.setEnabled(nb_selected == 1)
        self.actionReplyToSender.setEnabled(nb_selected == 1)
        self.actionForward.setEnabled(nb_selected == 1)
        self.actionDeleteMessage.setEnabled(bool(nb_selected))

    @Slot()
    def _compose(self):
        msg_id, = self._getSelectedMessages()
        if self.sender() == self.actionReplyToAll:
            self.triggeredReply.emit(msg_id, True)
        elif self.sender() == self.actionReplyToSender:
            self.triggeredReply.emit(msg_id, False)
        elif self.sender() == self.actionForward:
            self.triggeredForward.emit(msg_id)

    triggeredReply = Signal(str, bool)
    triggeredForward = Signal(str)

    @Slot()
    def openTagEditor(self):
        selected = self._getSelectedMessages()
        assert selected

        w = TagEditor(parent=self)
        with open_db() as db:
            msgs = [db.find_message(msg_id) for msg_id in selected]
            common_tags = reduce(set.__and__, (set(msg.get_tags()) for msg in msgs), set(msgs[0].get_tags()))
            union_tags = reduce(set.__or__, (set(msg.get_tags()) for msg in msgs), set())
            union_tags -= common_tags

            w.setCheckedTags(common_tags, union_tags)

        if not w.exec_():
            return

        with open_db_rw() as db:
            msgs = [db.find_message(sel) for sel in selected]
            checked, partially = w.checkedTags()

            db.begin_atomic()
            for msg in msgs:
                msg_tags = set(msg.get_tags())

                for tag in (msg_tags - checked):  # unchecked tags
                    if tag in partially:
                        continue
                    msg.remove_tag(tag)
                    WATCHER.tagMailRemoved.emit(tag, msg.get_message_id())

                for tag in (checked - msg_tags):  # newly checked tags
                    msg.add_tag(tag)
                    WATCHER.tagMailAdded.emit(tag, msg.get_message_id())

            db.end_atomic()

            for msg in msgs:
                msg.tags_to_maildir_flags()
