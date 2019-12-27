# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

from logging import getLogger
from pathlib import Path

from PyQt5.QtCore import QTimer, pyqtSlot as Slot, QThread, Qt
from lierre.utils.db_ops import open_db_rw
from lierre.utils.maildir_ops import MaildirPP
from lierre.change_watcher import WATCHER

from ..fetchers.base import Plugin, Job


LOGGER = getLogger(__name__)

TAG_DELETED = 'deleted'


class TrashingPlugin(Plugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timer = None
        self.periodic_thread = None

    def enable(self):
        WATCHER.tagMailAdded.connect(self.tagMailAdded, Qt.QueuedConnection)
        WATCHER.tagMailRemoved.connect(self.tagMailRemoved, Qt.QueuedConnection)

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
        self.config.setdefault('dry_run', True)

    def get_config(self):
        return self.config

    def create_job(self):
        return SearchTrashableJob(self.build_processor(), dry_run=self.config['dry_run'])

    # trash messages directly if tags are set by UI
    @Slot(str, str)
    def tagMailAdded(self, tag, msg_id):
        if tag != TAG_DELETED:
            return

        processor = self.build_processor()
        with open_db_rw() as db:
            for msg_path in db.find_message(msg_id).get_filenames():
                msg_path = Path(msg_path)
                LOGGER.info('deleting message %r with path %r', msg_id, msg_path)
                if not self.config['dry_run']:
                    processor.delete_message(db, msg_path)

    @Slot(str, str)
    def tagMailRemoved(self, tag, msg_id):
        if tag != TAG_DELETED:
            return

        processor = self.build_processor()
        with open_db_rw() as db:
            for msg_path in db.find_message(msg_id).get_filenames():
                msg_path = Path(msg_path)
                LOGGER.info('undeleting message %r with path %r', msg_id, msg_path)
                if not self.config['dry_run']:
                    processor.undelete_message(db, msg_path)

    # trash messages periodically if they are set by notmuch or while app is not run
    @Slot()
    def periodic_sync_deleted(self):
        self.periodic_thread = SearchTrashableThread(
            self.build_processor(), dry_run=self.config['dry_run']
        )
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
    def __init__(self, processor, *args, dry_run=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.processor = processor
        self.dry_run = dry_run

    def start(self):
        self.job = SearchTrashableThread(self.processor, dry_run=self.dry_run)
        self.job.finished.connect(self._finished)
        self.job.start()

    @Slot()
    def _finished(self):
        self.finished.emit(0)


class SearchTrashableThread(QThread):
    def __init__(self, processor, *args, dry_run=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.processor = processor
        self.dry_run = dry_run

    def run(self):
        with open_db_rw() as db:
            for msg in self.processor.find_messages_to_delete(db):
                for msg_path in msg.get_filenames():
                    msg_path = Path(msg_path)
                    LOGGER.info('deleting message %r with path %r', msg.get_message_id(), msg_path)
                    if not self.dry_run:
                        self.processor.delete_message(db, msg_path)

            for msg in self.processor.find_messages_to_undelete(db):
                for msg_path in msg.get_filenames():
                    msg_path = Path(msg_path)
                    LOGGER.info('undeleting message %r with path %r', msg.get_message_id(), msg_path)
                    if not self.dry_run:
                        self.processor.undelete_message(db, msg_path)


class TrashFolderProcessor:
    def __init__(self, box_name='Trash'):
        self.trash_box_name = box_name
        self.root = MaildirPP()
        self.trash_folder = self.root.try_get_folder([self.trash_box_name])

    def find_messages_to_delete(self, db):
        # FIXME quoting?
        qstr = 'tag:%s and not folder:%s' % (TAG_DELETED, self.trash_folder.encoded_name)
        q = db.create_query(qstr)
        return q.search_messages()

    def find_messages_to_undelete(self, db):
        # FIXME quoting?
        qstr = 'not tag:%s and folder:%s' % (TAG_DELETED, self.trash_folder.encoded_name)
        q = db.create_query(qstr)
        return q.search_messages()

    def delete_message(self, db, msg_path: Path) -> None:
        LOGGER.debug('trashing %r to %r', msg_path, self.trash_folder.path)
        new_path = self.root.move_message(msg_path, self.trash_folder)
        db.add_message(str(new_path))
        db.remove_message(str(msg_path))

    def expunge_message(self, db, msg_path: Path) -> None:
        LOGGER.error('expunging %r', msg_path)
        msg_path.unlink()
        db.remove_message(db.find_message(str(msg_path)))

    def undelete_message(self, db, msg_path: Path) -> None:
        LOGGER.error('untrashing %r to inbox', msg_path)
        new_path = self.root.move_message(msg_path, self.root.get_root())
        db.add_message(str(new_path))
        db.remove_message(str(msg_path))


class TrashFlagProcessor:
    pass
