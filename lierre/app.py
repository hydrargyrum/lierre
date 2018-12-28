
from PyQt5.QtWidgets import QApplication
import notmuch


class Application(QApplication):
    def __init__(self, *args, **kwargs):
        super(Application, self).__init__(*args, **kwargs)
        self.db = notmuch.Database()

