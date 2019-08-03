
from logging import getLogger
import sys

from PyQt5.QtWidgets import (
    QWidget, QFormLayout, QLabel, QLineEdit,
)
from PyQt5.QtCore import QThread, pyqtSlot as Slot
from pexpect import spawn, EOF
from lierre.credentials import get_credential

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


class Thread(QThread):
    def __init__(self, callable):
        super().__init__()
        self.callable = callable

    def run(self):
        self.result = -1
        self.result = self.callable()


class ThreadRunnerJob(Job):
    def __init__(self, callable):
        super().__init__()
        self.thread = Thread(callable)
        self.thread.finished.connect(self._finishedThread)

    @Slot()
    def _finishedThread(self):
        self.finished.emit(self.thread.result)

    def start(self):
        self.thread.start()


class MbsyncRunnable:
    def __init__(self, cmd, config):
        self.cmd = cmd
        self.config = config

    def __call__(self):
        pe = spawn(self.cmd[0], args=self.cmd[1:], encoding='utf-8')
        pe.logfile_read = sys.stdout

        event = pe.expect([r'Password \([^)]+\):', EOF])
        if event == 0:
            pe.sendline(get_credential(self.config.get('credential')))
            pe.expect(EOF)

        pe.wait()
        pe.close()
        if pe.signalstatus:
            return pe.signalstatus + 128
        return pe.exitstatus


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

        return ThreadRunnerJob(MbsyncRunnable(cmd, self.config))
