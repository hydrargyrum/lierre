# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

from email.message import EmailMessage
import logging

from lierre.utils.db_ops import open_db_rw
from lierre.utils.maildir_ops import MaildirPP
from lierre.change_watcher import WATCHER

from .plugin_manager import PLUGINS
from .config import CONFIG


LOGGER = logging.getLogger(__name__)


def is_identity_valid(d):
    return d.get('name') and d.get('email') and d.get('sender_plugin')


class Identity:
    def __init__(self, *, key=None, name=None, address=None, sender_plugin=None):
        self.key = key
        self.name = name
        self.address = address
        self.sender_plugin = sender_plugin

    def is_valid(self):
        return self.name and self.address and self.sender_plugin and self.key


def get_identities():
    identities_cfg = CONFIG.get('identities', default={})
    identities = {
        key: Identity(key=key, name=v['name'], sender_plugin=v['sender_plugin'], address=v['email'])
        for key, v in identities_cfg.items()
    }
    return {
        key: idt for key, idt in identities.items() if idt.is_valid()
    }


# TODO signature, reply-to address


def send_email(identity, msg):
    assert isinstance(msg, EmailMessage)

    # prepare to add to mailbox
    box = MaildirPP()
    folder = box.get_root()

    # really send
    plugin = PLUGINS['senders'][identity.sender_plugin]
    plugin.send(msg)

    # save in folder
    msg_path = box.add_message(msg, folder)  # TODO: add in cur?

    LOGGER.info('sent message saved to %r', msg_path)
    with open_db_rw() as db:
        nmsg, status = db.add_message(str(msg_path))
        nmsg.add_tag('sent', sync_maildir_flags=True)

    WATCHER.mailAdded.emit(msg['Message-ID'][1:-1])
