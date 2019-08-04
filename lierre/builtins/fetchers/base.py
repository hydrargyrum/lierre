# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

from PyQt5.QtCore import QObject, pyqtSignal as Signal


class Job(QObject):
    progress = Signal(int)
    finished = Signal(int)

    def start(self):
        raise NotImplementedError()


class Plugin(QObject):
    def enable(self):
        pass

    def disable(self):
        pass

    def is_available(self):
        return True

    def get_config(self):
        pass

    def set_config(self, config):
        return {}

    def build_config_form(self):
        pass

    def create_job(self, **kwargs):
        pass
