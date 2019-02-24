
import re

from PyQt5.QtCore import (
    pyqtSlot as Slot,
)
from PyQt5.QtWidgets import QListWidgetItem, QWidget, QInputDialog, QLineEdit
from lierre.plugin_manager import PLUGINS

from .ui_loader import load_ui_class


Ui_Form = load_ui_class('plugins_conf', 'Ui_Form')


class PluginsConf(Ui_Form, QWidget):
    def __init__(self, *args, **kwargs):
        super(PluginsConf, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.plugin_kind = None

        self.pluginsList.currentItemChanged.connect(self.updateButtons)
        self.pluginsList.currentItemChanged.connect(self.updatePlugins)

        self.removeButton.clicked.connect(self._removePlugin)
        self.addButton.clicked.connect(self._addPlugin)
        self.upButton.clicked.connect(self._moveUpPlugin)
        self.downButton.clicked.connect(self._moveDownPlugin)

        self.updateButtons(None)

    def setPluginKind(self, plugin_kind):
        self.plugin_kind = plugin_kind
        self.plugins = PLUGINS[plugin_kind]
        self.pluginsList.clear()

        for name, plugin in self.plugins.iter_enabled_plugins().items():
            item = QListWidgetItem(name)
            self.pluginsList.addItem(item)

    @Slot(QListWidgetItem)
    def updatePlugins(self, new_item):
        self.updateConfig()
        layout_item = self.pluginConf.layout().takeAt(0)
        if layout_item:
            plugin_widget = layout_item.widget()
            plugin_widget.deleteLater()

        if new_item:
            plugin = self.plugins[new_item.text()]
            new_widget = plugin.build_config_form()
            if new_widget:
                self.pluginConf.layout().addWidget(new_widget)

    @Slot(QListWidgetItem)
    def updateButtons(self, item):
        if item:
            self.upButton.setEnabled(self.pluginsList.row(item) > 0)
            self.downButton.setEnabled(self.pluginsList.row(item) < self.pluginsList.count() - 1)
            self.removeButton.setEnabled(True)
        else:
            self.upButton.setEnabled(False)
            self.downButton.setEnabled(False)
            self.removeButton.setEnabled(False)

    def _build_unused_name(self, ep):
        pattern = re.compile(r'%s_(\d+)' % re.escape(ep))
        matches = (pattern.fullmatch(plugin) for plugin in self.plugins.iter_enabled_plugins())
        matches = (int(match.group(1)) for match in matches if match)
        num = max(matches, default=0)
        return '%s_%d' % (ep, num + 1)

    def _addPlugin(self):
        entrypoint_names = [ext.name for ext in self.plugins.iter_extensions()]
        if not entrypoint_names:
            return

        # TODO display better labels
        ep_name, ok = QInputDialog.getItem(self, self.tr('Plugin'), self.tr('Choose a plugin to configure'), entrypoint_names, 0, False)
        if not ok:
            return

        default_name = self._build_unused_name(ep_name)
        while True:
            name, ok = QInputDialog.getText(self, self.tr('Name'), self.tr('Associate a name for this configuration'), QLineEdit.Normal, default_name)
            if not ok:
                return

            if name not in self.plugins.iter_enabled_plugins():
                break

        if not self.plugins.add_plugin(name, ep_name):
            return

        qitem = QListWidgetItem(name, self.pluginsList)
        self.pluginsList.setCurrentItem(qitem)

    def _removePlugin(self):
        row = self.pluginsList.currentRow()
        item = self.pluginsList.currentItem()
        self.plugins.remove_plugin(item.text())
        self.pluginsList.takeItem(row)

    def _moveDownPlugin(self):
        self._reorder_shift(1)

    def _moveUpPlugin(self):
        self._reorder_shift(-1)

    def _reorder_shift(self, offset):
        row = self.pluginsList.currentRow()
        assert row >= 0
        assert 0 <= row + offset < self.pluginsList.count()
        item = self.pluginsList.takeItem(row)
        self.pluginsList.insertItem(row + offset, item)
        self.pluginsList.setCurrentItem(item)

        new_order = [self.pluginsList.item(i).text() for i in range(self.pluginsList.count())]
        self.plugins.reorder_plugins(new_order)

    @Slot()
    def updateConfig(self):
        layout_item = self.pluginConf.layout().itemAt(0)
        if layout_item:
            plugin_widget = layout_item.widget()
            plugin_widget.update_config()

        self.plugins.write_config()
