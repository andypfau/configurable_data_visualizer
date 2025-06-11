from __future__ import annotations

from ..helpers.qt_helper import QtHelper
from ..filter_dialog import FilterDialog
from lib.config import Config, Sort, ConfigColumnSetup, ConfigFilter, FilterMode, ColumnRole, ColumnSwitch

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


    class ColumnItem(QListWidgetItem):


        def __init__(self, col: str, config: Config, role: ColumnRole, parent_dialog: QWidget):
            super().__init__()
            self.col = col
            self._config = config
            self._role = role
            self._parent_dialog = parent_dialog

            self._ui_context_menu = QMenu()
            self._add_contextmenu_items_at_beginning()
            def active_changed():
                self._config.set_role(self.col, self._role, self._ui_active_item.isChecked())
                self._update_data()
            def sort_asc_changed():
                self._setup().sort = Sort.Asc if self._ui_sort_asc.isChecked() else Sort.Off
                self._ui_sort_desc.setChecked(False)
                self._update_data()
            def sort_desc_changed():
                self._setup().sort = Sort.Desc if self._ui_sort_desc.isChecked() else Sort.Off
                self._ui_sort_asc.setChecked(False)
                self._update_data()
            def color_changed():
                self._setup().as_color = self._ui_color.isChecked()
                self._update_data()
            def style_changed():
                self._setup().as_style = self._ui_color.isChecked()
                self._update_data()
            def size_changed():
                self._setup().as_size = self._ui_color.isChecked()
                self._update_data()
            def filter_edit():
                FilterDialog.show_dialog(self._config, self.col, self._parent_dialog)
                self._update_data()
            
            if self._role != ColumnRole.AllColumns:
                self._ui_active_item = QtHelper.add_menuitem(self._ui_context_menu, 'Active', active_changed, checkable=True)
                self._ui_context_menu.addSeparator()
            self._ui_sort_asc = QtHelper.add_menuitem(self._ui_context_menu, 'Filter...', filter_edit)
            self._ui_context_menu.addSeparator()
            self._ui_sort_asc = QtHelper.add_menuitem(self._ui_context_menu, 'Sort Ascending', sort_asc_changed, checkable=True)
            self._ui_sort_desc = QtHelper.add_menuitem(self._ui_context_menu, 'Sort Descending', sort_desc_changed, checkable=True)
            self._ui_context_menu.addSeparator()
            self._ui_color = QtHelper.add_menuitem(self._ui_context_menu, 'Use for Color', color_changed, checkable=True)
            self._ui_style = QtHelper.add_menuitem(self._ui_context_menu, 'Use for Style', style_changed, checkable=True)
            self._ui_size = QtHelper.add_menuitem(self._ui_context_menu, 'Use for Size', size_changed, checkable=True)
            
            self._update_data()
        
        def _add_contextmenu_items_at_beginning(self):
            pass

        def _setup(self) -> ConfigColumnSetup:
            return self._config.find_setup(self.col)

        def _update_data(self):
            # a change in the user-role data will trigger a re-draw
            self.setData(Qt.ItemDataRole.UserRole, (self.col, hash(self._setup())))
        
        def context_menu(self) -> QMenu|None:
            if self._role != ColumnRole.AllColumns:
                self._ui_active_item.setChecked(self._config.has_role(self.col, self._role))
            self._ui_sort_asc.setChecked(self._setup().sort==Sort.Asc)
            self._ui_sort_desc.setChecked(self._setup().sort==Sort.Desc)
            self._ui_color.setChecked(self._setup().as_color)
            self._ui_style.setChecked(self._setup().as_style)
            self._ui_size.setChecked(self._setup().as_size)

            return self._ui_context_menu


    class ItemPaintDelegate(QStyledItemDelegate):

        def __init__(self, config: Config, role: ColumnRole):
            self._config = config
            self._role = role
            super().__init__()

        def set_config(self, config: Config):
            self._config = config
        
        def paint(self, painter: QtGui.QPainter, option: QStyleOptionViewItem, index: QtCore.QModelIndex):
            (col, _) = index.data(Qt.ItemDataRole.UserRole)
            setup = self._config.find_setup(col)

            text = setup.col
            activatable = self._role != ColumnRole.AllColumns
            active = activatable and (self._config.has_role(col, self._role))
            inactive = activatable and (not self._config.has_role(col, self._role))
            error = setup.error
            text2_items = []
            filter_str = setup.filter.format()
            if filter_str:
                MAX_LEN = 25
                if len(filter_str) > MAX_LEN:
                    filter_str = filter_str[:MAX_LEN-1] + '…'
                text2_items.append(filter_str)
            if setup.sort == Sort.Asc:
                text2_items.append('↓')
            elif setup.sort == Sort.Desc:
                text2_items.append('↑')
            usages = []
            if self._config.has_role(col, ColumnRole.Group):
                usages.append('G')
            if self._config.has_role(col, ColumnRole.X):
                usages.append('X')
            if self._config.has_role(col, ColumnRole.Y):
                usages.append('Y')
            if setup.as_color:
                usages.append('C')
            if setup.as_size:
                usages.append('S')
            if setup.as_style:
                usages.append('T')
            if len(usages) > 0:
                text2_items.append(''.join(usages))
            text2 = ' • '.join(text2_items)

            painter.save()

            if option.state & QStyle.StateFlag.State_Selected:
                painter.fillRect(option.rect, option.palette.highlight())

            outline_rect = QRect(option.rect)
            outline_rect.adjust(2, 2, -2, -2)
            painter.setPen(QColorConstants.DarkGray if inactive else QColorConstants.Black)
            if error:
                painter.setBrush(QColorConstants.Yellow.lighter(125))
            elif active:
                painter.setBrush(QColorConstants.Green.lighter(190))
            elif inactive:
                painter.setBrush(QColorConstants.LightGray)
            else:
                painter.setBrush(QColorConstants.White)
            painter.drawRoundedRect(outline_rect, 2.0, 2.0)

            text_rect = QRect(option.rect)
            text_rect.adjust(8, 2, -8, -2)
            painter.setPen(QColorConstants.DarkGray if inactive else QColorConstants.Black)
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
            
        
    class ColumnListWidget(QListWidget):

        
        MIME_COLUMN = 'application/x-pivot-column'


        userChange = pyqtSignal(str)


        def __init__(self, config: Config, role: ColumnRole, parent_dialog: QWidget):
            self._config = config
            self._role = role
            self._parent_dialog = parent_dialog

            super().__init__()

            self._drag_start_pos: QPoint = None
            self.setDragEnabled(True)
            self.setAcceptDrops(True)
            self.setDropIndicatorShown(True)
            self.setDragDropMode(QListWidget.DragDropMode.DragDrop)
            self.setDefaultDropAction(Qt.DropAction.MoveAction | Qt.DropAction.CopyAction)

            self._paint_delegate = PivotGrid.ItemPaintDelegate(config, role)
            self.setItemDelegate(self._paint_delegate)
            self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.customContextMenuRequested.connect(self.show_context_menu)
            self.model().dataChanged.connect(self._on_data_changed)
        

        def _on_data_changed(self, topLeft: QModelIndex, bottomRight: QModelIndex, roles: int):
            if Qt.ItemDataRole.UserRole not in roles:
                return
            (col, _) = self.model().itemData(topLeft)[Qt.ItemDataRole.UserRole]
            self.userChange.emit(col)
        

        def set_config(self, config: Config):
            self._config = config
            self._paint_delegate.set_config(config)


        def get_all_items(self) -> list[PivotGrid.ColumnItem]:
            return [self.item(row) for row in range(self.count())]


        def mousePressEvent(self, event: QtGui.QMouseEvent):
            if event.button() == Qt.MouseButton.LeftButton:
                self._drag_start_pos = event.pos()
            super().mousePressEvent(event)
        

        def pack_mimedata(self, item: PivotGrid.ColumnItem) -> QMimeData:
            data = QMimeData()
            data.setData(PivotGrid.ColumnListWidget.MIME_COLUMN, pickle.dumps(item.col))
            return data


        def unpack_mimedata(self, data: QMimeData) -> PivotGrid.ColumnItem:
            if data.hasFormat(PivotGrid.ColumnListWidget.MIME_COLUMN):
                col = pickle.loads(data.data(PivotGrid.ColumnListWidget.MIME_COLUMN))
                return PivotGrid.ColumnItem(col, self._config, self._role, self._parent_dialog)
            return None
        

        def mouseMoveEvent(self, event: QtGui.QMouseEvent):
            if Qt.MouseButton.LeftButton in event.buttons() and self._drag_start_pos:
                if (event.pos() - self._drag_start_pos).manhattanLength() >= QApplication.startDragDistance():
                    index = self.indexAt(event.position().toPoint())
                    if not index.isValid():
                        return
                    item = self.item(index.row())
                    if not isinstance(item, PivotGrid.ColumnItem):
                        return
                    
                    drag = QDrag(self)
                    drag.setMimeData(self.pack_mimedata(item))
                    
                    pixmap = QPixmap(QSize(90, 25))
                    pixmap.fill(QColorConstants.Transparent)
                    painter = QPainter(pixmap)
                    painter.setPen(QColorConstants.DarkGray)
                    painter.setBrush(QColorConstants.White)
                    painter.drawRoundedRect(QRect(0, 0, 89, 24), 3, 3)
                    painter.end()
                    drag.setPixmap(pixmap)

                    result = drag.exec(Qt.DropAction.MoveAction | Qt.DropAction.CopyAction, Qt.DropAction.MoveAction)
                    if result == Qt.DropAction.IgnoreAction:
                        return
                    self.handle_source_drop(item, result==Qt.DropAction.MoveAction, internal=drag.target()==self)
                    self.userChange.emit(item.col)
                    return
            super().mouseMoveEvent(event)
                

        def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
            if event.mimeData():
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    # print('Requesting copy')
                    event.setDropAction(Qt.DropAction.CopyAction)
                    event.accept()
                    # self.setCursor(QtCore.Qt.CursorShape.DragCopyCursor)  # TODO: changing cursor shapes doesn't work as expected
                else:
                    # print('Requesting move')
                    event.setDropAction(Qt.DropAction.MoveAction)
                    event.accept()
                    # self.setCursor(QtCore.Qt.CursorShape.DragMoveCursor)
                return
            event.ignore()
                

        def dragMoveEvent(self, event: QtGui.QDragMoveEvent):
            return self.dragEnterEvent(event)
                

        def dropEvent(self, event: QtGui.QDropEvent):
            # self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)

            if not event.mimeData():
                return
            item = self.unpack_mimedata(event.mimeData())
            if not item:
                event.ignore()
                return

            self.handle_target_drop(item, event.source(), event.position().toPoint())
            
            event.acceptProposedAction()
        
        def handle_source_drop(self, item: PivotGrid.ColumnItem, move: bool, internal: bool):
            # note that this is executed *after* handle_target_drop()
            

            if self._role == ColumnRole.AllColumns:
                # item was moved *out of* the all-columns box; no action required, as the list remains stable
                # TODO: should I maybe allow re-ordering?
                return

            def remove_role():
                self._config.set_role(item.col, self._role, False)

            def delete_item():
                index = self.indexFromItem(item)
                if index.isValid():
                    self.model().removeRow(index.row())
            
            if internal:
                if move:
                    delete_item()
            else:
                remove_role()
                if move:
                    delete_item()
        

        def handle_target_drop(self, item: PivotGrid.ColumnItem, source: QObject|None, point: QPoint):
            # note that this is executed *before* handle_source_drop()
            
            if self._role == ColumnRole.AllColumns:
                # item was moved *into* the all-columns box; no action required, as the list remains stable
                return
            
            self._config.set_role(item.col, self._role, True)
            
            index = self.indexAt(point)
            if index.isValid():
                self.insertItem(index.row(), item)
            else:
                self.addItem(item)

        def show_context_menu(self, pos: QPoint):
            item = self.itemAt(pos)
            if (not item) or (not isinstance(item, PivotGrid.ColumnItem)):
                return
            menu = item.context_menu()
            if not menu:
                return
            menu.exec(self.mapToGlobal(pos))
        

    def __init__(self, parent_dialog: QWidget):
        self._parent_dialog = parent_dialog
        super().__init__()

        self._config = Config()

        self._ui_all_list = PivotGrid.ColumnListWidget(self._config, ColumnRole.AllColumns, self._parent_dialog)
        self._ui_all_list.userChange.connect(self._on_user_change)
        self._ui_group_list = PivotGrid.ColumnListWidget(self._config, ColumnRole.Group, self._parent_dialog)
        self._ui_group_list.userChange.connect(self._on_user_change)
        self._ui_x_list = PivotGrid.ColumnListWidget(self._config, ColumnRole.X, self._parent_dialog)
        self._ui_x_list.userChange.connect(self._on_user_change)
        self._ui_y_list = PivotGrid.ColumnListWidget(self._config, ColumnRole.Y, self._parent_dialog)
        self._ui_y_list.userChange.connect(self._on_user_change)

        layout = QtHelper.layout_grid(
            [
                [
                    QtHelper.layout_v('All Columns', self._ui_all_list),
                    QtHelper.layout_v('Group', self._ui_group_list),
                ],
                [
                    QtHelper.layout_v('X-Axis', self._ui_x_list),
                    QtHelper.layout_v('Y-Axis', self._ui_y_list),
                ]
            ]
        )
        layout.setRowStretch(0, 3)
        layout.setRowStretch(1, 3)
        layout.setRowStretch(2, 1)
        layout.setRowStretch(3, 1)
        self.setLayout(layout)

        self._update_lists()
    

    def setConfig(self, config: Config):
        self._config = config
        self._update_lists()


    def _update_lists(self):

        def update_widget(widget: PivotGrid.ColumnListWidget, col_switches: list[ColumnSwitch]):
            cols = [c.col for c in col_switches]
            widget.set_config(self._config)
            for setup in self._config.col_setups:
                if setup.col in cols:
                    widget.addItem(PivotGrid.ColumnItem(setup.col, self._config, widget._role, self._parent_dialog))
        
        update_widget(self._ui_all_list, self._config.col_setups)
        update_widget(self._ui_group_list, self._config.cols_group)
        update_widget(self._ui_x_list, self._config.cols_x)
        update_widget(self._ui_y_list, self._config.cols_y)


    def _on_user_change(self, col: str):

        # TODO: make sure color/style/size are assigned to one column only

        self.userChange.emit()
