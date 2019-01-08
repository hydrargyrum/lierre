
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import pyqtSlot as Slot

from .window_ui import Ui_MainWindow


class Window(Ui_MainWindow, QMainWindow):
    def __init__(self, *args, **kwargs):
        super(Window, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.setWindowTitle(self.tr('Lierre'))

        self.tabWidget.currentChanged.connect(self._tabChanged)
        self.tabWidget.someTabTitleChanged.connect(self._tabChanged)

    @Slot()
    def _tabChanged(self):
        self.setWindowTitle(self.tabWidget.currentWidget().windowTitle())

