
from pathlib import Path

import xdg.BaseDirectory as xbd
import ruamel.yaml as yaml


def read_config():
    path = Path(xbd.save_config_path('lierre')).joinpath('config')
    if not path.exists():
        return

    with path.open() as fd:
        CONFIG.clear()
        CONFIG.update(yaml.safe_load(fd))


def write_config():
    path = Path(xbd.save_config_path('lierre')).joinpath('config')
    with path.open('w') as fd:
        yaml.dump(dict(CONFIG), fd, default_flow_style=False)


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

    def setdefault(self, *els):
        els = list(els)
        default = els.pop(-1)
        last_key = els.pop(-1)

        d = self
        for k in els:
            d = dict.setdefault(d, k, {})

        dict.setdefault(d, last_key, default)
        return d[last_key]


CONFIG = ConfigDict()
