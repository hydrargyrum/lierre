
import imaplib2
import logging
import subprocess

from PyQt5.QtCore import (
    QThread, pyqtSignal as Signal, pyqtSlot as Slot,
)
from lierre.builtins.fetchers.base import Plugin
from lierre.change_watcher import WATCHER
from lierre.fetching import Fetcher


LOGGER = logging.getLogger(__name__)


class IdlerThread(QThread):
    def __init__(self, config, password):
        super(IdlerThread, self).__init__()

        self.host = config['host']
        self.login = config['login']
        self.password = password
        self.folder = config.get('folder', 'INBOX')

        self.to_stop = False

    def run(self):
        self.connection = imaplib2.IMAP4_SSL(self.host)
        self.connection.login(self.login, self.password)
        # TODO handle login failure

        while not self.to_stop:
            self.connection.select(self.folder)
            LOGGER.info('watching server %r user %r folder %r', self.host, self.login, self.folder)
            self.connection.idle()
            self.activity.emit()
        # TODO handle failure
        # TODO look for specific message telling there are new messages
        # TODO start fetcher (only the right server?)
        # TODO handle disconnection

    def stop(self):
        self.to_stop = True
        self.connection.noop()

    activity = Signal()


class IdlePlugin(Plugin):
    def __init__(self):
        super(IdlePlugin, self).__init__()
        self.idler = None
        self.fetcher = None
        self.config = {}

    def set_config(self, config):
        self.config = config

    def get_config(self):
        return self.config

    def _is_config_valid(self):
        return (
            self.config.get('host') and self.config.get('login') and
            self.config.get('passcmd') and self.config.get('fetcher_key')
        )

    def enable(self):
        if not self._is_config_valid():
            return

        # TODO handle configuration
        # TODO watch multiple folders
        # TODO watch multiple hosts
        password = subprocess.check_output(self.config['passcmd'], shell=True).decode('utf-8').strip()
        self.idler = IdlerThread(self.config, password)
        self.idler.activity.connect(self._start_fetcher)
        self.idler.start()

    def disable(self):
        if not self.idler:
            return

        self.idler.stop()
        self.idler.join()

    @Slot()
    def _start_fetcher(self):
        idler = self.sender()

        self.fetcher = Fetcher()
        self.fetcher.start_only(self.config['fetcher_key'], folder=idler.folder)
