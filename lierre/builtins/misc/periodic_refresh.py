# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

from logging import getLogger

from PyQt5.QtCore import QTimer, pyqtSlot as Slot, Qt
from PyQt5.QtWidgets import QWidget, QSpinBox, QFormLayout, QLabel
from lierre.change_watcher import WATCHER
from lierre.fetching import Fetcher


LOGGER = getLogger(__name__)

DEFAULT = 60


class RefreshClock(QTimer):
    @Slot()
    def _tick(self):
        LOGGER.info('periodic refresh triggered')
        self.fetcher = Fetcher()
        self.fetcher.start()


class RefreshForm(QWidget):
    def __init__(self, plugin):
        super(RefreshForm, self).__init__()
        self.plugin = plugin

        layout = QFormLayout()
        self.setLayout(layout)
        self.editor = QSpinBox()
        self.editor.setRange(1, 60 * 24)
        self.editor.setValue(self.plugin.config.get('delay_minutes', DEFAULT))

        layout.addRow(QLabel(self.tr('Delay (in minutes)')), self.editor)

    def update_config(self):
        self.plugin.config['delay_minutes'] = self.editor.value()


class PeriodicRefreshPlugin:
    def enable(self):
        delay = self.config.get('delay_minutes', DEFAULT) * 60 * 1000

        self.refresher = RefreshClock()
        self.refresher.setTimerType(Qt.VeryCoarseTimer)
        self.refresher.setInterval(delay)
        self.refresher.start()

        # reset timer if manually triggered
        WATCHER.globalRefresh.connect(self.refresher.start)

    def disable(self):
        WATCHER.globalRefresh.disconnect(self.refresher.start)
        self.refresher.stop()
        self.refresher = None

    def set_config(self, config):
        self.config = config

    def get_config(self):
        return self.config

    def build_config_form(self):
        return RefreshForm(self)
