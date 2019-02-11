#!/usr/bin/env python3

import locale
import logging
import sys

from .app import Application
from .ui.window import Window


def main():
    if sys.excepthook is sys.__excepthook__:
        sys.excepthook = lambda *args: sys.__excepthook__(*args)

    logging.basicConfig()
    locale.setlocale(locale.LC_ALL, '')

    app = Application(sys.argv)
    win = Window()
    win.show()
    app.exec()


if __name__ == '__main__':
    main()
