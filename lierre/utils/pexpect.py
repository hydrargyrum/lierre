# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

from contextlib import contextmanager
from logging import getLogger
import os

from pexpect import ExceptionPexpect


LOGGER = getLogger(__name__)


def env_c_lang():
    """Get current env but locale forced to "C"."""
    new = {
        var: os.environ[var]
        for var in os.environ
        if not var.startswith('LC_')
    }
    new.pop('LANGUAGE', None)
    new['LANG'] = 'C'
    return new


def expect_get_obj(exp, patterns, **kwargs):
    """Like expect() but get the matched pattern instead of its index."""
    index = exp.expect(patterns, **kwargs)
    return patterns[index]


def close_expect(exp):
    if exp.closed:
        return

    args = [exp.command] + exp.args
    try:
        exp.close(True)
    except ExceptionPexpect:
        LOGGER.warning('command %r (pid=%s) did not terminate', args, exp.pid, exc_info=True)
    else:
        LOGGER.debug('terminated %r (pid=%s)', args, exp.pid)


@contextmanager
def closing_expect(exp):
    try:
        yield
    finally:
        close_expect(exp)
