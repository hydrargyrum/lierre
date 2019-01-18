
from PyQt5.QtWidgets import QApplication


class Application(QApplication):
    def __init__(self, *args, **kwargs):
        super(Application, self).__init__(*args, **kwargs)

