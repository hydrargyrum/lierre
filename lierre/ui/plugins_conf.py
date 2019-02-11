
from PyQt5.QtCore import (
    pyqtSlot as Slot,
)
from PyQt5.QtWidgets import QListWidgetItem, QWidget
from lierre.plugin_manager import PLUGINS

from .plugins_conf_ui import Ui_Form


class PluginsConf(Ui_Form, QWidget):
    def __init__(self, *args, **kwargs):
        super(PluginsConf, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.plugin_kind = None

        self.pluginsList.currentItemChanged.connect(self.updateButtons)
        self.pluginsList.currentItemChanged.connect(self.updatePlugins)

    def setPluginKind(self, plugin_kind):
        self.plugin_kind = plugin_kind
        self.pluginsList.clear()

        for name, plugin in PLUGINS[plugin_kind].iter_enabled_plugins().items():
            item = QListWidgetItem(name)
            self.pluginsList.addItem(item)

    @Slot(QListWidgetItem)
    def updatePlugins(self, new_item):
        layout_item = self.pluginConf.layout().itemAt(0)
        if layout_item:
            plugin_widget = layout_item.widget()
            plugin_widget.update_config()
            plugin_widget.deleteLater()

        if new_item:
            plugin = PLUGINS[self.plugin_kind][new_item.text()]
            new_widget = plugin.build_config_form()
            if new_widget:
                self.pluginConf.layout().addWidget(new_widget)

    @Slot(QListWidgetItem)
    def updateButtons(self, item):
        if item:
            self.upButton.setEnabled(self.pluginsList.row(item) > 0)
            self.downButton.setEnabled(self.pluginsList.row(item) < self.pluginsList.count() - 1)
            self.removeButton.setEnabled(True)
            self.addButton.setEnabled(True)
        else:
            self.upButton.setEnabled(False)
            self.downButton.setEnabled(False)
            self.addButton.setEnabled(False)
            self.removeButton.setEnabled(False)

