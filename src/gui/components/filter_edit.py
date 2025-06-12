from __future__ import annotations

from ..helpers.qt_helper import QtHelper
from lib.config import ConfigFilter
from lib.lock import Lock

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
import pathlib
import os
import enum



class FilterEdit(QLineEdit):

    valueChanged = pyqtSignal()

    def __init__(self, parent: QWidget = None, value: ConfigFilter = ConfigFilter()):
        super().__init__(parent)
        self.setMinimumWidth(150)
        self._event_lock = Lock(initially_locked=True)
        self._edit_in_progress = False
        self._value = value
        
        self.setPlaceholderText('Enter filter expression...')
        self.setToolTip('Examples:\n  "= 42"\n  "!= 0"\n  "<=100"\n  "10...20"\n  "! -5...+5"')
        
        self._update_text_from_value()
        
        self.textChanged.connect(self._on_text_changed)
        
        self._event_lock.force_unlock()
    

    def keyPressEvent(self, event: QtGui.QKeyEvent|None):
        self._edit_in_progress = True
        if event:
            if event.key() == Qt.Key.Key_Escape:
                self._on_escape_pressed()
            elif event.key() == Qt.Key.Key_Return:
                self._on_return_pressed()
        return super().keyPressEvent(event)

    
    def focusOutEvent(self, event: QtGui.QFocusEvent|None):
        self._edit_in_progress = False
        self._update_text_from_value()
        return super().focusOutEvent(event)
    

    def _update_text_from_value(self):
        with self._event_lock:
            self.setText(self._value.format_comparison())
            QtHelper.indicate_error(self, False)


    def blank(self) -> bool:
        return self._blank
    def setBlank(self, value: bool):
        self._blank = value
        if self.hasFocus() and self._edit_in_progress:
            return  # user is entering text -> do not overwrite user-input
        self._update_text_from_value()


    def value(self) -> ConfigFilter:
        return self._value
    def setValue(self, value: ConfigFilter):
        self._value = value
        if self.hasFocus() and self._edit_in_progress:
            return  # user is entering text -> do not overwrite user-input
        self._update_text_from_value()

    
    def _on_escape_pressed(self):
        self._edit_in_progress = False
        self._update_text_from_value()

    
    def _on_return_pressed(self):
        self._edit_in_progress = False
        if self.isReadOnly():
            return
        
        # was already parsed when text was changed
        self._update_text_from_value()
        self.selectAll()

    
    def _on_text_changed(self):
        if self.isReadOnly():
            return

        try:
            old_value = self._value.value
            self._value.parse_comparison(self.text())
            QtHelper.indicate_error(self, False)
            if self._value == old_value:
                return
            if not self._event_lock.locked:
                self.valueChanged.emit()
        except Exception as ex:
            QtHelper.indicate_error(self, True)



    def _on_value_changed_externally(self, *args, **kwargs):
        if self.hasFocus() and self._edit_in_progress:
            return  # user is entering text -> do not overwrite user-input
        self._update_text_from_value()
