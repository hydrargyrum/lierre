
from subprocess import check_output

from lierre.builtins.fetchers.command import CommandForm, CommandJob

from .base import Plugin


class CommandPlugin(Plugin):
    def get_config(self):
        return self.config

    def set_config(self, config):
        self.config = config

    def build_config_form(self):
        return CommandForm(self)

    def start(self):
        return CommandJob(self)
