
from PyQt5.QtCore import pyqtSlot as Slot
from PyQt5.QtWidgets import QApplication

from . import plugin_manager
from .config import read_config, write_config


class Application(QApplication):
    def __init__(self, *args, **kwargs):
        super(Application, self).__init__(*args, **kwargs)
        read_config()
        plugin_manager.init()

        self.aboutToQuit.connect(self._on_quit)

    @Slot()
    def _on_quit(self):
        write_config()
