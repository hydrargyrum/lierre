# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

import email.utils


def get_sender(text):
    name, mail = email.utils.parseaddr(text)
    return name or mail

