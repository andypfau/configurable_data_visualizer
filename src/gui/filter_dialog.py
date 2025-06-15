from .filter_dialog_ui import FilterDialogUi
from lib.config import Config, Relation, Sort, FilterMode, ColumnRole, ConfigFilter

import os, pathlib
import sys
import re
import logging
import polars as pl
import numpy as np
import plotly, plotly.express, plotly.validators.scatter.marker
import plotly.graph_objects as go



class FilterDialog(FilterDialogUi):

    def __init__(self, config: Config, col: str, parent=None):
        super().__init__(parent)
        self.config, self.col = config, col
        
        filter = self._filter
        self.ui_set_col_name(col)
        self.ui_set_values_and_checked(config.get_column_values(col), filter.selection)
        self.ui_set_mode(filter.mode)
        self.ui_set_comparison(filter)


    @staticmethod
    def show_dialog(config: Config, col: str, parent):
        dialog = FilterDialog(config, col, parent)
        dialog.ui_show_modal()
    

    @property
    def _filter(self) -> ConfigFilter:
        return self.config.find_setup(self.col).filter


    def on_comparison_change(self):
        self._filter.mode = self.ui_get_mode()


    def on_check_all(self):
        all_values = self.config.get_column_values(self.col)
        self.ui_set_values_and_checked(all_values, all_values)
        self._filter.selection = all_values


    def on_check_none(self):
        all_values = self.config.get_column_values(self.col)
        self.ui_set_values_and_checked(all_values, [])
        self._filter.selection = []


    def on_check_toggle(self):
        all_values = self.config.get_column_values(self.col)
        currently_checked = self.ui_get_checked()
        new_checked = [value for value in all_values if value not in currently_checked]
        self.ui_set_values_and_checked(all_values, new_checked)
        self._filter.selection = new_checked


    def on_list_check(self):
        self._filter.selection = self.ui_get_checked()


    def on_mode_changed(self):
        self._filter.mode = self.ui_get_mode()
