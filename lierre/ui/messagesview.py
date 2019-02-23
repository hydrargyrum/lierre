
import email
import email.policy
import html

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QLabel, QMenu, QSizePolicy,
)
from PyQt5.QtGui import QIcon, QPainter, QFontMetrics
from PyQt5.QtCore import (
    pyqtSignal as Signal, pyqtSlot as Slot, Qt, QSize,
)
from lierre.ui import plain_message_ui
from lierre.ui import collapsed_message_ui
from lierre.mailutils.parsequote import Parser, Line, Block
from lierre.utils.db_ops import EXCERPT_BUILDER, open_db, get_thread_by_id
from lierre.utils.date import short_datetime

from .models import build_thread_tree, tag_to_colors


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

        tool_menu = QMenu()
        tool_menu.addAction(self.actionChooseText)
        tool_menu.addAction(self.actionChooseHTML)
        self.toolButton.setMenu(tool_menu)

        self.message_id = message.get_message_id()
        self.message_filename = message.get_filename()
        self.fromLabel.setText(message.get_header('From'))
        self.toLabel.setText(message.get_header('To'))
        self.dateLabel.setText(short_datetime(message.get_date()))

        idx = self.layout().indexOf(self.messageEdit)
        tags_widget = TagsLabelWidget(list(message.get_tags()), parent=self)
        self.layout().insertWidget(idx, tags_widget)

        with open(self.message_filename, 'rb') as fp:
            self.pymessage = email.message_from_binary_file(fp, policy=email.policy.default)

        self.display_format = 'plain'
        self._populate_body()
        self._populate_attachments()

    def _populate_body(self):
        if self.display_format == 'plain':
            self._populate_body_plain()
        elif self.display_format == 'html':
            self._populate_body_html()
        else:
            assert False

    def _populate_body_html(self):
        body = self.pymessage.get_body(('html',))
        if body is None:
            return

        body = body.get_content()
        self.messageEdit.setHtml(body)

    def _populate_body_plain(self):
        body = self.pymessage.get_body(('plain',))
        if body is None:
            return

        body = body.get_content()

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

    def _populate_attachments(self):
        has_attach = False

        self.attachmentsButton.setMenu(QMenu(self.attachmentsButton))
        for n, attachment in enumerate(self.pymessage.iter_attachments()):
            has_attach = True
            action = self.attachmentsButton.menu().addAction(attachment.get_filename())
            action.setData(n)

        self.attachmentsButton.setVisible(has_attach)

    def eventFilter(self, obj, ev):
        if ev.type() == ev.MouseButtonPress:
            self.toggle.emit()
            return True

        return False

    toggle = Signal()

    @Slot()
    def on_actionChooseText_triggered(self):
        self.display_format = 'plain'
        self._populate_body()

    def on_actionChooseHTML_triggered(self):
        self.display_format = 'html'
        self._populate_body()


class CollapsedMessageWidget(QFrame, collapsed_message_ui.Ui_Frame):
    def __init__(self, message, *args, **kwargs):
        super(CollapsedMessageWidget, self).__init__(*args, **kwargs)
        self.setupUi(self)

        EXCERPT_BUILDER.builtExcerpt.connect(self._builtExcerpt)

        self.message_id = message.get_message_id()
        self.fromLabel.setText(message.get_header('From'))
        self.toLabel.setText(message.get_header('To'))
        self.dateLabel.setText(short_datetime(message.get_date()))
        self.excerptLabel.setText(EXCERPT_BUILDER.getOrBuild(message.get_message_id()) or '')

        tags = set(message.get_tags())
        if 'unread' in tags:
            self.unreadLabel.setPixmap(QIcon.fromTheme('mail-unread').pixmap(16, 16))
        if 'attachment' in tags:
            self.attachmentLabel.setPixmap(QIcon.fromTheme('mail-attachment').pixmap(16, 16))

    def mousePressEvent(self, ev):
        self.toggle.emit()

    toggle = Signal()

    @Slot(str, str)
    def _builtExcerpt(self, message_id, text):
        if message_id == self.message_id:
            self.excerptLabel.setText(text)


class MessagesView(QWidget):
    def __init__(self, *args, **kwargs):
        super(MessagesView, self).__init__(*args, **kwargs)
        self.setLayout(QVBoxLayout())

        self.widgets = {}

    def setThread(self, thread_id):
        with open_db() as db:
            thread = get_thread_by_id(db, thread_id)
            tree = build_thread_tree(thread)
            message_list = flatten_depth_first(tree)

            self.setWindowTitle(self.tr('Thread: %s') % thread.get_subject())

            subjectLabel = QLabel()
            subjectLabel.setTextFormat(Qt.PlainText)
            subjectLabel.setText(self.tr('Subject: %s') % thread.get_subject())
            subjectLabel.setLineWidth(1)
            subjectLabel.setFrameShape(QFrame.Box)
            self.layout().addWidget(subjectLabel)

            self.buildUi(message_list)

    def buildUi(self, message_list):
        for msg in message_list:
            qmsg = CollapsedMessageWidget(msg)
            qmsg.toggle.connect(self._toggleMessage)
            self.layout().addWidget(qmsg)
            self.widgets[msg.get_message_id()] = qmsg
        self.layout().addStretch()

    @Slot()
    def _toggleMessage(self):
        qmsg = self.sender()
        self._toggleMessageWidget(qmsg)

    def _toggleMessageWidget(self, qmsg):
        with open_db() as db:
            message = db.find_message(qmsg.message_id)

            collapsed = isinstance(qmsg, PlainMessageWidget)

            if collapsed:
                new = CollapsedMessageWidget(message)
                # new.toggle.connect(self._selectInTree)
            else:
                new = PlainMessageWidget(message)
            new.toggle.connect(self._toggleMessage)
            new.setLineWidth(qmsg.lineWidth())
            self.widgets[message.get_message_id()] = new

            self.layout().replaceWidget(qmsg, new)
            qmsg.deleteLater()

            if not collapsed:
                self.expanded.emit(message.get_message_id())

            return new

    @Slot(str)
    def showMessage(self, message_id):
        qmsg = self.widgets[message_id]
        if isinstance(qmsg, CollapsedMessageWidget):
            self._toggleMessageWidget(qmsg)
        # TODO scroll into view

    @Slot(list, list)
    def selectMessageChanged(self, added, removed):
        def changeWidth(l, width):
            for message_id in l:
                qmsg = self.widgets[message_id]
                qmsg.setLineWidth(width)

        changeWidth(removed, 1)
        changeWidth(added, 2)

    expanded = Signal(str)


class TagsLabelWidget(QFrame):
    xpadding = 2
    xmargin = 5
    ymargin = 0

    def __init__(self, tags, *args, **kwargs):
        super(TagsLabelWidget, self).__init__(*args, **kwargs)
        self.tags = tags

        self.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum, QSizePolicy.Label))

    def _positions(self, tags):
        fm = QFontMetrics(self.font())

        for tag in tags:
            sz = fm.size(Qt.TextSingleLine, tag)
            yield sz, tag

    def paintEvent(self, ev):
        super(TagsLabelWidget, self).paintEvent(ev)

        painter = QPainter(self)

        painter.save()
        try:
            painter.setBackground(self.palette().brush(self.backgroundRole()))
            painter.eraseRect(ev.rect())

            painter.setClipRect(ev.rect())

            fm = QFontMetrics(self.font())  # TODO use style

            x = self.xmargin
            for sz, tag in self._positions(self.tags):
                fg, bg = tag_to_colors(tag)
                painter.setPen(fg.color())

                painter.fillRect(x, self.ymargin, sz.width() + 2 * self.xpadding, fm.height(), bg.color())
                painter.drawText(x + self.xpadding, self.ymargin + fm.ascent(), tag)
                x += sz.width() + self.xmargin + 2 * self.xpadding

        finally:
            painter.restore()

    def sizeHint(self):
        fm = QFontMetrics(self.font())

        x = self.xmargin
        y = 0
        for sz, tag in self._positions(self.tags):
            x += sz.width() + self.xmargin + 2 * self.xpadding
            y = self.ymargin * 2 + fm.height()

        return QSize(x, y)
