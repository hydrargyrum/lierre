
from pathlib import Path

import xdg.BaseDirectory as xbd
import yaml


def read_config():
    path = Path(xbd.save_config_path('lierre')).joinpath('config')
    if not path.exists():
        return

    with path.open() as fd:
        CONFIG.clear()
        CONFIG.update(yaml.load(fd))


def write_config():
    path = Path(xbd.save_config_path('lierre')).joinpath('config')
    with path.open('w') as fd:
        yaml.dump(CONFIG, fd)


class ConfigDict(dict):
    def get(self, *keys, default=None):
        d = self
        try:
            for k in keys:
                d = d[k]
        except KeyError:
            return default
        else:
            return d


CONFIG = ConfigDict()
