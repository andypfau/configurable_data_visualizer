from .helpers.qt_helper import QtHelper

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

import pathlib



class FilesWindowUi(QMainWindow):


    class PathItem(QStandardItem):

        def __init__(self, path: pathlib.Path):
            super().__init__()
            self.path = path
            self.setText(path.name)
            self.setData(path,Qt.ItemDataRole.UserRole)


    def __init__(self):
        super().__init__()
        self.setWindowTitle('Configurable Data Visualizer')

        self._ui_path_edit = QLineEdit()
        self._ui_path_edit.textChanged.connect(self.on_input_change)
        self._ui_glob_edit = QLineEdit()
        self._ui_glob_edit.textChanged.connect(self.on_input_change)
        self._ui_include_rex_edit = QLineEdit()
        self._ui_include_rex_edit.textChanged.connect(self.on_input_change)
        self._ui_exclude_rex_edit = QLineEdit()
        self._ui_exclude_rex_edit.textChanged.connect(self.on_input_change)
        self._ui_files_list = QListView()
        self._ui_files_model = QStandardItemModel()
        self._ui_files_list.setModel(self._ui_files_model)
        self._ui_files_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._ui_files_list.setStyleSheet(f'''
            QListView::item:selected {{
                background-color: {QPalette().color(QPalette.ColorRole.Highlight).name()}; 
                color: {QPalette().color(QPalette.ColorRole.HighlightedText).name()}; 
            }}
        ''')
        self._ui_plot_button = QtHelper.make_button(self, 'Plot', self.on_plot)
        self._ui_plot_button.setMinimumSize(150, 40)
        self._ui_plot_button.setAutoDefault(True)

        self.setCentralWidget(QtHelper.layout_widget_v(
            QtHelper.layout_h('Directory:', self._ui_path_edit),
            QtHelper.layout_h('Pattern:', self._ui_glob_edit),
            QtHelper.layout_h('Regex Include:', self._ui_include_rex_edit, '/ Exclude:', self._ui_exclude_rex_edit),
            self._ui_files_list,
            QtHelper.layout_h(self._ui_plot_button, ...),
        ))

        self.resize(600, 800)
    

    def ui_set_parameters(self, directory: str, pattern: str, rex_in: str, rex_ex: str):
        self._ui_path_edit.textChanged.disconnect(self.on_input_change)
        self._ui_glob_edit.textChanged.disconnect(self.on_input_change)
        self._ui_include_rex_edit.textChanged.disconnect(self.on_input_change)
        self._ui_exclude_rex_edit.textChanged.disconnect(self.on_input_change)

        self._ui_path_edit.setText(directory)
        self._ui_glob_edit.setText(pattern)
        self._ui_include_rex_edit.setText(rex_in)
        self._ui_exclude_rex_edit.setText(rex_ex)

        self._ui_path_edit.textChanged.connect(self.on_input_change)
        self._ui_glob_edit.textChanged.connect(self.on_input_change)
        self._ui_include_rex_edit.textChanged.connect(self.on_input_change)
        self._ui_exclude_rex_edit.textChanged.connect(self.on_input_change)


    def ui_get_parameters(self) -> tuple[str,str,str,str]:
        return self._ui_path_edit.text(), self._ui_glob_edit.text(), self._ui_include_rex_edit.text(), self._ui_exclude_rex_edit.text()


    def ui_set_files(self, files: list[pathlib.Path], selected: list[pathlib.Path]):
        self._ui_files_model.clear()
        selections = []
        for i,path in enumerate(files):
            self._ui_files_model.appendRow(FilesWindowUi.PathItem(path))
            if path in selected:
                selections.append(QItemSelection(self._ui_files_list.model().index(i,0), self._ui_files_list.model().index(i,0)))
        for selection in selections:
            self._ui_files_list.selectionModel().select(selection, QItemSelectionModel.SelectionFlag.Select)
        self._ui_files_list.scrollToTop()


    def ui_get_selected_files(self) -> list[pathlib.Path]:
        result = []
        for index in self._ui_files_list.selectionModel().selectedRows(0):
            item: FilesWindowUi.PathItem = self._ui_files_model.itemFromIndex(index)
            result.append(item.path)
        return result


    def on_input_change(self):
        pass
    def on_plot(self):
        pass
