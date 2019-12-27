# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

from subprocess import check_output, CalledProcessError

from .base import Plugin


class KhardPlugin(Plugin):
    def _build_command(self):
        cmd = ['khard']
        if self.config.get('config_file'):
            cmd += ['-c', self.config['config_file']]
        return cmd

    def set_config(self, config):
        self.config = config

    def get_config(self):
        return self.config

    def search_contacts(self, s, others, message):
        cmd = self._build_command()
        cmd += ['email', '-p', s]

        try:
            out = check_output(cmd, encoding='utf-8').strip().split('\n')
        except CalledProcessError as exc:
            if exc.returncode != 1:
                raise
            # when there are no results, khard exits with status 1
            assert exc.output.startswith('searching for ')
            return []

        assert out[0].startswith('searching for ')
        entries = []
        for line in out[1:]:
            addr, name, _ = line.split('\t')
            entries.append((name, addr))

        return entries
