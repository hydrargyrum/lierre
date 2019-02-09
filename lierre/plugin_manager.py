
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

        enabled_sections = CONFIG.get('plugins', self.kind, fallback='')
        enabled_sections = list(filter(None, enabled_sections.strip().split('\n')))

        for section in enabled_sections:
            plugin_config = CONFIG['%s:%s' % (self.kind, section)]
            ep_name = plugin_config['ep_name']
            extension = EXTENSIONS_MANAGERS[self.kind][ep_name]

            LOGGER.info('loading plugin %r from extension %r', section, extension)
            try:
                plugin = extension.plugin()
                plugin.set_config(plugin_config)
            except Exception:
                LOGGER.exception('failed to load plugin %r', section)
                continue

            self.plugins[section] = plugin

    def iter_plugins(self):
        return EXTENSIONS_MANAGERS[self.kind]

    def iter_enabled_plugins(self):
        return self.plugins

    def write_config(self):
        working_plugins = []

        for name, plugin in self.plugins.items():
            section = '%s:%s' % (self.kind, name)
            if section not in CONFIG:
                CONFIG.add_section(section)

            try:
                plugin_config = plugin.get_config()
            except Exception:
                LOGGER.exception('failed to fetch config from plugin %r', section)
                continue
            # TODO ep_name and name should not be fetched from plugin

            CONFIG[section].clear()
            CONFIG[section].update(plugin_config)
            working_plugins.append(name)

        CONFIG['plugins'][self.kind] = working_plugins


def init_plugins_from_config(plugin_kind):
    EXTENSIONS_MANAGERS[plugin_kind] = stevedore.ExtensionManager('lierre.plugins.%s' % plugin_kind)
    PLUGINS[plugin_kind] = PluginList(plugin_kind)


def init():
    init_plugins_from_config('fetchers')
