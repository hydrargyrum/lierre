
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


def get_identities():
    identities = CONFIG.get('identities', default={})
    return {key: idt for key, idt in identities.items() if is_identity_valid(idt)}

# TODO signature, reply-to address
# TODO use a class for storing identity and validating


def send_email(identity, msg):
    assert isinstance(msg, EmailMessage)

    # prepare to add to mailbox
    box = MaildirPP()
    folder = box.try_get_folder([CONFIG.get('sent_folder', default='Sent')])
    box.create_folder(folder)

    # really send
    plugin = PLUGINS['senders'][identity['sender_plugin']]
    plugin.send(msg)

    # save in folder
    msg_path = box.add_message(msg, folder)  # TODO: add in cur?

    LOGGER.info('sent message saved to %r', msg_path)
    with open_db_rw() as db:
        nmsg, status = db.add_message(str(msg_path))
        nmsg.add_tag('sent', sync_maildir_flags=True)

    WATCHER.mailAdded.emit(msg['Message-ID'][1:-1])
