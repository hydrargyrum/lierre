
from subprocess import check_output

from PyQt5.QtWidgets import (
    QWidget, QFormLayout, QLabel, QLineEdit,
)

from .base import Plugin


class CommandForm(QWidget):
    def __init__(self, plugin):
        super(CommandForm, self).__init__()
        self.plugin = plugin

        layout = QFormLayout()
        self.setLayout(layout)
        self.editor = QLineEdit(self.plugin.config.get('command', ''))
        layout.addRow(QLabel(self.tr('Command')), self.editor)

    def update_config(self):
        self.plugin.config['command'] = self.editor.text()


class CommandPlugin(Plugin):
    def get_config(self):
        return self.config

    def set_config(self, config):
        self.config = config

    def build_config_form(self):
        return CommandForm(self)

    def run(self):
        check_output(self.config['command'], shell=True)
