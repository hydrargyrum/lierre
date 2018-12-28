#!/usr/bin/env python3

import locale
import sys

from .app import Application
from .ui.window import Window

if sys.excepthook is sys.__excepthook__:
    sys.excepthook = lambda *args: sys.__excepthook__(*args)


locale.setlocale(locale.LC_ALL, '')
app = Application(sys.argv)
win = Window()
win.show()
app.exec()

