
import logging

import stevedore

from .config import CONFIG


LOGGER = logging.getLogger(__name__)

EXTENSIONS_MANAGERS = {}

PLUGINS = {}


class PluginList:
    def __init__(self, kind):
        self.plugins = {}
        self.kind = kind

        # TODO store disabled too?
        # or rather make 'enabled' a config key of the plugin?

        plugins = CONFIG.get('plugins', self.kind, default={})

        for plugin_key, plugin_config in plugins.items():
            ep_name = plugin_config['ep_name']
            extension = EXTENSIONS_MANAGERS[self.kind][ep_name]

            LOGGER.info('loading plugin %r from extension %r', plugin_key, extension)
            try:
                plugin = extension.plugin()
                plugin.set_config(plugin_config)
            except Exception:
                LOGGER.exception('failed to load plugin %r', plugin_key)
                continue

            self.plugins[plugin_key] = plugin

    def iter_plugins(self):
        return EXTENSIONS_MANAGERS[self.kind]

    def iter_enabled_plugins(self):
        return self.plugins

    def write_config(self):
        working_plugins = []

        for plugin_key, plugin in self.plugins.items():
            try:
                plugin_config = plugin.get_config()
            except Exception:
                LOGGER.exception('failed to fetch config from plugin %r', plugin_key)
                continue
            # TODO ep_name and name should not be fetched from plugin

            CONFIG.setdefault('plugins', {}).setdefault(self.kind, {})
            CONFIG['plugins'][self.kind] = plugin_config
            working_plugins.append(plugin_key)

        CONFIG['plugins'][self.kind] = working_plugins


def init_plugins_from_config(plugin_kind):
    EXTENSIONS_MANAGERS[plugin_kind] = stevedore.ExtensionManager('lierre.plugins.%s' % plugin_kind)
    PLUGINS[plugin_kind] = PluginList(plugin_kind)


def init():
    init_plugins_from_config('fetchers')
    init_plugins_from_config('filters')
