# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

from lierre.config import ConfigDict


def test_config():
    d = ConfigDict()
    assert d.get('foo', 'bar') is None
    assert d.get('foo', 'bar', default=1) == 1

    assert d.setdefault('foo', 'bar', 2) == 2
    assert d.get('foo', 'bar') == 2

    assert d.setdefault('foo', 'bar', 3) == 2
    assert d.get('foo', 'bar') == 2

    d.set('foo', 'bar', 4)
    assert d.get('foo', 'bar') == 4
