from __future__ import annotations

from ..helpers.qt_helper import QtHelper
from ..filter_dialog import FilterDialog
from lib.config import Config, Sort, ConfigColumnSetup, ConfigFilter, FilterMode, ColumnRole, ColumnSwitch, PlotType

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


    drop_info = None

    @staticmethod
    def handle_drop(role: ColumnRole, role_index: int):
        PivotGrid.drop_info = (role, role_index)

    @staticmethod
    def handle_drag_end(config: Config, from_col: str, from_role: ColumnRole, from_role_index: int, is_move: bool):
        if not PivotGrid.drop_info:
            #print('Drag done, but got no drop data. Ingoring')
            return
        (to_role, to_role_index) = PivotGrid.drop_info
        PivotGrid.drop_info = None

        #print('===================================================================================')
        #print(f'{"Moving" if is_move else "Copying"} from {from_role} {from_role_index} to {to_role} {to_role_index}.')
        
        if from_role==to_role:  # just a re-order
            if from_role == ColumnRole.Unassigned:
                #print('Won\'t re-order all-columns.')
                return  # the unassigned columns are never re-ordered
            if from_role_index == to_role_index:
                #print('Won\'t re-order same indices.')
                return  # no action required
            
            #print(f'Moving inside {from_role} from {from_role_index} to {to_role_index}.')
            switches = config.get_switches(from_role)
            item_to_move = switches[from_role_index]
            del switches[from_role_index]
            if to_role_index == -1:
                switches.append(item_to_move)
            else:
                switches.insert(to_role_index, item_to_move)
            config.set_switches(from_role, switches)
        
        else:  # from one category to another

            if from_role == ColumnRole.Unassigned:  # must create new item
                item_to_move = ColumnSwitch()
                item_to_move.col = from_col
            else:
                item_to_move = config.get_switch(from_role, from_role_index)
            item_to_move.active = True  # user probably wants to use this immediately

            # remove from old role
            if is_move:
                if from_role != ColumnRole.Unassigned:
                    switches = config.get_switches(from_role)
                    del switches[from_role_index]
                    config.set_switches(from_role, switches)
                else:
                    pass#print('Cannot remove from all-columns.')
            else:
                pass#print('Won\'t remove from source (it\'s acopy).')

            # insert to new role
            if to_role != ColumnRole.Unassigned:
                switches = config.get_switches(to_role)
                if to_role_index == -1:
                    switches.append(item_to_move)
                else:
                    switches.insert(to_role_index, item_to_move)
                config.set_switches(to_role, switches)
            else:
                pass#print('Won\'t insert into all-columns.')
        

    userChange = pyqtSignal()


    class ColumnItem(QListWidgetItem):


        def __init__(self, col: str, role_index: int, config: Config, role: ColumnRole, parent_dialog: QWidget):
            super().__init__()
            self.col = col
            self._role_index = role_index
            self._config = config
            self._role = role
            self._parent_dialog = parent_dialog

            self._ui_context_menu = QMenu()
            self._add_contextmenu_items_at_beginning()
            def active_changed():
                self._config.get_switch(self._role, self._role_index).active = self._ui_active_item.isChecked()
                self._update_data()
            def remove_item():
                switches = self._config.get_switches(self._role)
                del switches[self._role_index]
                self._config.set_switches(self._role, switches)
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
                self._setup().as_style = self._ui_style.isChecked()
                self._update_data()
            def size_changed():
                self._setup().as_size = self._ui_size.isChecked()
                self._update_data()
            def filter_edit():
                FilterDialog.show_dialog(self._config, self.col, self._parent_dialog)
                self._update_data()
            
            if self._role != ColumnRole.Unassigned:
                self._ui_active_item = QtHelper.add_menuitem(self._ui_context_menu, 'Active', active_changed, checkable=True)
                self._ui_context_menu.addSeparator()
                self._ui_remove_item = QtHelper.add_menuitem(self._ui_context_menu, 'Remove', remove_item)
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
            self.setData(Qt.ItemDataRole.UserRole, (self.col, self._role, self._role_index, hash(self._setup())))
        
        def context_menu(self) -> QMenu|None:
            if self._role != ColumnRole.Unassigned:
                self._ui_active_item.setChecked(self._config.get_switch(self._role, self._role_index).active)
            self._ui_sort_asc.setChecked(self._setup().sort==Sort.Asc)
            self._ui_sort_desc.setChecked(self._setup().sort==Sort.Desc)
            self._ui_color.setChecked(self._setup().as_color)
            self._ui_style.setChecked(self._setup().as_style)
            self._ui_size.setChecked(self._setup().as_size)

            return self._ui_context_menu


    class ItemPaintDelegate(QStyledItemDelegate):

        def __init__(self, config: Config):
            self._config = config
            super().__init__()

        def set_config(self, config: Config):
            self._config = config
        
        def paint(self, painter: QtGui.QPainter, option: QStyleOptionViewItem, index: QtCore.QModelIndex):
            (col, role, role_index, _) = index.data(Qt.ItemDataRole.UserRole)
            setup = self._config.find_setup(col)

            text = setup.col
            activatable = role != ColumnRole.Unassigned
            if activatable:
                active = self._config.get_switch(role, role_index).active
            else:
                active = False
            error = setup.error
            text2_items = []
            if setup.filter.mode != FilterMode.Off:
                filter_str = setup.filter.format()
                if filter_str:
                    MAX_LEN = 25
                    if len(filter_str) > MAX_LEN:
                        filter_str = filter_str[:MAX_LEN-1] + '…'
                    text2_items.append(filter_str)
            if setup.sort != Sort.Off:
                if setup.sort == Sort.Asc:
                    text2_items.append('↓')
                elif setup.sort == Sort.Desc:
                    text2_items.append('↑')
            usages = []
            if role != ColumnRole.Unassigned:
                if len([sw for sw in self._config.get_switches(ColumnRole.Group) if sw.col==col and sw.active]) > 0:
                    usages.append('G')
                if len([sw for sw in self._config.get_switches(ColumnRole.X) if sw.col==col and sw.active]) > 0:
                    usages.append('X')
                if len([sw for sw in self._config.get_switches(ColumnRole.Y) if sw.col==col and sw.active]) > 0:
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
            if error:
                painter.setPen(QColorConstants.Black)
                painter.setBrush(QColorConstants.Yellow.lighter(125))
            elif activatable:
                if active:
                    painter.setPen(QColorConstants.Black)
                    painter.setBrush(QColorConstants.Green.lighter(190))
                else:
                    painter.setPen(QColorConstants.DarkGray)
                    painter.setBrush(QColorConstants.LightGray)
            else:
                painter.setPen(QColorConstants.Black)
                painter.setBrush(QColorConstants.White)
            painter.drawRoundedRect(outline_rect, 2.0, 2.0)

            regular_font = painter.font()
            bold_font = QFont(regular_font)
            bold_font.setBold(True)

            if setup.filter.mode != FilterMode.Off:
                text_rect = QRect(option.rect.right()-25, option.rect.top()+2, 23, option.rect.height()-4)
                painter.setPen(QColorConstants.Blue)
                painter.setFont(bold_font)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignTop|Qt.AlignmentFlag.AlignRight, 'F')
            if setup.sort != Sort.Off:
                text_rect = QRect(option.rect.right()-25, option.rect.top()+2, 23, option.rect.height()-4)
                painter.setPen(QColorConstants.Blue)
                painter.setFont(bold_font)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignBottom|Qt.AlignmentFlag.AlignRight, 'S')


            text_rect = QRect(option.rect)
            text_rect.adjust(8, 2, -8, -2)
            painter.setFont(regular_font)
            painter.setPen(QColorConstants.DarkGray if (activatable and not active) else QColorConstants.Black)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignTop|Qt.AlignmentFlag.AlignLeft, text)
            if text2:
                text_rect = QRect(option.rect)
                text_rect.adjust(8, 2, -8, -2)
                painter.setPen(QColorConstants.DarkGray)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignBottom|Qt.AlignmentFlag.AlignLeft, text2)

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

            self._paint_delegate = PivotGrid.ItemPaintDelegate(config)
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.updateGeometries()
            self.viewport().update()

            self.setItemDelegate(self._paint_delegate)
            self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.customContextMenuRequested.connect(self.show_context_menu)
            self.model().dataChanged.connect(self._on_data_changed)
        

        def _on_data_changed(self, topLeft: QModelIndex, bottomRight: QModelIndex, roles: int):
            if Qt.ItemDataRole.UserRole not in roles:
                return
            (col, role, role_index, _) = self.model().itemData(topLeft)[Qt.ItemDataRole.UserRole]
            self.userChange.emit(col)  # TODO: emit more data?
        

        def set_config(self, config: Config):
            self.clear()
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
            data.setData(PivotGrid.ColumnListWidget.MIME_COLUMN, pickle.dumps((item.col,item._role_index)))
            return data


        def unpack_mimedata(self, data: QMimeData) -> PivotGrid.ColumnItem:
            if data.hasFormat(PivotGrid.ColumnListWidget.MIME_COLUMN):
                (col,role_index) = pickle.loads(data.data(PivotGrid.ColumnListWidget.MIME_COLUMN))
                return PivotGrid.ColumnItem(col, role_index, self._config, self._role, self._parent_dialog)
            return None
        

        def mouseMoveEvent(self, event: QtGui.QMouseEvent):
            if Qt.MouseButton.LeftButton in event.buttons() and self._drag_start_pos:
                if (event.pos() - self._drag_start_pos).manhattanLength() >= QApplication.startDragDistance():
                    index: PivotGrid.ColumnItem = self.indexAt(event.position().toPoint())
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
                    painter.setPen(QColorConstants.Black)
                    painter.drawText(QRect(1, 1, 87, 22), Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter, item.col)
                    painter.end()
                    drag.setPixmap(pixmap)

                    result = drag.exec(Qt.DropAction.MoveAction | Qt.DropAction.CopyAction, Qt.DropAction.MoveAction)
                    if result == Qt.DropAction.IgnoreAction:
                        return
                    is_move = (result == Qt.DropAction.MoveAction)
                    
                    source_widget = self
                    target_widget = drag.target()
                    if target_widget is None:
                        return  # don't know what happend; drag to/from other app maybe?
                    if not isinstance(target_widget, PivotGrid.ColumnListWidget):
                        target_widget = target_widget.parent()
                    if not isinstance(target_widget, PivotGrid.ColumnListWidget):
                        return  # don't know what happend; drag to/from other app maybe?

                    PivotGrid.handle_drag_end(self._config, item.col, item._role, item._role_index, is_move)
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

            index = self.indexAt(event.position().toPoint())
            if index.isValid():
                row = index.row()
            else:
                row = -1
            PivotGrid.handle_drop(self._role, row)
            
            event.acceptProposedAction()


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

        self._ui_all_list = PivotGrid.ColumnListWidget(self._config, ColumnRole.Unassigned, self._parent_dialog)
        self._ui_all_list.userChange.connect(self._on_user_change)
        self._ui_group_list = PivotGrid.ColumnListWidget(self._config, ColumnRole.Group, self._parent_dialog)
        self._ui_group_list.userChange.connect(self._on_user_change)
        self._ui_x_list = PivotGrid.ColumnListWidget(self._config, ColumnRole.X, self._parent_dialog)
        self._ui_x_list.userChange.connect(self._on_user_change)
        self._ui_y_list = PivotGrid.ColumnListWidget(self._config, ColumnRole.Y, self._parent_dialog)
        self._ui_y_list.userChange.connect(self._on_user_change)
        self._ui_z_list = PivotGrid.ColumnListWidget(self._config, ColumnRole.Z, self._parent_dialog)
        self._ui_z_list.userChange.connect(self._on_user_change)

        self._ui_cell_lt_widget = QtHelper.layout_widget_v('X', self._ui_x_list)
        self._ui_cell_rt_widget = QtHelper.layout_widget_v('Y', self._ui_y_list)
        self._ui_cell_lb_widget = QtHelper.layout_widget_v('Z', self._ui_z_list)
        self._ui_cell_rb_widget = QtHelper.layout_widget_v()
        
        self._ui_layout = QtHelper.layout_grid(
            [
                [
                    QtHelper.layout_v('All Columns', self._ui_all_list),
                    QtHelper.layout_v('Group', self._ui_group_list),
                ],
                [
                    self._ui_cell_lt_widget, self._ui_cell_rt_widget,
                ],
                [
                    self._ui_cell_lb_widget, self._ui_cell_rb_widget,
                ]
            ]
        )
        self.setLayout(self._ui_layout)

        self._update_layout()
        self._update_lists()
    

    def setConfig(self, config: Config):
        self._config = config
        self._update_layout()
        self._update_lists()
    

    @property
    def _need_x(self) -> bool:
        return self._config.plot.type not in [PlotType.StatMatrix]
    

    @property
    def _need_y(self) -> bool:
        return self._config.plot.type not in [PlotType.StatMatrix]
    

    @property
    def _need_z(self) -> bool:
        return self._config.plot.type in [PlotType.Scatter3D]


    def _update_layout(self):
        self._ui_cell_lt_widget.setVisible(self._need_x)
        self._ui_cell_rt_widget.setVisible(self._need_y)
        self._ui_cell_lb_widget.setVisible(self._need_z)
        self._ui_cell_rb_widget.setVisible(False)


    def _update_lists(self):

        def update_widget(widget: PivotGrid.ColumnListWidget):
            widget.clear()
            widget.set_config(self._config)
            if widget._role == ColumnRole.Unassigned:
                for setup in sorted(self._config.col_setups, key=lambda s: s.col.casefold()):
                    widget.addItem(PivotGrid.ColumnItem(setup.col, None, self._config, widget._role, self._parent_dialog))
            else:
                for role_index,switch in enumerate(self._config.get_switches(widget._role)):
                    setup = self._config.find_setup(switch.col)
                    widget.addItem(PivotGrid.ColumnItem(switch.col, role_index, self._config, widget._role, self._parent_dialog))

        update_widget(self._ui_all_list)
        update_widget(self._ui_group_list)
        if self._need_x:
            update_widget(self._ui_x_list)
        if self._need_y:
            update_widget(self._ui_y_list)
        if self._need_z:
            update_widget(self._ui_z_list)


    def _on_user_change(self, col: str):

        # ensure the <as_*>-properties are unique
        setup = self._config.find_setup(col)
        if setup.as_color:
            for setup in self._config.col_setups:
                if setup.col == col:
                    continue
                setup.as_color = False
        if setup.as_size:
            for setup in self._config.col_setups:
                if setup.col == col:
                    continue
                setup.as_size = False
        if setup.as_style:
            for setup in self._config.col_setups:
                if setup.col == col:
                    continue
                setup.as_style = False


        self._update_lists()
        self.userChange.emit()
