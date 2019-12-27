# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details


class Plugin:
    def enable(self):
        pass

    def disable(self):
        pass

    def set_config(self, config):
        pass

    def get_config(self):
        pass

    def search_contacts(self, input: str, others: dict, message):
        raise NotImplementedError()

    def index_recipients(self, nmsg):
        pass
