

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
