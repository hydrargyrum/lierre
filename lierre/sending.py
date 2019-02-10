
from email.message import EmailMessage
from email.headerregistry import Address
from email.utils import make_msgid
import logging
import mailbox
from pathlib import Path

from lierre.utils.db_ops import open_db_rw, get_db_path

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

    # finish preparing EmailMessage
    from_addr = Address(identity['name'], addr_spec=identity['email'])
    msg['From'] = from_addr
    msg['Message-ID'] = make_msgid(domain=from_addr.domain)

    # prepare to add to mailbox
    box = mailbox.Maildir(get_db_path())
    boxmsg = mailbox.MaildirMessage(msg)
    boxmsg.add_flag('S')
    boxmsg.set_subdir('cur')

    # really send
    plugin = PLUGINS['senders'][identity['sender_plugin']]
    plugin.send(msg)

    # save in folder
    uniq = box.add(boxmsg)
    msg_path = str(Path(get_db_path()).joinpath(box._lookup(uniq)))

    LOGGER.info('sent message saved to %r', msg_path)
    with open_db_rw() as db:
        db.add_message(msg_path)
