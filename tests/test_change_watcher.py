# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

from lierre.change_watcher import diff_sorted


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
