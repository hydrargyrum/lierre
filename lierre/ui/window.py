
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import pyqtSlot as Slot
from lierre.fetching import Fetcher

from .window_ui import Ui_MainWindow
from .options_conf import OptionsConf


class Window(Ui_MainWindow, QMainWindow):
    def __init__(self, *args, **kwargs):
        super(Window, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.setWindowTitle(self.tr('Lierre'))

        self.tabWidget.currentChanged.connect(self._tabChanged)
        self.tabWidget.someTabTitleChanged.connect(self._tabChanged)

        self.actionRefresh.triggered.connect(self._startRefresh)
        self.fetcher = None

        self.actionCfgMail.triggered.connect(self.openOptions)

    @Slot()
    def _tabChanged(self):
        self.setWindowTitle(self.tabWidget.currentWidget().windowTitle())

    @Slot()
    def _startRefresh(self):
        self.fetcher = Fetcher()
        self.fetcher.finished.connect(self._finishedRefresh)
        self.fetcher.start()

    @Slot()
    def _finishedRefresh(self):
        self.fetcher = None

    @Slot()
    def openOptions(self):
        OptionsConf(parent=self).show()

