
from PyQt5.QtCore import pyqtSlot as Slot
from PyQt5.QtWidgets import QApplication

from . import __version__
from . import plugin_manager
from .config import read_config, write_config


class Application(QApplication):
    def __init__(self, *args, **kwargs):
        super(Application, self).__init__(*args, **kwargs)
        self.setApplicationDisplayName(self.tr('Lierre'))
        self.setApplicationName('Lierre')
        self.setApplicationVersion(__version__)

        read_config()
        plugin_manager.init()

        self.aboutToQuit.connect(self._on_quit)

    @Slot()
    def _on_quit(self):
        write_config()
