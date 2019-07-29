
from logging import getLogger

from PyQt5.QtWidgets import (
    QWidget, QFormLayout, QLabel, QLineEdit,
)
from PyQt5.QtCore import QProcess

from .base import Plugin, Job


LOGGER = getLogger(__name__)


class CommandForm(QWidget):
    def __init__(self, plugin):
        super(CommandForm, self).__init__()
        self.plugin = plugin

        layout = QFormLayout()
        self.setLayout(layout)
        self.editor = QLineEdit(self.plugin.config.get('command', ''))
        layout.addRow(QLabel(self.tr('Command')), self.editor)

    def update_config(self):
        self.plugin.config['command'] = self.editor.text()


class SavingProcess(QProcess):
    def __init__(self, *args, **kwargs):
        super(SavingProcess, self).__init__(*args, **kwargs)
        self.proc.setProcessChannelMode(QProcess.MergedChannels)
        self.proc.setInputChannelMode(QProcess.ForwardedInputChannel)


class ControllingProcess(QProcess):
    def __init__(self, *args, **kwargs):
        super(ControllingProcess, self).__init__(*args, **kwargs)
        self.proc.setInputChannelMode(QProcess.ManagedInputChannel)


class CommandJob(Job):
    def __init__(self, cmd):
        super(CommandJob, self).__init__()
        self.cmd = cmd
        if isinstance(self.cmd, str):
            self.cmd = ['sh', '-c', self.cmd]

    def start(self):
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.ForwardedChannels)
        self.proc.setInputChannelMode(QProcess.ForwardedInputChannel)
        self.proc.finished.connect(self.finished)

        LOGGER.debug('will invoke %s', self.cmd)
        self.proc.start(self.cmd[0], self.cmd[1:])


class CommandPlugin(Plugin):
    def __init__(self):
        super(CommandPlugin, self).__init__()
        self.thread = None

    def get_config(self):
        return self.config

    def set_config(self, config):
        self.config = config

    def build_config_form(self):
        return CommandForm(self)

    def create_job(self, **kwargs):
        return CommandJob(self.config['command'])

