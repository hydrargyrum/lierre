
from PyQt5.QtWidgets import QDialog

from .options_conf_ui import Ui_Dialog


class OptionsConf(Ui_Dialog, QDialog):
    def __init__(self, *args, **kwargs):
        super(OptionsConf, self).__init__(*args, **kwargs)
        self.setupUi(self)

        self.buttonBox.rejected.connect(self.reject)

        self.fetchersConf.setPluginKind('fetchers')
        self.filtersConf.setPluginKind('filters')
        self.sendersConf.setPluginKind('senders')

