
import email
import email.policy
import gc
import html

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFrame
from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
from lierre.ui import plain_message_ui
from lierre.ui import collapsed_message_ui
from lierre.mailutils.parsequote import Parser, Line, Block


def flatten_depth_first(tree_dict):
    def _build(msg):
        for sub in tree_dict.get(msg, ()):
            ret.append(sub)
            _build(sub)

    ret = []
    _build(None)
    return ret


class PlainMessageWidget(QFrame, plain_message_ui.Ui_Frame):
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


class CollapsedMessageWidget(QFrame, collapsed_message_ui.Ui_Frame):
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


class MessagesView(QWidget):
    def __init__(self, *args, **kwargs):
        super(MessagesView, self).__init__(*args, **kwargs)
        self.setLayout(QVBoxLayout())

        self.widgets = {}

    def setThread(self, thread, tree):
        self.thread = thread
        self.thread_tree = tree
        self.message_list = flatten_depth_first(self.thread_tree)

        self.setWindowTitle(self.tr('Thread: %s') % self.thread.get_subject())

        self.buildUi()

    def buildUi(self):
        for msg in self.message_list:
            qmsg = CollapsedMessageWidget(msg)
            qmsg.toggle.connect(self._toggleMessage)
            self.layout().addWidget(qmsg)
            self.widgets[msg.get_message_id()] = qmsg

    @Slot()
    def _toggleMessage(self):
        qmsg = self.sender()
        self._toggleMessageWidget(qmsg)

    def _toggleMessageWidget(self, qmsg):
        id = qmsg.message.get_message_id()
        if isinstance(qmsg, PlainMessageWidget):
            new = CollapsedMessageWidget(qmsg.message)
            # new.toggle.connect(self._selectInTree)
        else:
            new = PlainMessageWidget(qmsg.message)
        new.toggle.connect(self._toggleMessage)
        self.widgets[id] = new

        self.layout().replaceWidget(qmsg, new)
        qmsg.deleteLater()
        return new

    @Slot(str)
    def showMessage(self, id):
        qmsg = self.widgets[id]
        if isinstance(qmsg, CollapsedMessageWidget):
            self._toggleMessageWidget(qmsg)
        # TODO scroll into view

    def __del__(self):
        # WTF: collecting now makes python to free Thread then Threads
        # omitting it will cause python to free Threads then Thread (segfault!)
        gc.collect()

