# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

from base64 import b64decode
import email.utils
import quopri
import re


def get_sender(text):
    name, mail = email.utils.parseaddr(text)
    return name or mail


def rfc2047_parse_pairs(pairs):
    for name, addr in pairs:
        if name:
            name = rfc2047_parse(name)
        yield name, addr


RFC2047 = re.compile(r'=\?([^?]+)\?([^?]+)\?(.*)\?=')


def rfc2047_parse(name):
    """Parse RFC 2047-encoded name"""

    mtc = RFC2047.fullmatch(name)
    if mtc:
        charset = mtc[1].lower()
        func = mtc[2].lower()
        blob = mtc[3]

        if func == 'b':
            name = b64decode(blob).decode(charset)
        elif func == 'q':
            name = quopri.decodestring(blob).decode(charset)

    return name
