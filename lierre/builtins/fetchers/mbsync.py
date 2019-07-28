
from logging import getLogger

from PyQt5.QtWidgets import (
    QWidget, QFormLayout, QLabel, QLineEdit,
)
from PyQt5.QtCore import QProcess

from .base import Plugin
from .command import CommandJob


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


class MbsyncPlugin(Plugin):
    def __init__(self):
        super(MbsyncPlugin, self).__init__()
        self.thread = None

    def get_config(self):
        return self.config

    def set_config(self, config):
        self.config = config

    def build_config_form(self):
        return CommandForm(self)

    def create_job(self, **kwargs):
        cmd = ['mbsync']

        cfg_file = self.config.get('config_file')
        if cfg_file:
            cmd += ['-c', cfg_file]

        channel = self.config.get('channel')
        folder = kwargs.get('folder')
        if channel:
            if folder:
                cmd += [f'{channel}:{folder}']
            else:
                cmd += [channel]
        else:
            if folder:
                LOGGER.warning('specific folder-sync was requested, but no channel is configured, performing global sync')
            cmd += ['-a']

        return CommandJob(cmd)
