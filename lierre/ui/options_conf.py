# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

from PyQt5.QtWidgets import QDialog

from .ui_loader import load_ui_class


Ui_Dialog = load_ui_class('options_conf', 'Ui_Dialog')


class OptionsConf(Ui_Dialog, QDialog):
    def __init__(self, *args, **kwargs):
        super(OptionsConf, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.buttonBox.rejected.connect(self.reject)

        self.fetchersConf.setPluginKind('fetchers')
        self.filtersConf.setPluginKind('filters')
        self.sendersConf.setPluginKind('senders')
        self.miscConf.setPluginKind('misc')

        for widget in (self.fetchersConf, self.filtersConf, self.sendersConf, self.miscConf):
            self.finished.connect(widget.updateConfig)
