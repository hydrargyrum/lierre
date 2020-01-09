# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

from logging import getLogger
import os
import re
from shutil import which
import sys

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import QThread, pyqtSlot as Slot
from pexpect import spawn, EOF
from lierre.credentials import get_credential, list_credentials
from lierre.ui.ui_loader import load_ui_class
from lierre.utils.pexpect import env_c_lang, expect_get_obj, close_expect

from .base import Plugin, Job


LOGGER = getLogger(__name__)


Ui_Form = load_ui_class('mbsync', 'Form', 'lierre.builtins.fetchers')


def list_channels(path):
    if not path:
        path = os.path.expanduser('~/.mbsyncrc')

    chan_re = re.compile(r'Channel (\S+)')

    try:
        with open(path, 'r') as fp:
            for line in fp:
                line = line.rstrip()
                m = chan_re.fullmatch(line)
                if m:
                    yield m[1]
    except IOError:
        pass


class Widget(Ui_Form, QWidget):
    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin

        self.setupUi(self)

        self.cfgEdit.textChanged.connect(self._update_channels)
        self.cfgEdit.setText(self.plugin.config.get('config_file', ''))

        channel = self.plugin.config.get('channel')
        if channel:
            self.channelBox.setCurrentText(channel)
        else:
            self.channelBox.setCurrentIndex(0)

        self.credentialBox.addItem('<do not use credential>')
        for cred in list_credentials():
            self.credentialBox.addItem(cred)
        credential = self.plugin.config.get('credential')
        if credential:
            self.credentialBox.setCurrentText(credential)
        else:
            self.credentialBox.setCurrentIndex(0)

    @Slot()
    def _update_channels(self):
        self.channelBox.clear()
        self.channelBox.addItem(self.tr('<All channels>'))
        for channel in list_channels(self.cfgEdit.text()):
            self.channelBox.addItem(channel)

    def update_config(self):
        self.plugin.config['config_file'] = self.cfgEdit.text()

        if self.channelBox.currentIndex() == 0:
            self.plugin.config['channel'] = ''
        else:
            self.plugin.config['channel'] = self.channelBox.currentText()

        if self.credentialBox.currentIndex() == 0:
            self.plugin.config['credential'] = ''
        else:
            self.plugin.config['credential'] = self.credentialBox.currentText()


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


class CommandError(Exception):
    pass


class MbsyncRunnable:
    PASSWORD_PATTERN = re.compile(r'Password \([^)]+\):')
    ERROR_PATTERN = re.compile(r'IMAP command .* returned an error: (.*)\n')
    PROGRESS_PATTERN = re.compile(
        r'C: \d+/\d+  B: \d+/\d+'
        r'  M: \+\d+/\d+ \*\d+/\d+ #\d+/\d+'
        r'  S: \+\d+/\d+ \*\d+/\d+ #\d+/\d+\r'
    )

    def __init__(self, cmd, config):
        self.cmd = cmd
        self.config = config

    def __call__(self):
        pe = spawn(self.cmd[0], args=self.cmd[1:], encoding='utf-8', env=env_c_lang())
        try:
            pe.logfile_read = sys.stdout

            patt_list = [
                self.PASSWORD_PATTERN, self.PROGRESS_PATTERN,
                self.ERROR_PATTERN, EOF,
            ]

            # mbsync displays periodic progress info
            # but it might display initial progress info before asking password
            event = expect_get_obj(pe, patt_list)
            while event is self.PROGRESS_PATTERN:
                # we prefer TIMEOUT to be reserved for strictly no-activity cases
                # so we expect periodic progress updates even if we don't care
                event = expect_get_obj(pe, patt_list)

            if event is self.PASSWORD_PATTERN:
                pe.sendline(get_credential(self.config.get('credential')))

                event = expect_get_obj(pe, patt_list)
                while event is self.PROGRESS_PATTERN:
                    event = expect_get_obj(pe, patt_list)

            if event is self.PASSWORD_PATTERN:
                LOGGER.error('mbsync unexpectedly asked password again, exiting')
                raise CommandError('unexpected password')

            if event is self.ERROR_PATTERN:
                LOGGER.error('mbsync encountered an error: %s', pe.match[1])
                raise CommandError(pe.match[1])

            pe.close()

            if pe.signalstatus:
                return pe.signalstatus + 128
            return pe.exitstatus
        finally:
            close_expect(pe)


class MbsyncPlugin(Plugin):
    def __init__(self):
        super(MbsyncPlugin, self).__init__()
        self.thread = None

    def is_available(self):
        return bool(which('mbsync'))

    def get_config(self):
        return self.config

    def set_config(self, config):
        self.config = config

    def build_config_form(self):
        return Widget(self)

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
