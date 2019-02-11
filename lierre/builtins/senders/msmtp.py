
import email.policy
import logging
from subprocess import Popen, PIPE, STDOUT

from .base import Plugin


LOGGER = logging.getLogger(__name__)


class MSmtpPlugin(Plugin):
    def send(self, msg):
        cmd = ['msmtp', '--read-envelope-from', '--read-recipients']

        raw = msg.as_bytes(policy=email.policy.default)

        LOGGER.info('sending mail %r with msmtp', msg['Message-ID'])

        proc = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        outs, _ = proc.communicate(raw)

        if proc.returncode == 0:
            LOGGER.info('successfully sent with msmtp')
        else:
            LOGGER.error('msmtp exited with code %r', proc.returncode)
            LOGGER.error('msmtp output: %s', outs.decode('utf-8', errors='replace'))
            raise Exception('msmtp exited with code %r' % proc.returncode)

    def set_config(self, config):
        pass
