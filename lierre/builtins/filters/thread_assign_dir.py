
from time import time
import mailbox
from pathlib import Path

from lierre.utils.db_ops import open_db_rw, get_db_path, get_thread_by_id
from lierre.utils.maildir_ops import MaildirPP

from ..fetchers.base import Plugin, Job


THRESHOLD = 24 * 60 * 60


class ThreadToDirPlugin(Plugin):
    def get_config(self):
        return self.config

    def set_config(self, config):
        self.config = config

    def create_job(self):
        return MoveJob()


class MoveJob(Job):
    def start(self):
        now = time()
        mailroot = get_db_path()
        box = mailbox.Maildir(mailroot)

        # TODO: folder:"" and thread:{not folder:""}?
        with open_db_rw() as db:
            for msgname in box.iterkeys():
                msg_path = Path(mailroot).joinpath(box._lookup(msgname))

                if now - msg_path.stat().st_mtime >= THRESHOLD:
                    continue

                if 'deleted' in set(db.find_message_by_filename(str(msg_path)).get_tags()):
                    continue

                try_place_in_folder(db, msg_path)

        self.finished.emit(0)


def try_place_in_folder(db, msg_path):
    root = MaildirPP()

    msg = db.find_message_by_filename(str(msg_path))

    thread = get_thread_by_id(db, msg.get_thread_id())
    for toplevel in thread.get_toplevel_messages():
        # TODO: in what case multiple toplevel messages?
        # TODO: multiple filenames for toplevel message?
        top_path = Path(toplevel.get_filename())

        if msg_path.parent == top_path.parent:
            continue

        if root.folder_from_msg(msg_path) == root.folder_from_msg(top_path):
            # maildir: one may be in 'new' and the other in 'cur'
            continue

        new_path = root.move_message(msg_path, root.folder_from_msg(top_path))

        db.add_message(str(new_path))
        db.remove_message(str(msg_path))
        break
