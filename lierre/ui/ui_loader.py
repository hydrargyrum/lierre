
from importlib import import_module
from pathlib import Path

from PyQt5.uic import loadUiType


def load_ui_class(module_name, class_name):
    try:
        mod = import_module('.%s_ui' % module_name, 'lierre.ui')
    except ImportError:
        path = Path(__file__).with_name('%s.ui' % module_name)
        return loadUiType(str(path))[0]
    else:
        return getattr(mod, class_name)
