
import os.path
import sys

from PyQt5.QtWidgets import QMainWindow, QProgressBar
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSlot as Slot
import xdg.BaseDirectory as xbd
from lierre.fetching import Fetcher
from lierre.config import CONFIG

from .ui_loader import load_ui_class
from .options_conf import OptionsConf


Ui_MainWindow = load_ui_class('window', 'Ui_MainWindow')


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
        self.actionCompose.triggered.connect(self.tabWidget.addCompose)

        self.fetchProgress = QProgressBar()
        self.statusbar.addPermanentWidget(self.fetchProgress)

        self.setWindowIcon(get_icon('lierre'))

    @Slot()
    def _tabChanged(self):
        tab_title = self.tabWidget.currentWidget().windowTitle()
        self.setWindowTitle(self.tr('%s - Lierre') % tab_title)

    @Slot()
    def _startRefresh(self):
        self.fetcher = Fetcher()
        self.fetcher.finished.connect(self._finishedRefresh)

        self.fetchProgress.show()
        self.fetchProgress.setRange(0, 0)
        self.actionRefresh.setEnabled(False)

        self.fetcher.start()

    @Slot()
    def _finishedRefresh(self):
        self.actionRefresh.setEnabled(True)
        self.fetchProgress.hide()
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


def get_icon(name):
    def add_icon_search_path(path):
        current = QIcon.themeSearchPaths()
        if path not in current:
            current.append(path)
            QIcon.setThemeSearchPaths(current)

    # default search path doesn't seem to include XDG_DATA_HOME
    for path in xbd.load_data_paths('icons'):
        add_icon_search_path(path)

    # XDG will hardcode /usr* without ever considering virtualenvs
    # sys.prefix may refer to the virtualenv, so let's look there too
    add_icon_search_path(os.path.join(sys.prefix, 'share', 'icons'))

    return QIcon.fromTheme(name)
