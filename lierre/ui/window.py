
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import pyqtSlot as Slot
from lierre.fetching import Fetcher
from lierre.config import CONFIG

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
        tab_title = self.tabWidget.currentWidget().windowTitle()
        self.setWindowTitle(self.tr('%s - Lierre') % tab_title)

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

    def show(self):
        if CONFIG.get('ui', 'window', 'maximized', default=False):
            self.showMaximized()
        else:
            super(Window, self).show()

    def closeEvent(self, ev):
        CONFIG.setdefault('ui', 'window', {})['maximized'] = self.isMaximized()
        super(Window, self).closeEvent(ev)

