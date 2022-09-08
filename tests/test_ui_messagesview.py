# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

from lierre.ui.messagesview import LINK_RE


def test_link_parse():
    assert LINK_RE.findall('''
        http://foo.bar
        http://foo.bar/
        http://foo.bar/42
        http://foo.bar/42.
        http://foo.bar/42.html
        <http://foo.bar/42.html>
        [markdown](http://foo.bar/42.html)
        http://foo.bar/42%25.html
        http://qu:ux@foo.bar/~grault/42.html;param?k=k&v=v+v#yes=
    ''') == '''
        http://foo.bar
        http://foo.bar/
        http://foo.bar/42
        http://foo.bar/42
        http://foo.bar/42.html
        http://foo.bar/42.html
        http://foo.bar/42.html
        http://foo.bar/42%25.html
        http://qu:ux@foo.bar/~grault/42.html;param?k=k&v=v+v#yes=
    '''.split()
