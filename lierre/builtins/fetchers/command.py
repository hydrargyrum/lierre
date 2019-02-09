
from subprocess import check_output

from .base import Plugin


class CommandPlugin(Plugin):
    def get_config(self):
        return self.config

    def set_config(self, config):
        self.config = config

    def run(self):
        check_output(self.config['command'], shell=True)
