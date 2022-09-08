# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

from lierre.utils.maildir_ops import encode_maildir_name, decode_maildir_name


def test_maildir_encodings():
    assert encode_maildir_name('Rés.umé') == 'R&AOk-s&AC4-um&AOk-'
    assert 'Rés.umé' == decode_maildir_name('R&AOk-s&AC4-um&AOk-')
