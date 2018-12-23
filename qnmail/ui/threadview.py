
import email
import email.policy

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QScrollArea
from PyQt5.QtCore import pyqtSignal as Signal

from . import plain_message_ui
from . import collapsed_message_ui


def build_thread_tree(thread):
    def _build(msg):
        it = msg.get_replies()
        it._parent = msg
        for sub in it:
            sub._parent = it
            ret.setdefault(sub, []).append(sub)
            _build(sub)

    ret = {}

    it = thread.get_toplevel_messages()
    it._parent = thread
    for msg in it:
        msg._parent = it
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


class PlainMessageWidget(QWidget, plain_message_ui.Ui_Form):
    def __init__(self, message, *args, **kwargs):
        super(PlainMessageWidget, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.headerWidget.installEventFilter(self)

        self.message = message
        self.fromLabel.setText(message.get_header('From'))
        self.toLabel.setText(message.get_header('To'))
        self.dateLabel.setText(message.get_header('Date'))

        with open(message.get_filename(), 'rb') as fp:
            self.pymessage = email.message_from_binary_file(fp, policy=email.policy.default)

        self.messageEdit.setPlainText(self.pymessage.get_body('plain').get_content())

    def eventFilter(self, obj, ev):
        if ev.type() == ev.MouseButtonPress:
            self.toggle.emit()
            return True

        return False

    toggle = Signal()


class CollapsedMessageWidget(QWidget, collapsed_message_ui.Ui_Form):
    def __init__(self, message, *args, **kwargs):
        super(CollapsedMessageWidget, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.message = message
        self.fromLabel.setText(message.get_header('From'))
        self.toLabel.setText(message.get_header('To'))
        self.dateLabel.setText(message.get_header('Date'))

    def mousePressEvent(self, ev):
        self.toggle.emit()

    toggle = Signal()


class ThreadWidget(QScrollArea):
    def __init__(self, thread, *args, **kwargs):
        super(ThreadWidget, self).__init__(*args, **kwargs)
        self.setLayout(QVBoxLayout())

        self.thread = thread
        self.thread_tree = build_thread_tree(thread)
        self.message_list = flatten_depth_first(self.thread_tree)

        self.setWindowTitle(self.tr('Thread: %s') % self.thread.get_subject())

        self.buildUi()

    def buildUi(self):
        for msg in self.message_list:
            qmsg = CollapsedMessageWidget(msg)
            qmsg.toggle.connect(self._toggleMessage)
            self.layout().addWidget(qmsg)

    def _toggleMessage(self):
        qmsg = self.sender()
        if isinstance(qmsg, PlainMessageWidget):
            new = CollapsedMessageWidget(qmsg.message)
        else:
            new = PlainMessageWidget(qmsg.message)
        new.toggle.connect(self._toggleMessage)

        self.layout().replaceWidget(qmsg, new)
        qmsg.setParent(None)

