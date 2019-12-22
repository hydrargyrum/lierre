# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

import email
import email.policy
import html
from pathlib import Path
import re

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QLabel, QMenu, QSizePolicy, QFileDialog,
)
from PyQt5.QtGui import QIcon, QPainter, QFontMetrics
from PyQt5.QtCore import (
    pyqtSignal as Signal, pyqtSlot as Slot, Qt, QSize, QTimer, QStandardPaths,
)
from lierre.mailutils.parsequote import Parser, Line, Block
from lierre.utils.db_ops import (
    EXCERPT_BUILDER, open_db, open_db_rw, get_thread_by_id,
)
from lierre.utils.date import short_datetime
from lierre.change_watcher import WATCHER

from .models import build_thread_tree, tag_to_colors
from .ui_loader import load_ui_class


PlainMessageUi_Frame = load_ui_class('plain_message', 'Ui_Frame')
CollapsedMessageUi_Frame = load_ui_class('collapsed_message', 'Ui_Frame')


def flatten_depth_first(tree_dict):
    def _build(msg):
        for sub in tree_dict.get(msg, ()):
            ret.append(sub)
            _build(sub)

    ret = []
    _build(None)
    return ret


class PlainMessageWidget(QFrame, PlainMessageUi_Frame):
    UNREAD_DELAY = 5000

    def __init__(self, message, *args, **kwargs):
        super(PlainMessageWidget, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.headerWidget.installEventFilter(self)

        tool_menu = QMenu()
        tool_menu.addAction(self.actionChooseText)
        tool_menu.addAction(self.actionChooseHTML)
        tool_menu.addAction(self.actionChooseHTMLSource)
        tool_menu.addAction(self.actionChooseSource)
        self.toolButton.setMenu(tool_menu)

        self.message_id = message.get_message_id()
        self.message_filename = message.get_filename()
        self.fromLabel.setText(message.get_header('From'))
        self.toLabel.setText(message.get_header('To'))
        self.dateLabel.setText(short_datetime(message.get_date()))

        self.resumeDraftButton.setVisible('draft' in set(message.get_tags()))
        self.resumeDraftButton.clicked.connect(self.resumeDraft)

        idx = self.layout().indexOf(self.messageEdit)
        self.tags_widget = TagsLabelWidget(list(message.get_tags()), parent=self)
        self.layout().insertWidget(idx, self.tags_widget)

        with open(self.message_filename, 'rb') as fp:
            self.pymessage = email.message_from_binary_file(fp, policy=email.policy.default)

        self.display_format = 'plain'
        self._populate_body()
        self._populate_attachments()

        self.unread_timer = None
        if 'unread' in set(message.get_tags()):
            self.unread_timer = QTimer()
            self.unread_timer.setSingleShot(True)
            self.unread_timer.timeout.connect(self._mark_read)

        self.actionChooseText.setData('plain')
        self.actionChooseHTML.setData('html')
        self.actionChooseHTMLSource.setData('html_source')
        self.actionChooseSource.setData('source')

        self.actionChooseText.triggered.connect(self._chooseFormat)
        self.actionChooseSource.triggered.connect(self._chooseFormat)
        self.actionChooseHTML.triggered.connect(self._chooseFormat)
        self.actionChooseHTMLSource.triggered.connect(self._chooseFormat)

        WATCHER.tagMailAdded.connect(self._addedTag, Qt.QueuedConnection)
        WATCHER.tagMailRemoved.connect(self._removedTag, Qt.QueuedConnection)

    def _populate_body(self):
        if self.display_format == 'plain':
            self._populate_body_plain()
        elif self.display_format == 'html':
            self._populate_body_html()
        elif self.display_format == 'source':
            self._populate_body_source()
        elif self.display_format == 'html_source':
            self._populate_body_html_source()
        else:
            assert False

    def _populate_body_source(self):
        with open(self.message_filename, 'rb') as fp:
            body = fp.read()

        try:
            body = body.decode('utf-8')
        except UnicodeError:
            body = body.decode('iso8859-1')

        self.messageEdit.setMessage(self.pymessage)
        self.messageEdit.setPlainText(body)

    def _populate_body_html_source(self):
        body = self.pymessage.get_body(('html',))
        if body is None:
            return

        body = body.get_content()
        self.messageEdit.setMessage(self.pymessage)
        self.messageEdit.setPlainText(body)

    def _populate_body_html(self):
        body = self.pymessage.get_body(('html',))
        if body is None:
            return

        body = body.get_content()
        self.messageEdit.setMessage(self.pymessage)
        self.messageEdit.setHtml(body)

    def _line_to_html(self, line):
        line_html = html.escape(line)

        def to_nbsp(mtc):
            return '&nbsp;' * len(mtc.group())

        line_html = re.sub(r'\s{2,}', to_nbsp, line_html)

        def to_link(mtc):
            html_url = mtc.group()
            url = html.unescape(html_url)
            return '<a href="{0}">{0}</a>'.format(url)

        line_html = LINK_RE.sub(to_link, line_html)

        # TODO handle multiline (can't be done in this function)
        return line_html

    def _populate_body_plain(self):
        body = self.pymessage.get_body(('plain',))
        if body is None:
            return

        body = body.get_content()

        parser = Parser()
        parsed = parser.parse(body)

        full_html = []

        def _populate_rec_webengine(item):
            if isinstance(item, Line):
                full_html.append('  ' * item.level)
                full_html.append(self._line_to_html(item.text))
                full_html.append('<br/>')
            else:
                assert isinstance(item, Block)

                if item.level:
                    full_html.append('<blockquote>\n')
                    full_html.append('<details open="open">\n')
                    full_html.append('<summary>Quote</summary>\n')

                for sub in item.content:
                    _populate_rec_webengine(sub)

                if item.level:
                    full_html.append('</details>\n')
                    full_html.append('</blockquote>\n')

        def _populate_rec_qtextbrowser(item):
            if isinstance(item, Line):
                full_html.append('  ' * item.level)
                full_html.append(self._line_to_html(item.text))
                full_html.append('<br/>')
            else:
                assert isinstance(item, Block)

                if item.level:
                    full_html.append('</p>\n')
                    full_html.append('<blockquote>\n')
                    full_html.append('<p>\n')

                for sub in item.content:
                    _populate_rec_qtextbrowser(sub)

                if item.level:
                    full_html.append('</p>\n')
                    full_html.append('</blockquote>\n')
                    full_html.append('<p>\n')

        full_html.append('<p>\n')
        for item in parsed:
            _populate_rec_qtextbrowser(item)
        full_html.append('</p>\n')

        self.messageEdit.setHtml(''.join(full_html))

    def _populate_attachments(self):
        has_attach = False

        self.attachmentsButton.setMenu(QMenu(self.attachmentsButton))
        for n, attachment in enumerate(self.pymessage.iter_attachments()):
            has_attach = True
            action = self.attachmentsButton.menu().addAction(attachment.get_filename() or 'untitled.attachment')
            action.triggered.connect(self._saveAttachment)
            action.setData(n)

        self.attachmentsButton.setVisible(has_attach)

    @Slot()
    def _saveAttachment(self):
        action = self.sender()
        number = action.data()
        attachment = list(self.pymessage.iter_attachments())[number]

        dest = Path(QStandardPaths.writableLocation(QStandardPaths.DownloadLocation))
        if not dest.is_dir():
            dest = Path.home()

        dest, _ = QFileDialog.getSaveFileName(
            self, self.tr('Save attachment'),
            str(dest.joinpath(attachment.get_filename())),
        )
        if not dest:
            return

        with open(dest, 'wb') as fp:
            fp.write(attachment.get_payload())

    def eventFilter(self, obj, ev):
        if ev.type() == ev.MouseButtonPress:
            self.toggle.emit()
            return True

        return False

    toggle = Signal()
    resumeDraft = Signal()

    @Slot()
    def _chooseFormat(self):
        self.display_format = self.sender().data()
        self._populate_body()

    def paintEvent(self, ev):
        super(PlainMessageWidget, self).paintEvent(ev)

        if self.unread_timer and not self.unread_timer.isActive():
            self.unread_timer.start(self.UNREAD_DELAY)

    @Slot()
    def _mark_read(self):
        self.unread_timer = None
        with open_db_rw() as db:
            msg = db.find_message(self.message_id)
            msg.remove_tag('unread', True)
            self.message_filename = msg.get_filename()
            WATCHER.tagMailRemoved.emit('unread', self.message_id)

    @Slot(str, str)
    def _addedTag(self, tag, msg_id):
        if self.message_id == msg_id:
            self.tags_widget.tags.append(tag)
            self.tags_widget.update()

    @Slot(str, str)
    def _removedTag(self, tag, msg_id):
        if self.message_id == msg_id:
            try:
                self.tags_widget.tags.remove(tag)
            except ValueError:  # tag wasn't present
                pass
            else:
                self.tags_widget.update()


class CollapsedMessageWidget(QFrame, CollapsedMessageUi_Frame):
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
            if 'unread' in set(msg.get_tags()) or msg is message_list[-1]:
                qmsg = PlainMessageWidget(msg, parent=self)
                qmsg.resumeDraft.connect(self._resumeDraft)
            else:
                qmsg = CollapsedMessageWidget(msg, parent=self)

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
                new = CollapsedMessageWidget(message, parent=self)
                # new.toggle.connect(self._selectInTree)
            else:
                new = PlainMessageWidget(message, parent=self)
                new.resumeDraft.connect(self._resumeDraft)
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

    @Slot(list)
    def scrollToSelected(self, added):
        if not added:
            return

        qmsg = self.widgets[added[-1]]
        self.parent().parent().ensureWidgetVisible(qmsg)

    @Slot(list, list)
    def selectMessageChanged(self, added, removed):
        def changeWidth(l, width):
            for message_id in l:
                qmsg = self.widgets[message_id]
                qmsg.setLineWidth(width)

        changeWidth(removed, 1)
        changeWidth(added, 2)

    @Slot()
    def _resumeDraft(self):
        qmsg = self.sender()
        self.resumeDraft.emit(qmsg.message_id)

    expanded = Signal(str)
    resumeDraft = Signal(str)


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


LINK_RE = re.compile(
    r'''https?://
    [][(),'!*$_a-z@.A-Z:0-9/~;?+&=%#-]+  # legal chars in a URL
    [a-zA-Z0-9/+=#]+  # but we prefer URLs end with those rather than one of the above chars
    ''', re.VERBOSE,
)


def test_link_parse():
    assert LINK_RE.findall('''
        http://foo.bar
        http://foo.bar/
        http://foo.bar/42
        http://foo.bar/42.
        http://foo.bar/42.html
        <http://foo.bar/42.html>
        [markdown](http://foo.bar/42.html)
        http://foo.bar/42%25.html
        http://qu:ux@foo.bar/~grault/42.html;param?k=k&v=v+v#yes=
    ''') == '''
        http://foo.bar
        http://foo.bar/
        http://foo.bar/42
        http://foo.bar/42
        http://foo.bar/42.html
        http://foo.bar/42.html
        http://foo.bar/42.html
        http://foo.bar/42%25.html
        http://qu:ux@foo.bar/~grault/42.html;param?k=k&v=v+v#yes=
    '''.split()
