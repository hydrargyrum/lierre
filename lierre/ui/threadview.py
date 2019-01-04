
from PyQt5.QtWidgets import QWidget

from . import thread_window_ui
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


class ThreadWidget(QWidget, thread_window_ui.Ui_Form):
    def __init__(self, thread, *args, **kwargs):
        super(ThreadWidget, self).__init__(*args, **kwargs)
        self.setupUi(self)

        tree = build_thread_tree(thread)

        mdl = ThreadMessagesModel(tree)
        self.messagesTree.setModel(mdl)
        self.messagesTree.expandAll()

        self.messagesView.setThread(thread, tree)
        self.messagesTree.messageActivated.connect(self.messagesView.showMessage)

