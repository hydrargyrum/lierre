
import email.policy
import logging

from PyQt5.QtCore import QByteArray
from PyQt5.QtWidgets import QWidget
from lierre.builtins.fetchers.base import Job
from lierre.builtins.fetchers.command import ControllingProcess
from lierre.ui.ui_loader import load_ui_class

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


class MSmtpJob(Job):
    def __init__(self, plugin, msg):
        super().__init__()
        self.plugin = plugin
        self.msg = msg

    def run(self):
        LOGGER.info('sending mail %r with msmtp', self.msg['Message-ID'])

        self.proc = ControllingProcess(self)

        conf = self.plugin.config.get('config_file', '').strip()

        cmd = ['msmtp', '--read-envelope-from', '--read-recipients']
        if conf:
            cmd += ['-C', conf]

        self.proc.start(cmd[0], cmd[1:])
        self.proc.finished.connect(self.finished)

        raw = self.msg.as_bytes(policy=email.policy.default)
        self.proc.write(QByteArray(raw))


class MSmtpPlugin(Plugin):
    def send(self, msg):
        return MSmtpJob(self, msg)

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
