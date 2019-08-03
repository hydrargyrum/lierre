
import email.policy
import logging
import sys

from PyQt5.QtWidgets import QWidget
from lierre.ui.ui_loader import load_ui_class
from lierre.credentials import get_credential
from pexpect import spawn, EOF

from .base import Plugin


LOGGER = logging.getLogger(__name__)


Ui_Form = load_ui_class('msmtp', 'Form', 'lierre.builtins.senders')


class Widget(Ui_Form, QWidget):
    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin

        self.setupUi(self)
        self.cfgEdit.setText(self.plugin.config.get('config_file', ''))

    def update_config(self):
        self.plugin.config['config_file'] = self.cfgEdit.text()


class MSmtpPlugin(Plugin):
    def send(self, msg):
        conf = self.config.get('config_file', '').strip()

        cmd = ['msmtp', '--read-envelope-from', '--read-recipients']
        if conf:
            cmd += ['-C', conf]

        # - msmtp reads headers on stdin to find identity
        # - then it reads its configuration and might ask password on tty
        #   (use credentials in that case)
        # - then it reads the message body on stdin

        policy = email.policy.default
        raw_b = msg.as_bytes(policy=policy)
        raw = raw_b.decode('ascii')
        headers_s, sep, body_s = raw.partition(policy.linesep * 2)

        pe = spawn(cmd[0], args=cmd[1:], encoding='utf-8')
        pe.logfile_read = sys.stdout

        pe.send(headers_s + sep)

        event = pe.expect([r'password for \S+ at \S+:', EOF])
        if event == 0:
            pe.sendline(get_credential(self.config['credential']))

        pe.send(body_s)
        pe.sendeof()
        pe.expect(EOF)
        pe.close()

    def set_config(self, config):
        self.config = config

    def get_config(self):
        return self.config

    def enable(self):
        pass

    def disable(self):
        pass

    def build_config_form(self):
        return Widget(self)
