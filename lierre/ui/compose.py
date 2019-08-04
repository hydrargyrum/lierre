# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

import email
from email.message import EmailMessage
from email.headerregistry import Address
from email.utils import localtime, getaddresses, make_msgid
import json
from mailbox import Maildir, MaildirMessage
from pathlib import Path
import re
from subprocess import check_output

from PyQt5.QtCore import pyqtSlot as Slot, pyqtSignal as Signal
from PyQt5.QtWidgets import QWidget
from lierre.mailutils.parsequote import Parser, indent_recursive, to_text
from lierre.utils.db_ops import open_db, open_db_rw, get_db_path
from lierre.sending import get_identities, send_email
from lierre.change_watcher import WATCHER

from .ui_loader import load_ui_class


Ui_Form = load_ui_class('compose', 'Ui_Form')


class ComposeWidget(QWidget, Ui_Form):
    def __init__(self, *args, **kwargs):
        super(ComposeWidget, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self._updateIdentities()

        self.ccToggle.setChecked(False)

        self.addAction(self.actionSaveDraft)
        self.actionSaveDraft.triggered.connect(self._saveDraft)
        self.draft_id = None

        self.msg = EmailMessage()

    def _updateIdentities(self):
        identities = get_identities()

        self.fromCombo.clear()
        self.fromCombo.setEnabled(bool(identities))

        if identities:
            for key, idt in identities.items():
                txt = '%s <%s>' % (idt['name'], idt['email'])
                self.fromCombo.addItem(txt, key)
        else:
            self.fromCombo.addItem(self.tr('Please configure identities'))

    def _get_reply_from_cli(self, reply_to, reply_all=False):
        reply_flag = 'all' if reply_all else 'sender'
        cmd = [
            'notmuch', 'reply', '--format=json',
            '--reply-to=%s' % reply_flag, 'id:%s' % reply_to,
        ]

        d = json.loads(check_output(cmd).decode('utf-8'))
        d = d['reply-headers']
        return d

    def _get_reply_manually(self, reply_to, reply_all=False):
        d = {}

        with open_db() as db:
            msg = db.find_message(reply_to)

            subject = msg.get_header('subject')
            if not re.match('re:', subject, re.I):
                subject = 'Re: %s' % subject
            d['Subject'] = subject

            d['In-reply-to'] = '<%s>' % reply_to
            # TODO add 'References'

            # TODO add 'From'
            d['To'] = msg.get_header('reply-to') or msg.get_header('from')
            if reply_all:
                ccs = [
                    msg.get_header('from'), msg.get_header('to'),
                    msg.get_header('cc'),
                ]
                # TODO remove oneself
                d['Cc'] = ', '.join(filter(None, ccs))

            return d

    def setReply(self, reply_to, reply_all):
        assert reply_to

        info = self._get_reply_from_cli(reply_to, reply_all)
        for header in ('In-reply-to', 'References'):
            if header in info:
                self.msg[header] = info[header]

        self.subjectEdit.setText(info['Subject'])
        self.toEdit.setText(info.get('To', ''))
        self.ccEdit.setText(info.get('Cc', ''))
        self.ccToggle.setChecked(bool(self.ccEdit.text()))

        with open_db() as db:
            msg = db.find_message(reply_to)
            with open(msg.get_filename(), 'rb') as fp:
                pymessage = email.message_from_binary_file(fp, policy=email.policy.default)

        body = pymessage.get_body(('plain',))
        if body is not None:
            body = body.get_content()
            parser = Parser()
            parsed = parser.parse(body)
            for block in parsed:
                indent_recursive(block)
            self.messageEdit.setPlainText(to_text(parsed))

    def setFromDraft(self, draft_id):
        with open_db() as db:
            msg = db.find_message(draft_id)
            with open(msg.get_filename(), 'rb') as fp:
                pymessage = email.message_from_binary_file(fp, policy=email.policy.default)

        self.msg = pymessage
        self.draft_id = draft_id

        self.subjectEdit.setText(self.msg['Subject'])
        self.toEdit.setText(self.msg.get('To', ''))
        self.ccEdit.setText(self.msg.get('Cc', ''))
        self.ccToggle.setChecked(bool(self.ccEdit.text()))

        body = pymessage.get_body(('plain',))
        if body is not None:
            body = body.get_content()
            self.messageEdit.setPlainText(body)

    @Slot()
    def on_sendButton_clicked(self):
        # prevent double-click, etc.
        self.sendButton.setEnabled(False)
        try:
            self._send()
        finally:
            self.sendButton.setEnabled(True)

    def _setHeader(self, k, v):
        del self.msg[k]
        self.msg[k] = v

    def _prepareMessage(self):
        identity_key = self.fromCombo.currentData()
        if not identity_key:
            return

        identities = get_identities()
        idt = identities[identity_key]

        self._setHeader('Date', localtime())
        self._setHeader('Subject', self.subjectEdit.text())
        self._setHeader('To', [Address(name, addr_spec=addr) for name, addr in getaddresses([self.toEdit.text()])])
        self._setHeader('Cc', [Address(name, addr_spec=addr) for name, addr in getaddresses([self.ccEdit.text()])])
        self._setHeader('Bcc', [Address(name, addr_spec=addr) for name, addr in getaddresses([self.bccEdit.text()])])

        from_addr = Address(idt['name'], addr_spec=idt['email'])
        self._setHeader('From', from_addr)
        self._setHeader('Message-ID', make_msgid(domain=from_addr.domain))

        self.msg.set_content(self.messageEdit.toPlainText())

        return idt

    def _send(self):
        idt = self._prepareMessage()
        if not idt:
            return

        send_email(idt, self.msg)

        self.sent.emit()

        with open_db_rw() as db:
            if self.msg.get('In-reply-to', ''):
                replied_to = db.find_message(self.msg['In-reply-to'])
                if replied_to:
                    replied_to.add_tag('replied', True)
                    WATCHER.tagMailAdded.emit('replied', self.reply_to)

    @Slot()
    def _saveDraft(self):
        idt = self._prepareMessage()
        if not idt:
            return

        box = Maildir(get_db_path())
        boxmsg = MaildirMessage(self.msg)
        boxmsg.add_flag('D')

        uniq = box.add(boxmsg)
        msg_path = Path(get_db_path()).joinpath(box._lookup(uniq))
        with open_db_rw() as db:
            msg, _ = db.add_message(str(msg_path))
            msg.add_tag('draft', True)

            old_draft, self.draft_id = self.draft_id, msg.get_message_id()
            if old_draft:
                old_msg = db.find_message(old_draft)
                old_file = old_msg.get_filename()
                Path(old_file).unlink()
                db.remove_message(old_file)

    sent = Signal()
