
from PyQt5.QtWidgets import QApplication

from .config import read_config


class Application(QApplication):
    def __init__(self, *args, **kwargs):
        super(Application, self).__init__(*args, **kwargs)
        read_config()

