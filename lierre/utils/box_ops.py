
from base64 import b64encode, b64decode
from collections import namedtuple
from logging import getLogger
import mailbox
from pathlib import Path
import re
from time import time

from .db_ops import get_db_path, open_db_rw


LOGGER = getLogger(__name__)


def decode_maildir_name(name: str) -> str:
    # what a great encoding!
    def pad(b):
        if len(b) % 4:
            b += '=' * (4 - (len(b) % 4))
        return b

    def replace(mtc):
        seq = mtc.group(1)
        if seq == '':
            return '&'
        seq = pad(seq)
        return b64decode(seq, '+,').decode('utf-16-be')

    if isinstance(name, bytes):
        name = name.decode('ascii')

    name = re.sub(r'&([A-Za-z0-9+,]*)-', replace, name)
    return name


def encode_maildir_name(s: str) -> str:
    ret = bytearray()
    amp = ord('&')
    reserved = ord('.'), ord('/')

    s = s.encode('utf-16-be')
    for hi, lo in zip(s[::2], s[1::2]):
        if hi == 0:
            if lo == amp:
                ret.extend(b'&-')
                continue
            elif lo <= 127 and lo not in reserved:
                ret.append(lo)
                continue

        ret += b'&'
        ret.extend(b64encode(bytes([hi, lo]), b'+,').rstrip(b'='))
        ret += b'-'

    return ret.decode('ascii')


def subpath_to_maildir_name(subpath: str) -> str:
    path = '.'.join(encode_maildir_name(part) for part in subpath.split('/'))
    return '.%s' % path


def subpath_from_maildir_name(name: str) -> str:
    name = name.lstrip('.')
    return '/'.join(decode_maildir_name(part) for part in name.split('.'))


def test_maildir_encodings():
    assert encode_maildir_name('Rés.umé') == 'R&AOk-s&AC4-um&AOk-'
    assert 'Rés.umé' == decode_maildir_name('R&AOk-s&AC4-um&AOk-')

    assert subpath_to_maildir_name('foo.bar/qux') == '.foo&AC4-bar.qux'
    assert 'foo.bar/qux' == subpath_from_maildir_name('.foo&AC4-bar.qux')


def get_box_path(box_name: str) -> Path:
    path = Path(get_db_path())
    return path.joinpath(subpath_to_maildir_name(box_name))


def box_path_from_msg(msg_path) -> Path:
    msg_path = Path(msg_path)
    return msg_path.parent.parent


class Folder(namedtuple('Folder', ('path', 'parts'))):
    @property
    def dir(self):
        return str(self.path)

    @property
    def encoded_name(self):
        return self.path.name

    @property
    def basename(self):
        return self.parts[-1]


def list_folders():
    root = Path(get_db_path())

    yield Folder(root, ())

    for sub in root.iterdir():
        if not (sub.is_dir() and sub.joinpath('cur').exists()):
            continue

        yield Folder(
            sub,
            tuple(decode_maildir_name(part) for part in sub.name[1:].split('.'))
        )


TMP_CLEAN_THRESHOLD_SECS = 36 * 60 * 60  # 36 hours


def clean_tmp_box(box):
    box = Path(box)

    now = time()
    for sub in box.joinpath('tmp').iterdir():
        if sub.is_file() and now - sub.stat().st_mtime > TMP_CLEAN_THRESHOLD_SECS:
            sub.unlink()


def move_to_mailbox(src_path, target_box_path) -> Path:
    LOGGER.debug('moving %r to %r', src_path, target_box_path)
    src_path = Path(src_path)
    target_box_path = Path(target_box_path)

    box = mailbox.Maildir(str(target_box_path))

    with src_path.open('rb') as src_fd:
        new_key = box.add(src_fd)
    dest_path = target_box_path.joinpath(box._lookup(new_key))

    with open_db_rw() as db:
        db.add_message(str(dest_path))
        db.remove_message(str(src_path))
    src_path.unlink()

    return dest_path


def change_flags(src_path, to_add=None, to_remove=None):
    if ':2,' not in src_path.name:
        raise NotImplementedError()

    to_add = set(to_add or [])
    to_remove = set(to_remove or [])
    src_path = Path(src_path)

    name, _, flags = src_path.name.rpartition(',')
    flags = set(flags)
    flags |= to_add
    flags -= to_remove

    dest_path = src_path.with_name('%s,%s' % (name, ''.join(flags)))
    src_path.rename(dest_path)
