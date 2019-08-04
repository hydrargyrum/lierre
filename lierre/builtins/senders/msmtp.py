# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

import email.policy
import logging
import re
import sys

from PyQt5.QtWidgets import QWidget
from lierre.ui.ui_loader import load_ui_class
from lierre.credentials import get_credential, list_credentials
from lierre.utils.pexpect import env_c_lang, expect_get_obj, close_expect
from pexpect import spawn, EOF, TIMEOUT

from .base import Plugin


LOGGER = logging.getLogger(__name__)


Ui_Form = load_ui_class('msmtp', 'Form', 'lierre.builtins.senders')


class Widget(Ui_Form, QWidget):
    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin

        self.setupUi(self)

        self.cfgEdit.setText(self.plugin.config.get('config_file', ''))

        self.credentialBox.addItem('<do not use credential>')
        for cred in list_credentials():
            self.credentialBox.addItem(cred)
        credential = self.plugin.config.get('credential')
        if credential:
            self.credentialBox.setCurrentText(credential)
        else:
            self.credentialBox.setCurrentIndex(0)

    def update_config(self):
        self.plugin.config['config_file'] = self.cfgEdit.text()

        if self.credentialBox.currentIndex() == 0:
            self.plugin.config['credential'] = ''
        else:
            self.plugin.config['credential'] = self.credentialBox.currentText()


class CommandError(Exception):
    pass


class MSmtpPlugin(Plugin):
    PASSWORD_PATTERN = re.compile(r'password for \S+ at \S+:')
    ERROR_PATTERN = re.compile(r'msmtp: could not send mail \(account \S+ from .*\)')

    def send(self, msg):
        conf = self.config.get('config_file', '').strip()

        cmd = ['msmtp', '--read-envelope-from', '--read-recipients']
        if conf:
            cmd += ['-C', conf]

        # - msmtp reads headers on stdin to find identity
        # - then it reads its configuration and might ask password on TTY
        #   (use credentials in that case)
        # - then it reads the message body on stdin (until we send EOF)

        policy = email.policy.default
        raw_b = msg.as_bytes(policy=policy)
        raw = raw_b.decode('ascii')
        headers_s, sep, body_s = raw.partition(policy.linesep * 2)

        pe = spawn(cmd[0], args=cmd[1:], encoding='utf-8', env=env_c_lang())

        try:
            pe.setecho(False)
            pe.logfile_read = sys.stdout

            pe.send(headers_s + sep)

            event = expect_get_obj(pe, [self.PASSWORD_PATTERN, self.ERROR_PATTERN, TIMEOUT], timeout=10)
            # msmtp doesn't ack the correct password but it rejects an incorrect one
            # we don't know if msmtp didn't try to login yet
            # or if it logged successfully
            # this is stupid because we're not sure whether we need to send password or body
            if event is self.PASSWORD_PATTERN:
                pe.sendline(get_credential(self.config['credential']))
                # we still can't be sure it worked or it didn't login yet
                # let's send the body and see if it complains at some point
            elif event is self.ERROR_PATTERN:
                LOGGER.error('msmtp encoutered an error: %s', pe.before)
                raise CommandError(pe.before + pe.after)

            bufsize = 256
            for offset in range(0, len(body_s), bufsize):
                event = expect_get_obj(pe, [self.PASSWORD_PATTERN, self.ERROR_PATTERN, TIMEOUT], timeout=0)
                if event is self.ERROR_PATTERN:
                    LOGGER.error('msmtp encountered an error: %s', pe.before)
                    raise CommandError(pe.before + pe.after)
                elif event is self.PASSWORD_PATTERN:
                    LOGGER.error('msmtp unexpectedly asked password again, exiting')
                    raise CommandError('unexpected password')

                pe.send(body_s[offset:offset + bufsize])

            pe.sendeof()

            # final error verification, in case we sent the whole mail to msmtp
            # but msmtp or the server were so slow they did not test the password
            event = expect_get_obj(pe, [self.PASSWORD_PATTERN, self.ERROR_PATTERN, EOF])
            if event is self.ERROR_PATTERN:
                LOGGER.error('msmtp encountered an error: %s', pe.before)
                raise CommandError(pe.before + pe.after)
            elif event is self.PASSWORD_PATTERN:
                LOGGER.error('msmtp unexpectedly asked password again, exiting')
                raise CommandError('unexpected password')

            pe.close()

            if pe.signalstatus:
                return pe.signalstatus + 128
            return pe.exitstatus
        except EOF:
            LOGGER.error('msmtp unexpectedly EOF-ed')
            raise CommandError('unexpected EOF')
        finally:
            close_expect(pe)

    def set_config(self, config):
        self.config = config

    def get_config(self):
        return self.config

    def enable(self):
        pass

    def disable(self):
        pass

    def build_config_form(self):
        return Widget(self)
