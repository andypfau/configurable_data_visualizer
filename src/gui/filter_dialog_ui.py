from .helpers.qt_helper import QtHelper
from .components.filter_edit import FilterEdit
from lib.config import FilterMode, ConfigFilter

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *



class FilterDialogUi(QDialog):


    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Filter')
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)

        self._ui_tabs = QTabWidget()
        
        self._ui_tab_off = QWidget()
        self._ui_tabs.addTab(self._ui_tab_off, 'Off')
        self._ui_tab_off.setLayout(QtHelper.layout_h(QtHelper.layout_v('No Filtering')))
        
        self._ui_tab_comparison = QWidget()
        self._ui_tabs.addTab(self._ui_tab_comparison, 'Comparison')
        self._ui_compare_edit = FilterEdit()
        self._ui_compare_edit.valueChanged.connect(self.on_comparison_change)
        self._ui_tab_comparison.setLayout(QtHelper.layout_v(self._ui_compare_edit, ...))
        
        self._ui_tab_selection = QWidget()
        self._ui_tabs.addTab(self._ui_tab_selection, 'Selection')
        self._ui_checks = QListWidget()
        self._ui_checks.setMinimumSize(400,500)
        self._ui_checks.itemChanged.connect(self.on_list_check)
        self._ui_checkall_btn = QtHelper.make_button(self, '+', self.on_check_all)
        self._ui_checknone_btn = QtHelper.make_button(self, '-', self.on_check_none)
        self._ui_checktoggle_btn = QtHelper.make_button(self, '~', self.on_check_toggle)
        self._ui_tab_selection.setLayout(QtHelper.layout_v(
            self._ui_checks,
            QtHelper.layout_h(self._ui_checkall_btn, self._ui_checknone_btn, self._ui_checktoggle_btn, ...)
        ))

        self.setLayout(QtHelper.layout_h(self._ui_tabs))

        self._ui_tabs.currentChanged.connect(self.on_mode_changed)
    

    def ui_show_modal(self):
        self.exec()  # modal


    def ui_set_values_and_checked(self, values: list[any], checked: list[any]):
        self._ui_checks.itemChanged.disconnect(self.on_list_check)
        self._ui_checks.clear()
        for value in values:
            text = f'{value:.12g}' if isinstance(value,float) else str(value)
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, value)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if value in checked else Qt.CheckState.Unchecked)
            self._ui_checks.addItem(item)
        self._ui_checks.itemChanged.connect(self.on_list_check)
    

    def ui_get_checked(self) -> list[any]:
        result = []
        for row in range(self._ui_checks.model().rowCount()):
            item = self._ui_checks.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                result.append(item.data(Qt.ItemDataRole.UserRole))
        return result


    def ui_set_comparison(self, value: ConfigFilter):
        self._ui_compare_edit.setValue(value)
    def ui_get_comparison(self) -> ConfigFilter:
        return self._ui_compare_edit.value()


    def ui_set_mode(self, mode: FilterMode):
        match mode:
            case FilterMode.Off: self._ui_tabs.setCurrentIndex(0)
            case FilterMode.Comparison: self._ui_tabs.setCurrentIndex(1)
            case FilterMode.Selection: self._ui_tabs.setCurrentIndex(2)
    def ui_get_mode(self) -> FilterMode:
        match self._ui_tabs.currentIndex():
            case 0: return FilterMode.Off
            case 1: return FilterMode.Comparison
            case 2: return FilterMode.Selection
        raise ValueError()


    def ui_set_col_name(self, name: str):
        self.setWindowTitle(name)
    

    # to be overriden in derived class
    def on_comparison_change(self):
        pass
    def on_check_all(self):
        pass
    def on_check_none(self):
        pass
    def on_check_toggle(self):
        pass
    def on_list_check(self):
        pass
    def on_mode_changed(self):
        pass
