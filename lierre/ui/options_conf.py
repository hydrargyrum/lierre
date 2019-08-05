# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

from PyQt5.QtCore import Qt, pyqtSlot as Slot
from PyQt5.QtWidgets import QDialog, QListWidgetItem
from lierre.sending import get_identities
from lierre.plugin_manager import PLUGINS

from .ui_loader import load_ui_class


Ui_Dialog = load_ui_class('options_conf', 'Ui_Dialog')


class OptionsConf(Ui_Dialog, QDialog):
    def __init__(self, *args, **kwargs):
        super(OptionsConf, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.buttonBox.rejected.connect(self.reject)

        # plugins
        self.fetchersConf.setPluginKind('fetchers')
        self.filtersConf.setPluginKind('filters')
        self.sendersConf.setPluginKind('senders')
        self.miscConf.setPluginKind('misc')

        for widget in (self.fetchersConf, self.filtersConf, self.sendersConf, self.miscConf):
            self.finished.connect(widget.updateConfig)

        # identities
        identities = get_identities()
        for idt in identities.values():
            qitem = QListWidgetItem(idt.name)
            qitem.setData(Qt.UserRole, idt)
            self.identitiesList.addItem(qitem)

        for key in PLUGINS['senders'].iter_enabled_plugins():
            self.senderCombo.addItem(key)

    @Slot(QListWidgetItem, QListWidgetItem)
    def on_identitiesList_currentItemChanged(self, qitem, _):
        idt = qitem.data(Qt.UserRole)
        self.fullNameEdit.setText(idt.name)
        self.emailEdit.setText(idt.address)
        self.senderCombo.setCurrentText(idt.sender_plugin)
