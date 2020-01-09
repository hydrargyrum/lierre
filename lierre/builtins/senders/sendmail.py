# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

import email.policy
import logging
import shlex
from shutil import which
from subprocess import Popen, SubprocessError, PIPE

from .base import Plugin


LOGGER = logging.getLogger(__name__)


class CommandError(Exception):
    pass


class SendmailPlugin(Plugin):
    def is_available(self):
        return bool(which('sendmail'))

    def set_config(self, config):
        self.config = config

    def get_config(self):
        return self.config

    def enable(self):
        pass

    def disable(self):
        pass

    def build_config_form(self, widget):
        pass

    def run(self, msg):
        policy = email.policy.default
        raw_b = msg.as_bytes(policy=policy)
        raw = raw_b.decode('ascii')

        cmd = [
            'sendmail',
            '-i',  # "." line is not the end, EOF is
            '-t',  # use recipients from message headers, not arguments
        ]
        cmd += shlex.split(self.config.get('arguments', ''))

        proc = Popen(cmd, encoding='utf-8', stderr=PIPE)
        try:
            stdout, stderr = proc.communicate(raw)
            proc.wait()
        except SubprocessError:
            proc.terminate()
            raise

        if proc.returncode != 0:
            raise CommandError(stderr)
