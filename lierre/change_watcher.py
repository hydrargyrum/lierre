
import heapq
import itertools

from PyQt5.QtCore import (
    QObject, pyqtSignal as Signal
)


def diff_sorted(aitems, bitems, *, key=None, reverse=False):
    aitems_ = ((elem, None) for elem in aitems)
    bitems_ = ((None, elem) for elem in bitems)

    if key is None:
        def key(x):
            return x

    merged_its = heapq.merge(aitems_, bitems_, key=lambda els: key(els[0] or els[1]), reverse=reverse)
    grouped_its = itertools.groupby(merged_its, key=lambda els: els[0] or els[1])
    for v, g in grouped_its:
        g = list(g)
        assert 1 <= len(g) <= 2
        if len(g) == 1:
            yield g[0]
        else:
            yield (v, v)


def test_diff_sorted():
    assert list(diff_sorted(
        ['b', 'c', 'e'],
        ['a', 'c', 'd'],
    )) == [
        (None, 'a'),
        ('b', None),
        ('c', 'c'),
        (None, 'd'),
        ('e', None),
    ]


class ChangeWatcher(QObject):
    globalRefresh = Signal()
    tagMailAdded = Signal(str, str)
    tagMailRemoved = Signal(str, str)
    mailAdded = Signal(str)


WATCHER = ChangeWatcher()

