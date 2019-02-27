
from PyQt5.QtWidgets import QDialog

from .ui_loader import load_ui_class


Ui_Dialog = load_ui_class('tag_editor', 'Ui_Dialog')


class TagEditor(Ui_Dialog, QDialog):
    def __init__(self, *args, **kwargs):
        super(TagEditor, self).__init__(*args, **kwargs)
        self.setupUi(self)

    def setCheckedTags(self, tags, semi=()):
        self.chooser.setCheckedTags(tags, semi)

    def checkedTags(self):
        return self.chooser.checkedTags()

