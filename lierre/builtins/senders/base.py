
class Plugin:
    def __init__(self):
        pass

    def is_available(self):
        return True

    def get_config(self):
        pass

    def set_config(self, config):
        return {}

    def build_config_form(self):
        pass

    def run(self):
        raise NotImplementedError()
