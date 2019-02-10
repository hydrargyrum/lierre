
import logging
import subprocess
import threading

from PyQt5.QtCore import QObject, pyqtSignal as Signal
from lierre.change_watcher import WATCHER

from . import plugin_manager


LOGGER = logging.getLogger(__name__)


class Fetcher(QObject):
    def start(self):
        self.thread = threading.Thread(target=self._run)
        self.thread.start()

    def _run(self):
        LOGGER.info('running fetchers')
        for plugin in plugin_manager.PLUGINS['fetchers'].iter_enabled_plugins().values():
            LOGGER.info('running fetcher %r', plugin)
            try:
                plugin.run()
            except Exception as exc:
                LOGGER.exception('error while running fetcher %r: %s', plugin, exc)

        LOGGER.info('running notmuch-new')
        try:
            output = subprocess.check_output(['notmuch', 'new'], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as exc:
            LOGGER.error('notmuch-new returned status-code %s', exc.returncode)
            LOGGER.error('output is %s', exc.output.decode('utf-8', errors='replace'))
        except Exception as exc:
            LOGGER.exception('error while running notmuch-new: %s', exc)
        else:
            LOGGER.info('output is %s', output.decode('utf-8', errors='replace'))

        LOGGER.info('running filters')
        for plugin in plugin_manager.PLUGINS['filters'].iter_enabled_plugins().values():
            LOGGER.info('running filter %r', plugin)
            try:
                plugin.run()
            except Exception as exc:
                LOGGER.exception('error while running filter %r: %s', plugin, exc)

        self.finished.emit()
        WATCHER.globalRefresh.emit()

    # TODO progress bar info

    finished = Signal()

