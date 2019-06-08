
from PyQt5.QtWidgets import (
    QTabWidget, QAction,
)
from PyQt5.QtCore import pyqtSlot as Slot, pyqtSignal as Signal
from PyQt5.QtGui import QKeySequence

from .threads_widget import ThreadsWidget
from .thread_widget import ThreadWidget
from .compose import ComposeWidget


class TabWidget(QTabWidget):
    def __init__(self, *args, **kwargs):
        super(TabWidget, self).__init__(*args, **kwargs)

        self.tabCloseRequested.connect(self._closeTabRequested)

        action = QAction(self)
        action.setShortcuts(QKeySequence.Close)
        action.triggered.connect(self.closeCurrentTab)
        self.addAction(action)

        action = QAction(self)
        action.setShortcuts(QKeySequence('Ctrl+Page Up'))
        action.triggered.connect(self.moveToPreviousTab)
        self.addAction(action)

        action = QAction(self)
        action.setShortcuts(QKeySequence('Ctrl+Page Down'))
        action.triggered.connect(self.moveToNextTab)
        self.addAction(action)

        self.addThreads()

    def addThreads(self):
        w = ThreadsWidget(parent=self)
        idx = self._addTab(w)
        w.threadActivated.connect(self.addThread)
        w.tagActivated.connect(self._addThreadsTag)
        self.setCurrentIndex(idx)
        return w

    @Slot(str)
    def _addThreadsTag(self, tag):
        w = self.addThreads()
        w.setQueryAndSearch('tag:%s' % tag)

    @Slot(str)
    def addThread(self, tid):
        w = ThreadWidget(tid, parent=self)
        w.triggeredReply.connect(self.addReply)
        idx = self._addTab(w)
        self.setCurrentIndex(idx)
        return w

    @Slot(str, bool)
    def addReply(self, mid, to_all):
        w = ComposeWidget(parent=self)
        w.sent.connect(self._closeCompose)
        w.setReply(mid, to_all)
        idx = self._addTab(w)
        self.setCurrentIndex(idx)
        return w

    @Slot()
    def addCompose(self):
        w = ComposeWidget(parent=self)
        w.sent.connect(self._closeCompose)
        idx = self._addTab(w)
        self.setCurrentIndex(idx)
        return w

    @Slot()
    def _closeCompose(self):
        w = self.sender()
        idx = self.indexOf(w)
        self.removeTab(idx)
        w.deleteLater()

    @Slot(str)
    def addForward(self, mid):
        pass

    def _addTab(self, widget):
        idx = self.addTab(widget, widget.windowTitle())
        widget.windowTitleChanged.connect(self._tabTitleChanged)
        return idx

    @Slot(int)
    def _closeTabRequested(self, idx):
        if self.count() > 1:
            self.removeTab(idx)

    @Slot()
    def closeCurrentTab(self):
        if self.count() > 1:
            self.removeTab(self.currentIndex())

    def removeTab(self, idx):
        w = self.widget(idx)
        super(TabWidget, self).removeTab(idx)
        w.setParent(None)

    @Slot()
    def moveToNextTab(self):
        idx = (self.currentIndex() + 1) % self.count()
        self.setCurrentIndex(idx)

    @Slot()
    def moveToPreviousTab(self):
        idx = (self.currentIndex() - 1) % self.count()
        self.setCurrentIndex(idx)

    @Slot(str)
    def _tabTitleChanged(self, title):
        widget = self.sender()
        idx = self.indexOf(widget)
        if idx < 0:
            return

        self.setTabText(idx, title)
        self.someTabTitleChanged.emit()

    someTabTitleChanged = Signal()

