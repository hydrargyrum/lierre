
from PyQt5.QtWidgets import QApplication

from . import plugin_manager
from .config import read_config


class Application(QApplication):
    def __init__(self, *args, **kwargs):
        super(Application, self).__init__(*args, **kwargs)
        read_config()
        plugin_manager.init()

