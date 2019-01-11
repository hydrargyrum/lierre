
from collections import deque
import email
import email.policy
import re

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import (
    QObject, QBasicTimer, pyqtSignal as Signal
)


def get_thread_by_id(db, id):
    q = db.create_query('thread:%s' % id)
    it = q.search_threads()
    thr = list(it)[0]
    return thr


def iter_thread_messages(thread):
    def _iter(msg):
        yield msg
        for sub in msg.get_replies():
            yield from _iter(sub)

    for msg in thread.get_toplevel_messages():
        yield from _iter(msg)


class ExcerptBuilder(QObject):
    PROPERTY = 'x-lierre-excerpt'

    def __init__(self, *args, **kwargs):
        super(ExcerptBuilder, self).__init__(*args, **kwargs)
        self.queue = deque()
        self.timer = QBasicTimer()

    def getOrBuild(self, filename):
        app = QApplication.instance()
        message = app.db.find_message_by_filename(filename)
        value = message.get_property(self.PROPERTY)
        if value is not None:
            return value

        self._queueMail(filename)

    def _queueMail(self, filename):
        self.queue.append(filename)
        if not self.timer.isActive():
            self.timer.start(0, self)

    def timerEvent(self, ev):
        if ev.timerId() != self.timer.timerId():
            super(ExcerptBuilder, self).timerEvent(ev)
            return

        filename = self.queue.popleft()

        if not self.queue:
            self.timer.stop()

        with open(filename, 'rb') as fp:
            pymessage = email.message_from_binary_file(fp, policy=email.policy.default)
        text = pymessage.get_body('plain').get_content()

        text = re.sub(r'^>.*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'\s+', ' ', text)[:100]

        app = QApplication.instance()
        message = app.db.find_message_by_filename(filename)
        message.add_property(self.PROPERTY, text)
        self.builtExcerpt.emit(filename, text)

    builtExcerpt = Signal(str, str)


EXCERPT_BUILDER = ExcerptBuilder()
