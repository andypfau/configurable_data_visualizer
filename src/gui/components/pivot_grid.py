from __future__ import annotations

from ..helpers.qt_helper import QtHelper
from lib.config import Config

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

import pathlib
import enum
import logging
import os
import re
import pickle
import numpy as np
import tokenize, token
from typing import Callable, Optional, Union



class PivotGrid(QWidget):


    userChange = pyqtSignal()
    
    
    MIME_ANYCOL = 'application/x-pivot-column'
    MIME_PLOTCOL = 'application/x-pivot-plot-column'
    MIME_SORTCOL = 'application/x-pivot-sort-column'
    MIME_FILTER = 'application/x-pivot-filter-column'


    class AbstractItem(QListWidgetItem):

        def update_item(self):
            pass

        def col_name(self) -> str:
            raise NotImplementedError()
        
        def __eq__(self, other):
            if isinstance(other, PivotGrid.AbstractItem):
                return self.col_name() == other.col_name()
            return super().__eq__(self)


    class AnyColItem(AbstractItem):

        def __init__(self, col: str):
            super().__init__()
            self.col = col
            self.update_item()
        
        def update_item(self):
            self.setText(self.col)
        
        def col_name(self) -> str:
            return self.col


    class PlotColItem(AbstractItem):

        def __init__(self, col: Config.PlotCol):
            super().__init__()
            self.col = col
            self.update_item()
        
        def update_item(self):
            self.setText(self.col.col)
            if self.col.active:
                self.setForeground(QtHelper.get_palette_color(QPalette.ColorRole.Text))
            else:
                self.setForeground(QtHelper.get_palette_color(QPalette.ColorRole.Dark))
        
        def col_name(self) -> str:
            return self.col_name()


    class FilterColItem(AbstractItem):

        def __init__(self, col: Config.ColFilter):
            super().__init__()
            self.col = col
            self.update_item()
        
        def update_item(self):
            self.setText(self.col.col)
            if self.col.active:
                self.setForeground(QtHelper.get_palette_color(QPalette.ColorRole.Text))
            else:
                self.setForeground(QtHelper.get_palette_color(QPalette.ColorRole.Dark))
        
        def col_name(self) -> str:
            return self.col_name()


    class SortColItem(AbstractItem):

        def __init__(self, col: Config.SortCol):
            super().__init__()
            self.col = col
            self.update_item()
        
        def update_item(self):
            self.setText(self.col.col)
        
        def col_name(self) -> str:
            return self.col_name()

    
    class AbstractListWidget(QListWidget):


        userChange = pyqtSignal()


        def __init__(self, parent = None):
            super().__init__(parent)
            self._drag_start_pos: QPoint = None
            self.setDragEnabled(True)
            self.setAcceptDrops(True)
            self.setDropIndicatorShown(True)
            self.setDragDropMode(QListWidget.DragDropMode.DragDrop)
            self.setDefaultDropAction(Qt.DropAction.MoveAction | Qt.DropAction.CopyAction)
        

        def get_all_items(self) -> list[PivotGrid.AbstractItem]:
            return [self.item(row) for row in range(self.count())]


        def mousePressEvent(self, event: QtGui.QMouseEvent):
            if event.button() == Qt.MouseButton.LeftButton:
                self._drag_start_pos = event.pos()
            super().mousePressEvent(event)
        

        def pack_mimedata(self, item: QListWidgetItem) -> QMimeData:
            data = QMimeData()
            if isinstance(item, PivotGrid.PlotColItem):
                data.setData(PivotGrid.MIME_PLOTCOL, pickle.dumps(item.col))
            elif isinstance(item, PivotGrid.SortColItem):
                data.setData(PivotGrid.MIME_SORTCOL, pickle.dumps(item.col))
            elif isinstance(item, PivotGrid.FilterColItem):
                data.setData(PivotGrid.MIME_FILTER, pickle.dumps(item.col))
            elif isinstance(item, QListWidgetItem):
                data.setData(PivotGrid.MIME_ANYCOL, pickle.dumps(item.text()))
            else:
                raise ValueError()
            return data


        def unpack_mimedata(self, data: QMimeData) -> QListWidgetItem:
            if data.hasFormat(PivotGrid.MIME_ANYCOL):
                return QListWidgetItem(pickle.loads(data.data(PivotGrid.MIME_ANYCOL)))
            elif data.hasFormat(PivotGrid.MIME_PLOTCOL):
                return PivotGrid.PlotColItem(pickle.loads(data.data(PivotGrid.MIME_PLOTCOL)))
            elif data.hasFormat(PivotGrid.MIME_SORTCOL):
                return PivotGrid.SortColItem(pickle.loads(data.data(PivotGrid.MIME_SORTCOL)))
            elif data.hasFormat(PivotGrid.MIME_FILTER):
                return PivotGrid.FilterColItem(pickle.loads(data.data(PivotGrid.MIME_FILTER)))
            raise ValueError()
        

        def mouseMoveEvent(self, event: QtGui.QMouseEvent):
            if Qt.MouseButton.LeftButton in event.buttons() and self._drag_start_pos:
                if (event.pos() - self._drag_start_pos).manhattanLength() >= QApplication.startDragDistance():
                    index = self.indexAt(event.position().toPoint())
                    if not index.isValid():
                        return
                    item = self.item(index.row())
                    drag = QDrag(self)
                    drag.setMimeData(self.pack_mimedata(item))
                    result = drag.exec(Qt.DropAction.MoveAction | Qt.DropAction.CopyAction, Qt.DropAction.MoveAction)
                    self.handle_source_drop(item, index.row(), result==Qt.DropAction.MoveAction)
                    return
            super().mouseMoveEvent(event)
                

        def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
            if event.mimeData():
                item = self.unpack_mimedata(event.mimeData())
                action = self.handle_drag(item)
                event.setDropAction(action)
                if action != Qt.DropAction.IgnoreAction:
                    event.accept()
                self.setDropIndicatorShown(True)
                return
            event.ignore()


        def supportedDropActions(self) -> Qt.DropAction:
            return Qt.DropAction.MoveAction | Qt.DropAction.CopyAction
                

        def dragMoveEvent(self, event: QtGui.QDragMoveEvent):
            if event.mimeData():
                event.acceptProposedAction()
                self.setDropIndicatorShown(True)
            else:
                event.ignore()
                

        def dropEvent(self, event: QtGui.QDropEvent):
            if not event.mimeData():
                return
            
            item = self.unpack_mimedata(event.mimeData())
            index = self.indexAt(event.position().toPoint())
            row = index.row() if index.isValid() else self.count()
            if not self.handle_target_drop(item, row):
                return
            
            event.acceptProposedAction()

            self.userChange.emit()
        

        def handle_drag(self, item: QListWidgetItem) -> Qt.DropAction:
            return Qt.DropAction.IgnoreAction


        def handle_source_drop(self, item: QListWidgetItem, row: int, move: bool):
            pass


        def handle_target_drop(self, item: QListWidgetItem, row: int) -> bool:
            return False


    class FilterColListWidget(AbstractListWidget):

        def handle_drag(self, item: QListWidgetItem) -> Qt.DropAction:
            return Qt.DropAction.CopyAction

        def handle_source_drop(self, item: QListWidgetItem, row: int, move: bool):
            if move:
                self.model().removeRow(row)

        def handle_target_drop(self, item: QListWidgetItem, row: int) -> bool:
            item = PivotGrid.FilterColItem(Config.ColFilter(item.text()))
            self.insertItem(row, item)
            return True


    class PlotColListWidget(AbstractListWidget):

        def handle_drag(self, item: QListWidgetItem) -> Qt.DropAction:
            if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier:
                return Qt.DropAction.CopyAction
            else:
                return Qt.DropAction.MoveAction

        def handle_source_drop(self, item: QListWidgetItem, row: int, move: bool):
            if move:
                self.model().removeRow(row)

        def handle_target_drop(self, item: QListWidgetItem, row: int) -> bool:
            item = PivotGrid.PlotColItem(Config.PlotCol(item.text()))
            self.insertItem(row, item)
            return True


    class SortColListWidget(AbstractListWidget):

        def dropHandler(self, item: QListWidgetItem, row: int) -> bool:
            if isinstance(item, PivotGrid.PlotColItem):
                pass
            elif isinstance(item, QListWidgetItem):
                pass
            else:
                return False
            self.insertItem(row, item)
            return True


    class AnyColListWidget(AbstractListWidget):

        def handle_drag(self, item: QListWidgetItem) -> Qt.DropAction:
            return Qt.DropAction.MoveAction

        def handle_source_drop(self, item: QListWidgetItem, row: int, move: bool):
            pass

        def handle_target_drop(self, item: QListWidgetItem, row: int) -> bool:
            return True
        

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self._all_columns: list[str] = []
        self._config = Config()

        self._ui_all_list = PivotGrid.AnyColListWidget()
        self._ui_all_list.userChange.connect(self._on_user_change)
        self._ui_x_list = PivotGrid.PlotColListWidget()
        self._ui_x_list.userChange.connect(self._on_user_change)
        self._ui_y_list = PivotGrid.PlotColListWidget()
        self._ui_y_list.userChange.connect(self._on_user_change)
        self._ui_group_list = PivotGrid.PlotColListWidget()
        self._ui_group_list.userChange.connect(self._on_user_change)
        self._ui_sort_list = PivotGrid.SortColListWidget()
        self._ui_sort_list.userChange.connect(self._on_user_change)
        self._ui_filter_list = PivotGrid.FilterColListWidget()
        self._ui_filter_list.userChange.connect(self._on_user_change)
        self._ui_color_list = PivotGrid.PlotColListWidget()
        self._ui_color_list.userChange.connect(self._on_user_change)

        self.setLayout(QtHelper.layout_grid(
            [
                [
                    QtHelper.CellSpan(
                        QtHelper.layout_v('All Columns', self._ui_all_list),
                        rows=2
                    ),
                    QtHelper.layout_v('Filter', self._ui_filter_list),
                ],
                [
                    None,
                    QtHelper.layout_v('Sort', self._ui_sort_list),
                ],
                [
                    QtHelper.layout_v('Group', self._ui_group_list),
                    QtHelper.layout_v('Color', self._ui_color_list),
                ],
                [
                    QtHelper.layout_v('X', self._ui_x_list),
                    QtHelper.layout_v('Y', self._ui_y_list),
                ],
            ]
        ))

        self._update_lists()

    

    def setData(self, all_columns: list[str], config: Config):
        self._all_columns = all_columns
        self._config = config
        self._update_lists()


    def _update_lists(self):
        self._ui_all_list.clear()
        for col in sorted(self._all_columns):
            self._ui_all_list.addItem(col)
        
        self._ui_filter_list.clear()
        for col in self._config.filters:
            self._ui_filter_list.addItem(PivotGrid.FilterColItem(col))
        
        self._ui_sort_list.clear()
        for col in self._config.sort:
            self._ui_sort_list.addItem(PivotGrid.SortColItem(col))
        
        self._ui_group_list.clear()
        for col in self._config.cols_group:
            self._ui_group_list.addItem(PivotGrid.PlotColItem(col))
        
        self._ui_x_list.clear()
        for col in self._config.cols_x:
            self._ui_x_list.addItem(PivotGrid.PlotColItem(col))
        
        self._ui_y_list.clear()
        for col in self._config.cols_y:
            self._ui_y_list.addItem(PivotGrid.PlotColItem(col))
        
        self._ui_color_list.clear()
        for col in self._config.cols_color:
            self._ui_color_list.addItem(PivotGrid.PlotColItem(col))


    def _on_user_change(self):
        self._config.filters.clear()
        for item in self._ui_filter_list.get_all_items():
            self._config.filters.append(item.col)

        self._config.sort.clear()
        for item in self._ui_sort_list.get_all_items():
            self._config.sort.append(item.col)

        self._config.cols_x.clear()
        for item in self._ui_x_list.get_all_items():
            self._config.cols_x.append(item.col)

        self._config.cols_y.clear()
        for item in self._ui_y_list.get_all_items():
            self._config.cols_y.append(item.col)

        self._config.cols_color.clear()
        for item in self._ui_color_list.get_all_items():
            self._config.cols_color.append(item.col)

        self._config.cols_group.clear()
        for item in self._ui_group_list.get_all_items():
            self._config.cols_group.append(item.col)

        self.userChange.emit()
