
import json
import re
from subprocess import check_output
from uuid import uuid4

from PyQt5.QtWidgets import QWidget
from lierre.utils.db_ops import open_db

from . import compose_ui


class ComposeWidget(QWidget, compose_ui.Ui_Form):
    def __init__(self, *args, **kwargs):
        super(ComposeWidget, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.reply_to = None

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

            d['Message-ID'] = '%s@%s' % (uuid4(), 'TODO')  # TODO fill domain

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

        self.subjectEdit.setText(info['Subject'])
        self.toEdit.setText(info['To'])

