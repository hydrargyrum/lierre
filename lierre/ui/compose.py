
from email.message import EmailMessage
from email.headerregistry import Address
from email.utils import localtime, getaddresses
import json
import re
from subprocess import check_output

from PyQt5.QtCore import pyqtSlot as Slot, pyqtSignal as Signal
from PyQt5.QtWidgets import QWidget
from lierre.utils.db_ops import open_db, open_db_rw
from lierre.sending import get_identities, send_email
from lierre.change_watcher import WATCHER

from . import compose_ui


class ComposeWidget(QWidget, compose_ui.Ui_Form):
    def __init__(self, *args, **kwargs):
        super(ComposeWidget, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.reply_to = None
        self.built_info = None

        self._updateIdentities()

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

    def _info_from_cli(self, msg_id, reply_all=False):
        reply_flag = 'all' if reply_all else 'sender'
        cmd = [
            'notmuch', 'reply', '--format=json',
            '--reply-to=%s' % reply_flag, 'id:%s' % msg_id,
        ]

        d = json.loads(check_output(cmd).decode('utf-8'))
        d = d['reply-headers']
        return d

    def _info_manually(self, msg_id, reply_all=False):
        d = {}

        with open_db() as db:
            msg = db.find_message(msg_id)

            subject = msg.get_header('subject')
            if not re.match('re:', subject, re.I):
                subject = 'Re: %s' % subject
            d['Subject'] = subject

            d['In-reply-to'] = '<%s>' % msg_id
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

    def setReply(self, msg_id, reply_all):
        assert msg_id
        self.reply_to = msg_id

        info = self._info_from_cli(msg_id, reply_all)
        self.built_info = info

        self.subjectEdit.setText(info['Subject'])
        self.toEdit.setText(info.get('To', ''))

    @Slot()
    def on_sendButton_clicked(self):
        # prevent double-click, etc.
        self.sendButton.setEnabled(False)
        try:
            self._send()
        finally:
            self.sendButton.setEnabled(True)

    def _send(self):
        identity_key = self.fromCombo.currentData()
        if not identity_key:
            return

        identities = get_identities()
        idt = identities[identity_key]

        msg = EmailMessage()
        msg['Date'] = localtime()
        msg['Subject'] = self.subjectEdit.text()
        msg['To'] = [Address(name, addr_spec=addr) for name, addr in getaddresses([self.toEdit.text()])]

        if self.built_info:
            for header in ('In-reply-to', 'References'):
                if header in self.built_info:
                    msg[header] = self.built_info[header]

        msg.set_content(self.messageEdit.toPlainText())

        send_email(idt, msg)

        self.sent.emit()

        with open_db_rw() as db:
            if self.reply_to:
                replied_to = db.find_message(self.reply_to)
                replied_to.add_tag('replied', True)
                WATCHER.mailTagAdded('replied', self.reply_to)

    sent = Signal()
