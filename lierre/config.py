
from configparser import ConfigParser
from pathlib import Path

import xdg.BaseDirectory as xbd


def read_config():
    path = Path(xbd.save_config_path('lierre')).joinpath('config')
    if not path.exists():
        return

    with path.open() as fd:
        CONFIG.read_file(fd)


def write_config():
    path = Path(xbd.save_config_path('lierre')).joinpath('config')
    with path.open('w') as fd:
        CONFIG.write(fd)


CONFIG = ConfigParser(interpolation=None)
