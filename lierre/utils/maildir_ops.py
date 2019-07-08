
from base64 import b64encode, b64decode
from collections import namedtuple
import email.policy
from logging import getLogger
from os import getpid
from pathlib import Path
import re
import shutil
from socket import gethostname
from time import time
from typing import Union, Optional, Iterable

from .db_ops import get_db_path, open_db_rw


LOGGER = getLogger(__name__)

TMP_CLEAN_THRESHOLD_SECS = 36 * 60 * 60  # 36 hours

StrOrPath = Union[str, Path]
Tags = Iterable[str]


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

    u16 = s.encode('utf-16-be')
    for hi, lo in zip(u16[::2], u16[1::2]):
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


def test_maildir_encodings():
    assert encode_maildir_name('Rés.umé') == 'R&AOk-s&AC4-um&AOk-'
    assert 'Rés.umé' == decode_maildir_name('R&AOk-s&AC4-um&AOk-')


def box_path_from_msg(msg_path: StrOrPath) -> Path:
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


def change_flags(src_path: StrOrPath, to_add: Optional[Tags] = None, to_remove: Optional[Tags] = None):
    src_path = Path(src_path)
    if ':2,' not in src_path.name:
        raise NotImplementedError()

    to_add = set(to_add or [])
    to_remove = set(to_remove or [])
    src_path = Path(src_path)

    name, sep, s_flags = src_path.name.rpartition(':2,')
    flags = set(s_flags)
    flags |= to_add
    flags -= to_remove

    dest_path = src_path.with_name('%s%s%s' % (name, sep, ''.join(flags)))
    src_path.rename(dest_path)

    with open_db_rw() as db:
        db.add_message(str(dest_path))
        db.remove_message(str(src_path))


class MaildirPP:
    def __init__(self, path: Optional[StrOrPath] = None):
        if path is None:
            path = get_db_path()
        self.path = Path(path)

    def list_folders(self) -> Iterable[Folder]:
        root = self.path

        yield Folder(root, ())

        for sub in root.iterdir():
            if not (sub.is_dir() and sub.joinpath('cur').exists()):
                continue

            yield Folder(
                sub,
                tuple(decode_maildir_name(part) for part in sub.name[1:].split('.'))
            )

    def get_root(self):
        return Folder(self.path, ())

    def try_get_folder(self, parts: Iterable[str]) -> Folder:
        sub = self.path.joinpath('.%s' % '.'.join(encode_maildir_name(part) for part in parts))
        return Folder(sub, parts)

    def create_folder(self, folder: Folder) -> None:
        LOGGER.debug('creating folder %r', folder.path)
        for sub in ('new', 'cur', 'tmp'):
            folder.path.joinpath(sub).mkdir(parents=True, exist_ok=True)

    def _build_uniq(self, folder: Folder) -> Path:
        tmp_path = folder.path.joinpath('tmp')

        # choose courier-mta scheme even though uuid4 would probably suffice
        now = time()
        name = f'{int(now)}.M{int(now % 1 * 1e6)}P{getpid()}.{gethostname()}'
        tmp_uniq = tmp_path.joinpath(name)
        try:
            tmp_uniq.touch(exist_ok=False)
        except FileExistsError:
            return self._build_uniq(folder)
        return tmp_uniq

    def _move_to_new(self, tmp_uniq: Path, folder: Folder) -> Path:
        dest_path = folder.path.joinpath('new').joinpath(tmp_uniq.name)
        LOGGER.debug('moving %r to %r', tmp_uniq, dest_path)
        tmp_uniq.rename(dest_path)
        return dest_path

    def _move_to_cur(self, tmp_uniq: Path, folder: Folder, flags: str = '') -> Path:
        dest_path = folder.path.joinpath('cur').joinpath(f'{tmp_uniq.name}:2,{flags}')
        LOGGER.debug('moving %r to %r', tmp_uniq, dest_path)
        tmp_uniq.rename(dest_path)
        return dest_path

    def _parse_flags(self, msg_name: str) -> str:
        return msg_name.rpartition(':2,')[2]

    def add_message(self, msg, folder: Folder) -> Path:
        tmp_uniq = self._build_uniq(folder)
        LOGGER.debug('creating message in %r', tmp_uniq)
        tmp_uniq.write_bytes(msg.as_bytes(policy=email.policy.default))
        return self._move_to_new(tmp_uniq, folder)

    def move_message(self, msg_path: StrOrPath, folder: Folder) -> Path:
        msg_path = Path(msg_path)
        old_flags = self._parse_flags(msg_path.name)

        tmp_uniq = self._build_uniq(folder)
        LOGGER.debug('moving %r to %r', msg_path, tmp_uniq)
        shutil.copy(str(msg_path), str(tmp_uniq))

        ret = self._move_to_cur(tmp_uniq, folder, flags=old_flags)
        msg_path.unlink()
        return ret

    def clean_tmp(self, folder: Folder) -> None:
        now = time()
        for sub in folder.path.joinpath('tmp').iterdir():
            if sub.is_file() and now - sub.stat().st_mtime > TMP_CLEAN_THRESHOLD_SECS:
                sub.unlink()
