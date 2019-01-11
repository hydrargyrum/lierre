
import email
import email.policy
import html

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFrame, QApplication
from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
from lierre.ui import plain_message_ui
from lierre.ui import collapsed_message_ui
from lierre.mailutils.parsequote import Parser, Line, Block
from lierre.utils.db_ops import EXCERPT_BUILDER


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

        self.message_filename = message.get_filename()
        self.fromLabel.setText(message.get_header('From'))
        self.toLabel.setText(message.get_header('To'))
        self.dateLabel.setText(message.get_header('Date'))

        self._populate_body()

    def _populate_body(self):
        with open(self.message_filename, 'rb') as fp:
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

        EXCERPT_BUILDER.builtExcerpt.connect(self._builtExcerpt)

        self.message_filename = message.get_filename()
        self.fromLabel.setText(message.get_header('From'))
        self.toLabel.setText(message.get_header('To'))
        self.dateLabel.setText(message.get_header('Date'))
        self.excerptLabel.setText(EXCERPT_BUILDER.getOrBuild(message.get_filename()) or '')

    def mousePressEvent(self, ev):
        self.toggle.emit()

    toggle = Signal()

    @Slot(str, str)
    def _builtExcerpt(self, filename, text):
        if filename == self.message_filename:
            self.excerptLabel.setText(text)


class MessagesView(QWidget):
    def __init__(self, *args, **kwargs):
        super(MessagesView, self).__init__(*args, **kwargs)
        self.setLayout(QVBoxLayout())

        self.widgets = {}

    def setThread(self, thread, tree):
        message_list = flatten_depth_first(tree)

        self.setWindowTitle(self.tr('Thread: %s') % thread.get_subject())

        self.buildUi(message_list)

    def buildUi(self, message_list):
        for msg in message_list:
            qmsg = CollapsedMessageWidget(msg)
            qmsg.toggle.connect(self._toggleMessage)
            self.layout().addWidget(qmsg)
            self.widgets[msg.get_filename()] = qmsg
        self.layout().addStretch()

    @Slot()
    def _toggleMessage(self):
        qmsg = self.sender()
        self._toggleMessageWidget(qmsg)

    def _toggleMessageWidget(self, qmsg):
        app = QApplication.instance()
        message = app.db.find_message_by_filename(qmsg.message_filename)

        if isinstance(qmsg, PlainMessageWidget):
            new = CollapsedMessageWidget(message)
            # new.toggle.connect(self._selectInTree)
        else:
            new = PlainMessageWidget(message)
        new.toggle.connect(self._toggleMessage)
        new.setLineWidth(qmsg.lineWidth())
        self.widgets[message.get_filename()] = new

        self.layout().replaceWidget(qmsg, new)
        qmsg.deleteLater()
        return new

    @Slot(str)
    def showMessage(self, filename):
        qmsg = self.widgets[filename]
        if isinstance(qmsg, CollapsedMessageWidget):
            self._toggleMessageWidget(qmsg)
        # TODO scroll into view

    @Slot(list, list)
    def selectMessage(self, added, removed):
        def changeWidth(l, width):
            for filename in l:
                qmsg = self.widgets[filename]
                qmsg.setLineWidth(width)

        changeWidth(removed, 1)
        changeWidth(added, 2)

