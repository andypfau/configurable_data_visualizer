from .main_window_ui import MainWindowUi
from lib.config import Config, Relation, Sort, FilterMode, ColumnRole

import os, pathlib
import sys
import re
import logging
import polars as pl
import numpy as np
import plotly, plotly.express, plotly.validators.scatter.marker
import plotly.graph_objects as go



class MainWindow(MainWindowUi):

    def __init__(self, filenames: list[str]):
        super().__init__()
        self.config: Config = Config.load('config.json')

        self.load_files()
        self.apply_filters_and_sorting()
        self.uiPivotGrid().setConfig(self.config)
        self.update_plot()
        self.config.save('config_generated.json')

    
    def load_files(self):

        self.config.all_files.clear()
        if len(self.config.input.files) > 0:
            paths = [pathlib.Path(p) for p in self.config.input.files]
            self.config.all_files.extend([p for p in paths if p.exists() and p.is_file()])
        else:
            rex_include = re.compile(self.config.input.glob_regex_include) if self.config.input.glob_regex_include else None
            rex_exclude = re.compile(self.config.input.glob_regex_exclude) if self.config.input.glob_regex_exclude else None
            for path in sorted(pathlib.Path(self.config.input.glob_dir).glob(self.config.input.glob_pattern)):
                if rex_include and not rex_include.match(path.name):
                    continue
                if rex_exclude and rex_exclude.match(path.name):
                    continue
                self.config.all_files.append(path)
        
        dfs = []
        for path in self.config.all_files:
            try:
                logging.info(f'Loading <{path}>')
                comment_list = []
                with open(path, 'r') as fp:
                    for line in fp.readline():
                        if line.startswith('#'):
                            comment_list.append(line.strip())
                comment = '\n'.join(comment_list)
                df = pl.scan_csv(path, separator=';', comment_prefix='#')
                df = df.with_columns([
                    pl.lit(comment).alias('_file_comment'),
                    pl.lit(str(path)).alias('_file_path'),
                    pl.lit(len(dfs)).alias('_file_id'),
                ])
                df = df.with_row_index(name='_file_row_id')
                dfs.append(df)
            except Exception as ex:
                logging.error(f'Loading <{path}> failed ({ex})')
        
        if len(dfs) == 1:
            self.config.raw_df = dfs[0]
        elif len(dfs) > 1:
            self.config.raw_df = pl.concat(dfs)
        else:
            self.config.raw_df = pl.DataFrame()
        self.config.raw_df = self.config.raw_df.with_row_index(name='_row_id')
        self.config.columns = self.config.raw_df.collect_schema().names()
    

    def apply_filters_and_sorting(self):

        conditions = None
        sort_cols, sort_desc = [], []
        for col_setup in self.config.col_setups:
            if col_setup.col not in self.config.columns:
                logging.warning(f'Ignoring setup of non-existing column "{col_setup.col}"')
                continue
            
            condition = None
            if col_setup.filter.mode == FilterMode.Expression:
                raise NotImplementedError('Expression filtering is not implemented yet')
            elif col_setup.filter.mode == FilterMode.Comparison:
                match col_setup.filter.rel:
                    case Relation.Equal: condition = pl.col(col_setup.col)==col_setup.filter.value
                    case Relation.NotEqual: condition = pl.col(col_setup.col)!=col_setup.filter.value
                    case Relation.Greater: condition = pl.col(col_setup.col)>col_setup.filter.value
                    case Relation.GreaterOrEqual: condition = pl.col(col_setup.col)>=col_setup.filter.value
                    case Relation.Less: condition = pl.col(col_setup.col)<col_setup.filter.value
                    case Relation.LessOrEqual: condition = pl.col(col_setup.col)<=col_setup.filter.value
                    case Relation.In: condition = pl.col(col_setup.col).is_between(col_setup.filter.value,col_setup.filter.value2,closed=True)
                    case Relation.NotIn: condition = ~pl.col(col_setup.col).is_between(col_setup.filter.value,col_setup.filter.value2,closed=True)
                    case _: raise ValueError()
            elif col_setup.filter.mode == FilterMode.Values:
                raise NotImplementedError('Value-list filtering is not implemented yet')
            elif col_setup.filter.mode == FilterMode.Off:
                pass
            else: raise ValueError()
            if condition is not None:
                if conditions is None:
                    conditions = condition
                else:
                    conditions = conditions & (condition)
            
            if col_setup.sort == Sort.Asc:
                sort_cols.append(col_setup.col)
                sort_desc.append(False)
            if col_setup.sort == Sort.Desc:
                sort_cols.append(col_setup.col)
                sort_desc.append(True)

        if conditions is not None:
            self.config.raw_df = self.config.raw_df.filter(conditions)
        if len(sort_cols) >= 1:
            print(f'Sorting by {sort_cols}')
            self.config.raw_df = self.config.raw_df.sort(by=sort_cols, descending=sort_desc)


    def update_plot(self):

        self.config.df = self.config.raw_df.collect()

        def get_cols(role: ColumnRole, single: bool = False):
            result = []
            for col in self.config.col_setups:
                if role & col.activation:
                    result.append(col.col)
            
            if single:
                if len(result) == 0:
                    return None
                else:
                    if len(result) > 1:
                        logging.warning(f'Ignoring multiple assingnments for role <{role}>')
                    return result[0]
            else:
                return result

        group_cols = get_cols(ColumnRole.Group)
        x_cols = get_cols(ColumnRole.X)
        y_cols = get_cols(ColumnRole.Y)
        color_col = get_cols(ColumnRole.Color, single=True)
        size_col = get_cols(ColumnRole.Size, single=True)  # TODO: implement
        style_col = get_cols(ColumnRole.Style, single=True)  # TODO: implement
        
        color_map = {}
        def get_discrete_color(key):
            nonlocal color_map
            if key not in color_map:
                available = MainWindow.get_all_plot_colors()
                color_map[key] = available[len(color_map) % len(available)]
            return color_map[key]

        marker_map = {}
        def get_discrete_marker(key):
            nonlocal marker_map
            if key not in marker_map:
                available = MainWindow.get_all_plot_markers()
                marker_map[key] = available[len(marker_map) % len(available)]
            return marker_map[key]
        
        print(f'Groups: {group_cols}; Color: {color_col}; Style: {style_col}; Size: {size_col}; X: {x_cols}; Y: {y_cols}')

        fig = go.Figure()

        def plot_group(group_tuple: tuple, df: pl.DataFrame):

            unique = True
            if len(x_cols) == 0:
                logging.warning(f'No x-columns to plot')
                return
            elif len(x_cols) == 1:
                x = df.get_column(x_cols[0]).to_numpy()
                n_total, n_unique = len(x), len(np.unique(x))
                if n_total > n_unique:
                    logging.warning(f'There are {n_total} X-axis values, but only {n_unique} unique; you probably forgot some grouping or filtering')
                    unique = False
            else:
                x = [df.get_column(x_col).to_numpy() for x_col in x_cols]
                n_total = max(*[len(x1) for x1 in x])
                n_unique_per_group = [len(np.unique(x1)) for x1 in x]
                n_expected_total = np.prod(n_unique_per_group)
                if n_total > n_expected_total:
                    logging.warning(f'There are {n_total} X-axis values, but only {n_expected_total} unique; you probably forgot some grouping or filtering')
                    unique = False
            
            def format(x):
                if isinstance(x, float):
                    return f'{x:.6g}'
                return str(x)

            for y_col in y_cols:
                y = df.get_column(y_col).to_numpy()

                if len(group_tuple) == 1:
                    legend = format(group_tuple[0])
                else:
                    legend = ', '.join([f'{n}={format(v)}' for (n,v) in zip(group_cols,group_tuple)])
                if len(y_cols) > 1:
                    legend = y_col + ' ' + legend
                
                infos = y_col + '<br>' + '<br>'.join([f'{n} = {format(v)}' for (n,v) in zip(group_cols,group_tuple)])
                
                common_color = None
                individual_colors = None
                if color_col is not None:
                    color_values = df.get_column(color_col)
                    if len(set(color_values)) == 1:
                        common_color = get_discrete_color(color_values[0])
                    else:
                        unique = False
                        individual_colors = [get_discrete_color(elem) for elem in color_values]#
                
                common_markers = None
                individual_markers = None
                if style_col is not None:
                    style_values = df.get_column(style_col)
                    if len(set(style_values)) == 1:
                        common_markers = get_discrete_marker(style_values[0])
                    else:
                        unique = False
                        individual_markers = [get_discrete_marker(elem) for elem in style_values]#

                line = dict()
                marker = dict()
                if unique:
                    mode = 'lines'
                    if common_color:
                        line['color'] = common_color
                else:
                    mode = 'markers'
                    if individual_colors:
                        marker['color'] = individual_colors
                    elif common_color:
                        marker['color'] = common_color
                if common_markers or individual_markers:
                    if mode=='lines':
                        mode = 'lines+markers'
                    marker['symbol'] = common_markers or individual_markers

                fig.add_trace(go.Scatter(x=x, y=y, name=legend, mode=mode, text=infos, line=line, marker=marker))

        if len(group_cols) >= 1:
            for group_tuple,dfg in self.config.df.group_by(group_cols, maintain_order=True):
                plot_group(group_tuple, dfg)
        else:
            plot_group(tuple(), self.config.df)

        fig.update_layout(xaxis_title=self.config.plot.x_title, yaxis_title=self.config.plot.y_title)
        self.uiPlot(fig)
    

    @staticmethod
    def get_all_plot_colors() -> list:
        return plotly.express.colors.qualitative.Plotly
    

    @staticmethod
    def get_all_plot_markers() -> list:
        all_symbols = plotly.validators.scatter.marker.SymbolValidator().values
        symbols_without_numers = [s for s in all_symbols if not re.match(r'^[0-9].*', str(s))]
        symbols_without_specials = [s for s in symbols_without_numers if '-' not in s]
        return symbols_without_specials

    def on_pivot_change(self):
        self.apply_filters_and_sorting()
        self.update_plot()
        self.config.save('config_generated.json')
