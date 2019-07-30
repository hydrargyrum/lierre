
from importlib import import_module
from pathlib import Path

from PyQt5.uic import loadUiType


def load_ui_class(module_name, class_name, package='lierre.ui'):
    try:
        mod = import_module(f'.{module_name}_ui', package)
    except ImportError:
        pkg_parts = package.split('.')
        folder = Path(__file__).parent.parent.joinpath(*pkg_parts[1:])
        path = folder.joinpath(f'{module_name}.ui')
        return loadUiType(str(path))[0]
    else:
        return getattr(mod, class_name)
