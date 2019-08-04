# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

from configparser import ConfigParser
from collections import deque
from contextlib import contextmanager
import email
import email.policy
import gc
import re

import notmuch
from PyQt5.QtCore import (
    QObject, QBasicTimer, pyqtSignal as Signal
)
from lierre.config import get_notmuch_config_path
try:
    from html2text import HTML2Text
    HAS_HTML2TEXT = True
except ImportError:
    HAS_HTML2TEXT = False


def get_thread_by_id(db, id):
    q = db.create_query('thread:%s' % id)
    q.set_omit_excluded(q.EXCLUDE.FALSE)

    it = q.search_threads()
    thr = next(iter(it), None)
    return thr


def iter_thread_messages(thread):
    def _iter(msg):
        yield msg
        for sub in msg.get_replies():
            yield from _iter(sub)

    for msg in thread.get_toplevel_messages():
        yield from _iter(msg)


class Database(notmuch.Database):
    @staticmethod
    def _get_excluded_tags():
        try:
            with open(get_notmuch_config_path()) as fd:
                cfg = ConfigParser(interpolation=None)
                cfg.read_file(fd)
                return list(filter(None, cfg.get('search', 'exclude_tags', fallback='').split(';')))
        except OSError:
            return []

    def create_query(self, querystring):
        query = super(Database, self).create_query(querystring)

        for tag in self._get_excluded_tags():
            query.exclude_tag(tag)

        return query


@contextmanager
def open_db():
    try:
        with Database(mode=notmuch.Database.MODE.READ_ONLY) as db:
            yield db
    finally:
        # WTF: collecting now makes python to free Thread then Threads.
        # Omitting it can cause python to free Threads then Thread (segfault!)
        # This happens more when build_thread_tree is used.
        gc.collect()


@contextmanager
def open_db_rw():
    try:
        with Database(mode=notmuch.Database.MODE.READ_WRITE) as db:
            yield db
    finally:
        gc.collect()


def get_db_path():
    return notmuch.Database()._get_user_default_db()


class ExcerptBuilder(QObject):
    PROPERTY = 'x-lierre-excerpt'

    def __init__(self, *args, **kwargs):
        super(ExcerptBuilder, self).__init__(*args, **kwargs)
        self.queue = deque()
        self.timer = QBasicTimer()

    def getOrBuild(self, message_id):
        with open_db() as db:
            message = db.find_message(message_id)
            filename = message.get_filename()
            value = message.get_property(self.PROPERTY)
            if value is not None:
                return value

        self._queueMail((message_id, filename))

    def _queueMail(self, item):
        self.queue.append(item)
        if not self.timer.isActive():
            self.timer.start(0, self)

    def _getExcerptPlainText(self, pymessage):
        body = pymessage.get_body(('plain',))

        if body is not None:
            text = body.get_content()
            text = re.sub(r'^>.*$', '', text, flags=re.MULTILINE)
            return text

    def _getExcerptHtml(self, pymessage):
        body = pymessage.get_body(('html',))

        if body is not None:
            text = body.get_content()
            converter = HTML2Text()
            converter.skip_internal_links = True
            converter.unicode_snob = True
            converter.ignore_tables = True
            converter.ignore_images = True
            return converter.handle(text)

    def timerEvent(self, ev):
        if ev.timerId() != self.timer.timerId():
            super(ExcerptBuilder, self).timerEvent(ev)
            return

        message_id, filename = self.queue.popleft()

        if not self.queue:
            self.timer.stop()

        with open(filename, 'rb') as fp:
            pymessage = email.message_from_binary_file(fp, policy=email.policy.default)

        text = self._getExcerptPlainText(pymessage)
        if text is None:
            if HAS_HTML2TEXT:
                text = self._getExcerptHtml(pymessage)
            else:
                return
        if not text:
            text = ''

        text = re.sub(r'\s+', ' ', text)
        text = text[:100]

        with open_db_rw() as db:
            message = db.find_message(message_id)
            message.add_property(self.PROPERTY, text)
            self.builtExcerpt.emit(message_id, text)

    builtExcerpt = Signal(str, str)


EXCERPT_BUILDER = ExcerptBuilder()


UNTOUCHABLE_TAGS = frozenset({'attachment', 'signed', 'encrypted', 'passed', 'replied'})
