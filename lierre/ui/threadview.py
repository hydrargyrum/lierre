
import email
import email.policy
import gc
import html

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QScrollArea, QTreeView, QSplitter,
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import pyqtSignal as Signal

from . import plain_message_ui
from . import collapsed_message_ui
from ..mailutils.parsequote import Parser, Line, Block
from ..utils.date import short_datetime
from ..utils.addresses import get_sender


def build_thread_tree(thread):
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


def build_thread_tree_model(tree):
    mdl = QStandardItemModel()
    mdl.setHorizontalHeaderLabels(['From', 'Date'])

    def _build(parent, qparent):
        for msg in tree.get(parent, ()):
            qitems = [
                QStandardItem(get_sender(msg.get_header('From'))),
                QStandardItem(short_datetime(msg.get_date())),
            ]

            for qitem in qitems:
                qitem.setEditable(False)

            qparent.appendRow(qitems)
            _build(msg, qitems[0])

    _build(None, mdl.invisibleRootItem())

    return mdl


class PlainMessageWidget(QWidget, plain_message_ui.Ui_Form):
    def __init__(self, message, *args, **kwargs):
        super(PlainMessageWidget, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.headerWidget.installEventFilter(self)

        self.message = message
        self.fromLabel.setText(message.get_header('From'))
        self.toLabel.setText(message.get_header('To'))
        self.dateLabel.setText(message.get_header('Date'))

        self._populate_body()

    def _populate_body(self):
        with open(self.message.get_filename(), 'rb') as fp:
            self.pymessage = email.message_from_binary_file(fp, policy=email.policy.default)
        body = self.pymessage.get_body('plain').get_content()

        parser = Parser()
        parsed = parser.parse(body)

        full_html = []

        def _populate_rec(item):
            if isinstance(item, Line):
                full_html.append('  ' * item.level)
                full_html.append(html.escape(item.text))
                full_html.append('<br/>')
            else:
                assert isinstance(item, Block)

                if item.level:
                    full_html.append('  ' * item.level)
                    full_html.append('<blockquote>\n')

                for sub in item.content:
                    _populate_rec(sub)

                if item.level:
                    full_html.append('  ' * item.level)
                    full_html.append('</blockquote>\n')

        for item in parsed:
            _populate_rec(item)

        self.messageEdit.setHtml(''.join(full_html))

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


class ThreadMessagesBase(QWidget):
    def __init__(self, thread, *args, **kwargs):
        super(ThreadMessagesBase, self).__init__(*args, **kwargs)
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
        qmsg.deleteLater()

    def __del__(self):
        # WTF: collecting now makes python to free Thread then Threads
        # omitting it will cause python to free Threads then Thread (segfault!)
        gc.collect()


class ThreadMessagesWidget(QScrollArea):
    def __init__(self, thread, *args, **kwargs):
        super(ThreadMessagesWidget, self).__init__(*args, **kwargs)
        self.setWidgetResizable(True)
        self.setWidget(ThreadMessagesBase(thread))


class ThreadWidget(QSplitter):
    def __init__(self, thread, *args, **kwargs):
        super(ThreadWidget, self).__init__(*args, **kwargs)

        qtree = QTreeView()
        qmessages = ThreadMessagesWidget(thread)

        tree = qmessages.widget().thread_tree
        tree_mdl = build_thread_tree_model(tree)
        qtree.setModel(tree_mdl)

        self.addWidget(qtree)
        self.addWidget(qmessages)

