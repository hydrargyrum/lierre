# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

from logging import getLogger
import os
from pathlib import Path

import xdg.BaseDirectory as xbd
import ruamel.yaml as yaml


LOGGER = getLogger(__name__)


def read_config():
    path = Path(xbd.save_config_path('lierre')).joinpath('config')
    if not path.exists():
        LOGGER.warning('cannot read config, file does not exist: %s', path)
        return

    with path.open() as fd:
        CONFIG.clear()
        CONFIG.update(yaml.safe_load(fd))
    LOGGER.debug('read config: %s', path)

    from . import credentials

    credentials.load()


def write_config():
    path = Path(xbd.save_config_path('lierre')).joinpath('config')
    LOGGER.debug('writing config: %s', path)
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
