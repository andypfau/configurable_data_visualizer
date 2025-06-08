from __future__ import annotations

from ..helpers.qt_helper import QtHelper
from lib.config import Config, Sort

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
    
    
    MIME_ANY_COL = 'application/x-pivot-column'
    MIME_PLOT_COL = 'application/x-pivot-plot-column'
    MIME_SORTABLE_PLOT_COL = 'application/x-pivot-sortable-plot-column'
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
    
        def get_context_menu(self) -> QMenu|None:
            return None


    class AnyColItem(AbstractItem):

        def __init__(self, col: str):
            super().__init__()
            self.col = col
            self.setData(Qt.ItemDataRole.UserRole, col)
            self.update_item()
        
        def update_item(self):
            self.setText(self.col)
        
        def col_name(self) -> str:
            return self.col


    class PlotColItem(AbstractItem):

        def __init__(self, col: Config.PlotCol):
            super().__init__()
            self.col = col
            self.setData(Qt.ItemDataRole.UserRole, col)
            self._ui_context_menu = QMenu()
            def active_changed():
                self.col.active = self._ui_active_item.isChecked()
                self.setData(Qt.ItemDataRole.UserRole, None)
                self.setData(Qt.ItemDataRole.UserRole, self.col)
            self._ui_active_item = QtHelper.add_menuitem(self._ui_context_menu, 'Active', active_changed, checked=self.col.active)
            self.update_item()
        
        def update_item(self):
            self.setText(self.col.col)
            if self.col.active:
                self.setForeground(QtHelper.get_palette_color(QPalette.ColorRole.Text))
            else:
                self.setForeground(QtHelper.get_palette_color(QPalette.ColorRole.Dark))
        
        def col_name(self) -> str:
            return self.col.col
        
        def get_context_menu(self) -> QMenu|None:
            return self._ui_context_menu


    class FilterColItem(AbstractItem):

        def __init__(self, col: Config.Filter):
            super().__init__()
            self.col = col
            self.setData(Qt.ItemDataRole.UserRole, col)
            self.update_item()
            self._ui_context_menu = QMenu()
            def active_changed():
                self.col.active = self._ui_active_item.isChecked()
                self.setData(Qt.ItemDataRole.UserRole, None)
                self.setData(Qt.ItemDataRole.UserRole, self.col)
            self._ui_active_item = QtHelper.add_menuitem(self._ui_context_menu, 'Active', active_changed, checked=self.col.active)
            self.update_item()
        
        def update_item(self):
            self.setText(self.col.col)
            if self.col.active:
                self.setForeground(QtHelper.get_palette_color(QPalette.ColorRole.Text))
            else:
                self.setForeground(QtHelper.get_palette_color(QPalette.ColorRole.Dark))
        
        def col_name(self) -> str:
            return self.col.col
        
        def get_context_menu(self) -> QMenu|None:
            return self._ui_context_menu


    class SortablePlotColItem(AbstractItem):

        def __init__(self, col: Config.SortablePlotCol):
            super().__init__()
            self.col = col
            self.setData(Qt.ItemDataRole.UserRole, col)
            self.update_item()
            self._ui_context_menu = QMenu()
            def active_changed():
                self.col.active = self._ui_active_item.isChecked()
                self.setData(Qt.ItemDataRole.UserRole, None)
                self.setData(Qt.ItemDataRole.UserRole, self.col)
            self._ui_active_item = QtHelper.add_menuitem(self._ui_context_menu, 'Active', active_changed, checked=self.col.active)
            self.update_item()
      
        def update_item(self):
            self.setText(self.col.col)
        
        def col_name(self) -> str:
            return self.col.col
        
        def get_context_menu(self) -> QMenu|None:
            return self._ui_context_menu

    

    class ItemDelegate(QStyledItemDelegate):
        
        def paint(self, painter: QtGui.QPainter, option: QStyleOptionViewItem, index: QtCore.QModelIndex):
            item = index.data(Qt.ItemDataRole.UserRole)
            if isinstance(item, (Config.PlotCol, Config.SortablePlotCol, Config.Filter)):
                text = item.col
                text2 = None
                active = item.active
                if isinstance(item, Config.SortablePlotCol):
                    if item.sort == Sort.Asc:
                        text2 = 'Sort ↓'
                    elif item.sort == Sort.Desc:
                        text2 = 'Sort ↑'
                elif isinstance(item, Config.Filter):
                    text2 = item.as_str()
            elif isinstance(item, str):
                text = item
                text2 = None
                active = False

            painter.save()

            if option.state & QStyle.StateFlag.State_Selected:
                painter.fillRect(option.rect, option.palette.highlight())


            outline_rect = QRect(option.rect)
            outline_rect.adjust(2, 2, -2, -2)
            painter.setPen(QColorConstants.Black if active else QColorConstants.DarkGray)
            painter.setBrush(QColorConstants.Green.lighter(190) if active else QColorConstants.LightGray)
            painter.drawRoundedRect(outline_rect, 2.0, 2.0)

            text_rect = QRect(option.rect)
            text_rect.adjust(8, 2, -8, -2)
            painter.setPen(QColorConstants.Black if active else QColorConstants.DarkGray)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignTop, text)
            if text2:
                text_rect = QRect(option.rect)
                text_rect.adjust(8, 2, -8, -2)
                painter.setPen(QColorConstants.DarkGray)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignBottom, text2)

            painter.restore()


        def sizeHint(self, option: QStyleOptionViewItem, index: QtCore.QModelIndex) -> QtCore.QSize:
            if option.widget and isinstance(option.widget, QListWidget):
                available_width = option.widget.viewport().width()
            else:
                available_width = option.rect.width()
            return QSize(available_width, 40)
            
            
        
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
            self.setItemDelegate(PivotGrid.ItemDelegate())
            self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.customContextMenuRequested.connect(self.show_context_menu)
            self.model().dataChanged.connect(self.userChange)


        def get_all_items(self) -> list[PivotGrid.AbstractItem]:
            return [self.item(row) for row in range(self.count())]


        def mousePressEvent(self, event: QtGui.QMouseEvent):
            if event.button() == Qt.MouseButton.LeftButton:
                self._drag_start_pos = event.pos()
            super().mousePressEvent(event)
        

        def pack_mimedata(self, item: PivotGrid.AbstractItem) -> QMimeData:
            data = QMimeData()
            if isinstance(item, PivotGrid.PlotColItem):
                data.setData(PivotGrid.MIME_PLOT_COL, pickle.dumps(item.col))
            elif isinstance(item, PivotGrid.SortablePlotColItem):
                data.setData(PivotGrid.MIME_SORTABLE_PLOT_COL, pickle.dumps(item.col))
            elif isinstance(item, PivotGrid.FilterColItem):
                data.setData(PivotGrid.MIME_FILTER, pickle.dumps(item.col))
            else:
                data.setData(PivotGrid.MIME_ANY_COL, pickle.dumps(item.text()))
            return data


        def unpack_mimedata(self, data: QMimeData) -> PivotGrid.AbstractItem:
            if data.hasFormat(PivotGrid.MIME_ANY_COL):
                return PivotGrid.AnyColItem(pickle.loads(data.data(PivotGrid.MIME_ANY_COL)))
            elif data.hasFormat(PivotGrid.MIME_PLOT_COL):
                return PivotGrid.PlotColItem(pickle.loads(data.data(PivotGrid.MIME_PLOT_COL)))
            elif data.hasFormat(PivotGrid.MIME_SORTABLE_PLOT_COL):
                return PivotGrid.SortablePlotColItem(pickle.loads(data.data(PivotGrid.MIME_SORTABLE_PLOT_COL)))
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
                if action == Qt.DropAction.CopyAction:
                    event.setDropAction(Qt.DropAction.CopyAction)
                    event.acceptProposedAction()
                    self.setCursor(QtCore.Qt.CursorShape.DragCopyCursor)  # TODO: changing cursor shapes doesn't work as expected
                elif action == Qt.DropAction.MoveAction:
                    event.setDropAction(Qt.DropAction.MoveAction)
                    event.acceptProposedAction()
                    self.setCursor(QtCore.Qt.CursorShape.DragMoveCursor)
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
        

        def handle_drag(self, item: PivotGrid.AbstractItem) -> Qt.DropAction:
            return Qt.DropAction.IgnoreAction


        def handle_source_drop(self, item: PivotGrid.AbstractItem, row: int, move: bool):
            pass


        def handle_target_drop(self, item: PivotGrid.AbstractItem, row: int) -> bool:
            return False
        

        def show_context_menu(self, pos: QPoint):
            item = self.itemAt(pos)
            if (not item) or (not isinstance(item, PivotGrid.AbstractItem)):
                return
            menu = item.get_context_menu()
            if not menu:
                return
            menu.exec(self.mapToGlobal(pos))
        

        def make_context_menu(self, item: PivotGrid.AbstractItem) -> QMenu|None:
            return None



    class FilterColListWidget(AbstractListWidget):

        def handle_drag(self, item: PivotGrid.AbstractItem) -> Qt.DropAction:
            return Qt.DropAction.CopyAction

        def handle_source_drop(self, item: PivotGrid.AbstractItem, row: int, move: bool):
            if move:
                self.model().removeRow(row)

        def handle_target_drop(self, item: PivotGrid.AbstractItem, row: int) -> bool:
            item = PivotGrid.FilterColItem(Config.Filter(item.col_name()))
            self.insertItem(row, item)
            return True


    class PlotColListWidget(AbstractListWidget):

        def handle_drag(self, item: PivotGrid.AbstractItem) -> Qt.DropAction:
            if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier:
                return Qt.DropAction.CopyAction
            else:
                return Qt.DropAction.MoveAction

        def handle_source_drop(self, item: PivotGrid.AbstractItem, row: int, move: bool):
            if move:
                self.model().removeRow(row)

        def handle_target_drop(self, item: PivotGrid.AbstractItem, row: int) -> bool:
            item = PivotGrid.PlotColItem(Config.PlotCol(item.col_name()))
            self.insertItem(row, item)
            return True


    class SortablePlotColListWidget(AbstractListWidget):

        def handle_drag(self, item: PivotGrid.AbstractItem) -> Qt.DropAction:
            if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier:
                return Qt.DropAction.CopyAction
            else:
                return Qt.DropAction.MoveAction

        def handle_source_drop(self, item: PivotGrid.AbstractItem, row: int, move: bool):
            if move:
                self.model().removeRow(row)

        def handle_target_drop(self, item: PivotGrid.AbstractItem, row: int) -> bool:
            item = PivotGrid.SortablePlotColItem(Config.SortablePlotCol(item.col_name()))
            self.insertItem(row, item)
            return True


    class AnyColListWidget(AbstractListWidget):

        def handle_drag(self, item: PivotGrid.AbstractItem) -> Qt.DropAction:
            return Qt.DropAction.MoveAction

        def handle_source_drop(self, item: PivotGrid.AbstractItem, row: int, move: bool):
            pass  # do never remove item

        def handle_target_drop(self, item: PivotGrid.AbstractItem, row: int) -> bool:
            return True
        
        def make_context_menu(self, item: PivotGrid.AbstractItem) -> QMenu|None:
            return None  # no context menu
        

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self._all_columns: list[str] = []
        self._config = Config()

        self._ui_all_list = PivotGrid.AnyColListWidget()
        self._ui_all_list.userChange.connect(self._on_user_change)
        self._ui_x_list = PivotGrid.SortablePlotColListWidget()
        self._ui_x_list.userChange.connect(self._on_user_change)
        self._ui_y_list = PivotGrid.PlotColListWidget()
        self._ui_y_list.userChange.connect(self._on_user_change)
        self._ui_group_list = PivotGrid.SortablePlotColListWidget()
        self._ui_group_list.userChange.connect(self._on_user_change)
        self._ui_filter_list = PivotGrid.FilterColListWidget()
        self._ui_filter_list.userChange.connect(self._on_user_change)
        self._ui_color_list = PivotGrid.SortablePlotColListWidget()
        self._ui_color_list.userChange.connect(self._on_user_change)

        self.setLayout(QtHelper.layout_grid(
            [
                [
                    QtHelper.layout_v('All Columns', self._ui_all_list),
                    QtHelper.layout_v('Filter', self._ui_filter_list),
                ],
                [
                    QtHelper.layout_v('Group', self._ui_group_list),
                    QtHelper.layout_v('Color', self._ui_color_list),
                ],
                [
                    QtHelper.layout_v('X-Axis', self._ui_x_list),
                    QtHelper.layout_v('Y-Axis', self._ui_y_list),
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
            self._ui_all_list.addItem(PivotGrid.AnyColItem(col))
        
        self._ui_filter_list.clear()
        for col in self._config.filters:
            self._ui_filter_list.addItem(PivotGrid.FilterColItem(col))
        
        self._ui_group_list.clear()
        for col in self._config.cols_group:
            self._ui_group_list.addItem(PivotGrid.SortablePlotColItem(col))
        
        self._ui_x_list.clear()
        for col in self._config.cols_x:
            self._ui_x_list.addItem(PivotGrid.SortablePlotColItem(col))
        
        self._ui_y_list.clear()
        for col in self._config.cols_y:
            self._ui_y_list.addItem(PivotGrid.PlotColItem(col))
        
        self._ui_color_list.clear()
        for col in self._config.cols_color:
            self._ui_color_list.addItem(PivotGrid.SortablePlotColItem(col))


    def _on_user_change(self):
        self._config.filters.clear()
        for item in self._ui_filter_list.get_all_items():
            self._config.filters.append(item.col)

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
