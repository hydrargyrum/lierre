
from PyQt5.QtCore import pyqtSlot as Slot
from PyQt5.QtWidgets import QApplication

from . import __version__
from . import plugin_manager
from .config import read_config, write_config
from .error_logs import install as install_log_handler


class Application(QApplication):
    def __init__(self, *args, **kwargs):
        super(Application, self).__init__(*args, **kwargs)
        self.setApplicationDisplayName(self.tr('Lierre'))
        self.setApplicationName('Lierre')
        self.setApplicationVersion(__version__)
        self.setDesktopFileName('lierre.desktop')

        read_config()
        install_log_handler()
        plugin_manager.init()

        self.aboutToQuit.connect(self._on_quit)

    @Slot()
    def _on_quit(self):
        write_config()
