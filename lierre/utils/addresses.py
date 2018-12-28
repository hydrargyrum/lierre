
import email.utils


def get_sender(text):
    name, mail = email.utils.parseaddr(text)
    return name or mail

