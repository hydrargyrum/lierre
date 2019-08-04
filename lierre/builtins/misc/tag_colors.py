# this project is licensed under the WTFPLv2, see COPYING.wtfpl for details

from PyQt5.QtCore import pyqtSlot as Slot
from PyQt5.QtWidgets import (
    QColorDialog, QListWidgetItem, QWidget, QInputDialog,
)
from lierre.config import CONFIG
from lierre.ui.ui_loader import load_ui_class
from lierre.ui.models import tag_to_colors
from lierre.utils.db_ops import open_db

from ..fetchers.base import Plugin


Ui_Form = load_ui_class('tag_colors', 'Ui_Form')


class ColorConfigurer(Ui_Form, QWidget):
    def __init__(self):
        super(ColorConfigurer, self).__init__()
        self.setupUi(self)
        self._buildTags()

    @Slot()
    def on_addButton_clicked(self):
        with open_db() as db:
            all_tags = set(db.get_all_tags())
        cfg_tags = set(self.tagsList.item(i).text() for i in range(self.tagsList.count()))
        choose_tags = sorted(all_tags - cfg_tags)

        tag, ok = QInputDialog.getItem(
            self, self.tr('Tag'), self.tr('Choose a tag to configure'),
            choose_tags
        )
        if not ok:
            return

        item = QListWidgetItem(tag, self.tagsList)
        self._refreshItem(item)

    @Slot()
    def on_removeButton_clicked(self):
        item = self.tagsList.currentItem()
        if item is None:
            return

        CONFIG.get('ui', 'tag_colors', default={}).pop(item.text(), None)
        self.tagsList.takeItem(self.tagsList.row(item))

    @Slot(QListWidgetItem)
    def on_tagsList_itemActivated(self, item):
        color = QColorDialog.getColor(item.background().color(), self)
        if not color.isValid():
            # dialog cancelled
            return

        CONFIG.set('ui', 'tag_colors', item.text(), color.name())
        self._refreshItem(item)

    def _buildTags(self):
        cfg = CONFIG.get('ui', 'tag_colors', default={})

        for tag in sorted(cfg):
            item = QListWidgetItem(tag, self.tagsList)
            self._refreshItem(item)

    def _refreshItem(self, item):
        fg, bg = tag_to_colors(item.text())
        item.setBackground(bg)
        item.setForeground(fg)

    def update_config(self):
        pass


class ColorsPlugin(Plugin):
    def enable(self):
        pass

    def disable(self):
        pass

    def is_available(self):
        return True

    def get_config(self):
        return self.config

    def set_config(self, config):
        self.config = config

    def build_config_form(self):
        return ColorConfigurer()
