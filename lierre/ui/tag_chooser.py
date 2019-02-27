
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import (
    QSortFilterProxyModel, Qt, pyqtSlot as Slot, QItemSelectionModel,
)
from lierre.utils.db_ops import open_db

from .models import CheckableTagsListModel
from .ui_loader import load_ui_class


Ui_Form = load_ui_class('tag_chooser', 'Ui_Form')


class TagChooser(Ui_Form, QWidget):
    def __init__(self, *args, **kwargs):
        super(TagChooser, self).__init__(*args, **kwargs)
        self.setupUi(self)

        with open_db() as db:
            self.tags_model = CheckableTagsListModel(db, parent=self)

            self.filter_model = QSortFilterProxyModel(self)
            self.filter_model.setSourceModel(self.tags_model)

            self.tagsList.setModel(self.filter_model)

        self.filterEdit.textEdited.connect(self.tags_model.setNewTagItem)
        self.filterEdit.textEdited.connect(self.filter_model.setFilterFixedString)
        self.filterEdit.textEdited.connect(self.selectAtLeastOne)
        self.filterEdit.installEventFilter(self)

        self.selectAtLeastOne()

    def setCheckedTags(self, tags, semi=()):
        self.tags_model.set_checked(tags, semi)

    def checkedTags(self):
        return self.tags_model.get_checked()

    @Slot()
    def selectAtLeastOne(self):
        if not self.tagsList.selectionModel().hasSelection():
            self.tagsList.selectionModel().setCurrentIndex(
                self.filter_model.index(0, 0),
                QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
            )

    def eventFilter(self, target, event):
        if target is not self.filterEdit:
            return super(TagChooser, self).eventFilter(target, event)

        elif event.type() != event.KeyPress:
            return False
        elif event.key() in (Qt.Key_Up, Qt.Key_Down):
            self.tagsList.event(event)
            return True
        elif event.key() == Qt.Key_Space:
            self.tagsList.event(event)
            return True
        return False
