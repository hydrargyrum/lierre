
import os
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

    from . import credentials

    credentials.load()


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

        return dict.setdefault(d, last_key, default)

    def set(self, *els):
        els = list(els)
        value = els.pop(-1)
        last_key = els.pop(-1)

        d = self.setdefault(*els, {})
        d[last_key] = value


CONFIG = ConfigDict()


def get_notmuch_config_path():
    return os.environ.get('NOTMUCH_CONFIG', str(Path.home().joinpath('.notmuch-config')))


def test_config():
    d = ConfigDict()
    assert d.get('foo', 'bar') is None
    assert d.get('foo', 'bar', default=1) == 1

    assert d.setdefault('foo', 'bar', 2) == 2
    assert d.get('foo', 'bar') == 2

    assert d.setdefault('foo', 'bar', 3) == 2
    assert d.get('foo', 'bar') == 2

    d.set('foo', 'bar', 4)
    assert d.get('foo', 'bar') == 4
