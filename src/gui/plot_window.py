from .plot_window_ui import PlotWindowUi
from .filter_dialog import FilterDialog
from lib.config import Config, Relation, Sort, FilterMode, ColumnRole, PlotType
from lib.utils import reverse_lookup
from lib.shortstr import shorten_string_list
from lib.plot import Plot

import os, pathlib
import sys
import re
import logging
import polars as pl
import numpy as np
import plotly, plotly.express, plotly.validators.scatter.marker
import plotly.graph_objects as go
from typing import Callable



class PlotWindow(PlotWindowUi):


    PLOTTYPE_NAMES = {
        PlotType.Scatter: 'Scatter',
        PlotType.Heatmap: 'Heatmap',
        PlotType.Scatter3D: '3D Scatter',
        PlotType.StatMatrix: 'Stat Matrix',
    }


    def __init__(self, callback_plot: Callable):
        super().__init__()
        self._callback_plot = callback_plot
        self.ui_set_plottype_options(PlotWindow.PLOTTYPE_NAMES.values())
        self.config: Config = None
        

    def show(self, config: Config):
        self.config = config

        try:
            self.update_ui_from_config()
            self.load_files()
            self.ui_pivot_grid().setConfig(self.config)
            self.apply_filters_and_sorting()
            self.update_plot()

            self.config.autosave()
        
        except Exception as ex:
            logging.error(f'Unable to load ({ex})')
        
        super().show()
    

    def update_ui_from_config(self):
        self.ui_set_lines(self.config.plot.scatter_lines)
        self.ui_set_plottype(PlotWindow.PLOTTYPE_NAMES[self.config.plot.type])

    
    def load_files(self):
        
        file_names = shorten_string_list([pathlib.Path(path).name for path in self.config.input.files])

        dfs = []
        for path,name in zip(self.config.input.files,file_names):
            try:
                logging.info(f'Loading <{path}>')
                comment_list = []
                with open(path, 'r') as fp:
                    for line in fp.readlines():
                        if line.startswith('#'):
                            comment_list.append(line.strip())
                comment = '\n'.join(comment_list)
                df = pl.scan_csv(path, comment_prefix='#', separator=self.config.input.csv_separator)
                #print(df)
                df = df.with_columns([
                    pl.lit(comment).alias('_file_comment'),
                    pl.lit(name).alias('_file_name'),
                    pl.lit(path).alias('_file_path'),
                    pl.lit(len(dfs)).alias('_file_id'),
                ])
                df = df.with_row_index(name='_file_row_id')
                dfs.append(df)
            except Exception as ex:
                logging.error(f'Loading <{path}> failed ({ex})')
        
        if len(dfs) == 1:
            df = dfs[0]
        elif len(dfs) > 1:
            df = pl.concat(dfs)
        else:
            df = pl.LazyFrame()
        df = df.with_row_index(name='_row_id')

        self.config.raw_df = df.collect()
    

    def apply_filters_and_sorting(self):

        conditions = None
        sort_cols, sort_desc = [], []

        # TODO: the sorting should depend on the order in those 3 roles

        for col_setup in self.config.col_setups:
            if col_setup.col not in self.config.all_columns:
                logging.warning(f'Ignoring setup of non-existing column "{col_setup.col}"')
                continue
            
            condition = None
            if col_setup.filter.mode == FilterMode.Expression:
                raise NotImplementedError('Expression filtering is not implemented yet')
            elif col_setup.filter.mode == FilterMode.Comparison:
                match col_setup.filter.cmp_rel:
                    case Relation.Equal: condition = pl.col(col_setup.col)==col_setup.filter.cmp_value
                    case Relation.NotEqual: condition = pl.col(col_setup.col)!=col_setup.filter.cmp_value
                    case Relation.Greater: condition = pl.col(col_setup.col)>col_setup.filter.cmp_value
                    case Relation.GreaterOrEqual: condition = pl.col(col_setup.col)>=col_setup.filter.cmp_value
                    case Relation.Less: condition = pl.col(col_setup.col)<col_setup.filter.cmp_value
                    case Relation.LessOrEqual: condition = pl.col(col_setup.col)<=col_setup.filter.cmp_value
                    case Relation.In: condition = pl.col(col_setup.col).is_between(col_setup.filter.cmp_value,col_setup.filter.cmp_value2,closed='both')
                    case Relation.NotIn: condition = ~pl.col(col_setup.col).is_between(col_setup.filter.cmp_value,col_setup.filter.cmp_value2,closed='both')
                    case _: raise ValueError()
            elif col_setup.filter.mode == FilterMode.Selection:
                condition = pl.col(col_setup.col).is_in(col_setup.filter.selection)
            elif col_setup.filter.mode == FilterMode.Off:
                pass
            else: raise ValueError()
            if condition is not None:
                if conditions is None:
                    conditions = condition
                else:
                    conditions = conditions & (condition)
        
        for role in [ColumnRole.Y, ColumnRole.X, ColumnRole.Group]:
            for switch in self.config.get_switches(role):
                col = switch.col
                setup = self.config.find_setup(col)
                if setup.sort == Sort.Asc:
                    sort_cols.append(setup.col)
                    sort_desc.append(False)
                if setup.sort == Sort.Desc:
                    sort_cols.append(setup.col)
                    sort_desc.append(True)
        
        df = self.config.raw_df.lazy()
        if conditions is not None:
            df = df.filter(conditions)
        if len(sort_cols) >= 1:
            logging.info(f'Sorting by {sort_cols}')
            df = df.sort(by=sort_cols, descending=sort_desc)
        self.config.df = df.collect()
        logging.info(f'Dataframe shape: {self.config.df.shape}')


    def update_plot(self):
        try:
            self.ui_plot('Preparing...')
            fig = Plot(self.config).plot()
            self.ui_plot(fig)
        except Exception as ex:
            logging.error(f'Plot update failed ({ex})')
            self.ui_plot(str(ex))


    def need_re_render(self):
        try:
            self.apply_filters_and_sorting()
            self.update_plot()
            self.config.autosave()
        except Exception as ex:
            logging.error(f'Plot update failed ({ex})')


    def on_pivot_change(self):
        self.need_re_render()


    def on_lines_change(self):
        self.config.plot.scatter_lines = self.ui_get_lines()
        self.need_re_render()


    def on_plottype_change(self):
        self.config.plot.type = reverse_lookup(PlotWindow.PLOTTYPE_NAMES, self.ui_get_plottype())
        self.ui_pivot_grid().setConfig(self.config)
        self.need_re_render()
    
    
    def on_files(self):
        self._callback_plot(self.config)


    def on_save(self):
        try:
            self.config.save(self.config.filename)
        except Exception as ex:
            logging.error(f'Saving failed ({ex})')
