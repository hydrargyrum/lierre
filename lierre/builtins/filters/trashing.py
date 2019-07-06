
from logging import getLogger
from pathlib import Path

from PyQt5.QtCore import QTimer, pyqtSlot as Slot, QThread
from lierre.utils.db_ops import open_db_rw, get_db_path
from lierre.utils.box_ops import (
    move_to_mailbox, get_box_path, subpath_to_maildir_name,
)
from lierre.change_watcher import WATCHER

from ..fetchers.base import Plugin, Job


LOGGER = getLogger(__name__)


class TrashingPlugin(Plugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timer = None
        self.periodic_thread = None

    def enable(self):
        WATCHER.tagMailAdded.connect(self.tagMailAdded)
        WATCHER.tagMailRemoved.connect(self.tagMailRemoved)

        self.timer = QTimer(parent=self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.periodic_sync_deleted)
        self.timer.setInterval(60000)
        self.timer.start()

    def disable(self):
        WATCHER.tagMailAdded.disconnect(self.tagMailAdded)
        WATCHER.tagMailRemoved.disconnect(self.tagMailRemoved)
        if self.periodic_thread:
            self.periodic_thread.finished.disconnect(self.timer.start)
        self.timer.stop()
        self.timer = None

    def set_config(self, config):
        self.config = config

    def get_config(self):
        return self.config

    def create_job(self):
        return SearchTrashableJob(self.build_processor())

    # trash messages directly if tags are set by UI
    @Slot(str, str)
    def tagMailAdded(self, tag, msg_id):
        if tag != 'deleted':
            return

        processor = self.build_processor()
        with open_db_rw() as db:
            for msg_path in db.find_message(msg_id).get_filenames():
                msg_path = Path(msg_path)
                LOGGER.info('deleting message %r with path %r', msg_id, msg_path)
                processor.delete_message(db, msg_path)

    @Slot(str, str)
    def tagMailRemoved(self, tag, msg_id):
        if tag != 'deleted':
            return

        processor = self.build_processor()
        with open_db_rw() as db:
            for msg_path in db.find_message(msg_id).get_filenames():
                msg_path = Path(msg_path)
                LOGGER.info('undeleting message %r with path %r', msg_id, msg_path)
                processor.undelete_message(db, msg_path)

    # trash messages periodically if they are set by notmuch or while app is not run
    @Slot()
    def periodic_sync_deleted(self):
        self.periodic_thread = SearchTrashableThread(self.build_processor())
        self.periodic_thread.finished.connect(self.timer.start)
        self.timer.stop()
        self.periodic_thread.start()

    # TODO auto-expunge?
    # TODO how to expunge user-manually?

    def build_processor(self):
        if self.config.get('trash_type', 'folder') == 'folder':
            return TrashFolderProcessor(self.config.get('trash_box_name', 'Trash'))
        assert 0


class SearchTrashableJob(Job):
    def __init__(self, processor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.processor = processor

    def start(self):
        self.job = SearchTrashableThread(self.processor)
        self.job.finished.connect(self._finished)
        self.job.start()

    @Slot()
    def _finished(self):
        self.finished.emit(0)


class SearchTrashableThread(QThread):
    def __init__(self, processor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.processor = processor

    def run(self):
        with open_db_rw() as db:
            for msg in self.processor.find_messages_to_delete(db):
                for msg_path in msg.get_filenames():
                    msg_path = Path(msg_path)
                    LOGGER.info('deleting message %r with path %r', msg.get_message_id(), msg_path)
                    self.processor.delete_message(db, msg_path)

            for msg in self.processor.find_messages_to_undelete(db):
                for msg_path in msg.get_filenames():
                    msg_path = Path(msg_path)
                    LOGGER.info('undeleting message %r with path %r', msg.get_message_id(), msg_path)
                    self.processor.undelete_message(db, msg_path)


class TrashFolderProcessor:
    def __init__(self, box_name='Trash'):
        self.trash_box_name = box_name

    def find_messages_to_delete(self, db):
        # FIXME quoting?
        qstr = 'tag:deleted and not folder:%s' % subpath_to_maildir_name(self.trash_box_name)
        q = db.create_query(qstr)
        return q.search_messages()

    def find_messages_to_undelete(self, db):
        # FIXME quoting?
        qstr = 'not tag:deleted and folder:%s' % subpath_to_maildir_name(self.trash_box_name)
        q = db.create_query(qstr)
        return q.search_messages()

    def delete_message(self, db, msg_path):
        trash_path = get_box_path(self.trash_box_name)
        LOGGER.debug('trashing %r to %r', msg_path, trash_path)
        move_to_mailbox(msg_path, trash_path)

    def expunge_message(self, db, msg_path):
        LOGGER.error('expunging %r', msg_path)
        msg_path.unlink()
        db.remove_message(db.find_message(str(msg_path)))

    def undelete_message(self, db, msg_path):
        LOGGER.error('untrashing %r to inbox', msg_path)
        move_to_mailbox(msg_path, get_db_path())


class TrashFlagProcessor:
    pass
