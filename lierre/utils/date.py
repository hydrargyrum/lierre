# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

import datetime


def locale_datetime(dt):
    if isinstance(dt, (int, float)):
        dt = datetime.datetime.fromtimestamp(dt)

    return dt.strftime('%c')


def short_datetime(dt):
    if isinstance(dt, (int, float)):
        dt = datetime.datetime.fromtimestamp(dt)

    now = datetime.datetime.now()
    if now.date() == dt.date():
        return dt.strftime('%X')
    return dt.strftime('%c')

