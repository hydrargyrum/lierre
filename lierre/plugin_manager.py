# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

import logging
from collections import OrderedDict

import stevedore

from .config import CONFIG, write_config as config_write_config


LOGGER = logging.getLogger(__name__)

EXTENSIONS_MANAGERS = {}

PLUGINS = {}


class PluginList:
    def __init__(self, kind):
        self.plugins = OrderedDict()
        self.kind = kind

        plugins = CONFIG.get('plugins', self.kind, default={})

        for plugin_key, plugin_config in plugins.items():
            self._load_plugin(plugin_key, plugin_config)

    def _load_plugin(self, plugin_key, plugin_config):
        assert plugin_key not in self.plugins

        ep_name = plugin_config['ep_name']
        extension = EXTENSIONS_MANAGERS[self.kind][ep_name]

        LOGGER.info('loading plugin %r from extension %r', plugin_key, extension)
        try:
            plugin = extension.plugin()
            plugin.set_config(plugin_config)
            plugin.enable()
        except Exception:
            LOGGER.exception('failed to load plugin %r', plugin_key)
            return False

        self.plugins[plugin_key] = plugin
        return True

    def iter_extensions(self):
        return EXTENSIONS_MANAGERS[self.kind]

    def iter_enabled_plugins(self):
        return self.plugins

    def write_config(self):
        new_conf = OrderedDict()

        for plugin_key, plugin in self.plugins.items():
            try:
                plugin_config = plugin.get_config()
                assert plugin_config
            except Exception:
                LOGGER.exception('failed to fetch config from plugin %r', plugin_key)
                continue
            # TODO ep_name should not be fetched from plugin

            new_conf[plugin_key] = plugin_config

        CONFIG.setdefault('plugins', {})[self.kind] = new_conf

        config_write_config()

    def reorder_plugins(self, new_order):
        assert len(new_order) == len(self.plugins)
        self.plugins = OrderedDict((k, self.plugins[k]) for k in new_order)

    def add_plugin(self, name, ep_name):
        config = {'ep_name': ep_name}
        return self._load_plugin(name, config)

    def remove_plugin(self, name):
        try:
            self.plugins[name].disable()
        except Exception:
            LOGGER.exception('failed to disable plugin %r', name)
            raise

        del self.plugins[name]
        try:
            del CONFIG['plugins'][self.kind][name]
        except KeyError:
            pass

    def __getitem__(self, key):
        return self.plugins[key]


def init_plugins_from_config(plugin_kind):
    EXTENSIONS_MANAGERS[plugin_kind] = stevedore.ExtensionManager('lierre.plugins.%s' % plugin_kind)
    PLUGINS[plugin_kind] = PluginList(plugin_kind)


def init():
    init_plugins_from_config('fetchers')
    init_plugins_from_config('filters')
    init_plugins_from_config('senders')
    init_plugins_from_config('misc')

