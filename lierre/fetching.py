
import logging
import subprocess

from PyQt5.QtCore import (
    QObject, pyqtSignal as Signal, pyqtSlot as Slot,
)
from lierre.change_watcher import WATCHER
from lierre.builtins.fetchers.command import CommandJob

from . import plugin_manager


LOGGER = logging.getLogger(__name__)


class Fetcher(QObject):
    def __init__(self):
        super(Fetcher, self).__init__()
        self.queue = []

    def start(self):
        for plugin in plugin_manager.PLUGINS['fetchers'].iter_enabled_plugins().values():
            self.queue.append(plugin.create_job())

        self.queue.append(CommandJob('notmuch new'))

        for plugin in plugin_manager.PLUGINS['filters'].iter_enabled_plugins().values():
            self.queue.append(plugin.create_job())

        self._start_job(self.queue.pop(0))

    def _start_job(self, job):
        if not job.parent():
            job.setParent(self)
        job.finished.connect(self.jobFinished)
        job.finished.connect(job.deleteLater)
        job.start()

    @Slot()
    def jobFinished(self):
        if self.queue:
            job = self.queue.pop(0)
            self._start_job(job)
        else:
            self.finished.emit()
            WATCHER.globalRefresh.emit()

    # TODO progress bar info

    finished = Signal()
