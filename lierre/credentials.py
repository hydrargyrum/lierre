
from logging import getLogger
from subprocess import check_output, CalledProcessError

from .config import CONFIG


__all__ = (
    'load', 'get_credential',
)


LOGGER = getLogger(__name__)

CREDS = {}


def load():
    CREDS.clear()
    for name, cmd in CONFIG.get('credentials', default={}).items():
        try:
            CREDS[name] = check_output(cmd, shell=True, encoding='utf-8').strip()
        except CalledProcessError:
            LOGGER.warning('could not get password for account %s', name)


def get_credential(name):
    return CREDS[name]


def list_credentials():
    return list(CREDS.keys())
