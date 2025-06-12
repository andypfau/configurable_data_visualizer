from .main_window_ui import MainWindowUi
from .filter_dialog import FilterDialog
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
        #self.config: Config = Config.load('datafile.json')
        self.config: Config = Config.load('autosave.json')

        self.ui_set_lines(self.config.plot.lines)
        self.load_files()
        self.apply_filters_and_sorting()
        self.ui_pivot_grid().setConfig(self.config)
        self.update_plot()
        self.config.save('autosave.json')

    
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
                    for line in fp.readlines():
                        if line.startswith('#'):
                            comment_list.append(line.strip())
                comment = '\n'.join(comment_list)
                df = pl.scan_csv(path, comment_prefix='#')
                #print(df)
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
                match col_setup.filter.rel:
                    case Relation.Equal: condition = pl.col(col_setup.col)==col_setup.filter.value
                    case Relation.NotEqual: condition = pl.col(col_setup.col)!=col_setup.filter.value
                    case Relation.Greater: condition = pl.col(col_setup.col)>col_setup.filter.value
                    case Relation.GreaterOrEqual: condition = pl.col(col_setup.col)>=col_setup.filter.value
                    case Relation.Less: condition = pl.col(col_setup.col)<col_setup.filter.value
                    case Relation.LessOrEqual: condition = pl.col(col_setup.col)<=col_setup.filter.value
                    case Relation.In: condition = pl.col(col_setup.col).is_between(col_setup.filter.value,col_setup.filter.value2,closed='both')
                    case Relation.NotIn: condition = ~pl.col(col_setup.col).is_between(col_setup.filter.value,col_setup.filter.value2,closed='both')
                    case _: raise ValueError()
            elif col_setup.filter.mode == FilterMode.Values:
                condition = pl.col(col_setup.col).is_in(col_setup.filter.values)
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


    def update_plot(self):

        df = self.config.df

        def check_cols(list):
            for col in list:
                if col not in self.config.all_columns:
                    logging.warning(f'Invalid column "{col}"')
        def get_single_col(cols):
            if len(cols) == 0:
                return None
            else:
                if len(cols) > 1:
                    logging.warning(f'Ignoring multiple assignments for color, using column "{cols[0]}"')
                return cols[0]
        
        check_cols(self.config.cols_group)
        check_cols(self.config.cols_x)
        check_cols(self.config.cols_y)

        group_cols = [c.col for c in self.config.cols_group if c.active and c.col in self.config.all_columns]
        x_cols = [c.col for c in self.config.cols_x if c.active and c.col in self.config.all_columns]
        y_cols = [c.col for c in self.config.cols_y if c.active and c.col in self.config.all_columns]
        color_col = get_single_col([c.col for c in self.config.col_setups if c.as_color and c.col in self.config.all_columns])
        style_col = get_single_col([c.col for c in self.config.col_setups if c.as_style and c.col in self.config.all_columns])
        size_col = get_single_col([c.col for c in self.config.col_setups if c.as_size and c.col in self.config.all_columns])
        
        color_map = {}
        def get_discrete_color(col):
            nonlocal color_map
            if col not in color_map:
                available = MainWindow.get_all_plot_colors()
                color_map[col] = available[len(color_map) % len(available)]
            return color_map[col]

        marker_map = {}
        def get_discrete_marker(col):
            nonlocal marker_map
            if col not in marker_map:
                available = MainWindow.get_all_plot_markers()
                marker_map[col] = available[len(marker_map) % len(available)]
            return marker_map[col]

        range_map = {}
        def get_relative_value(col, value):
            nonlocal range_map
            if col not in range_map:
                all_values = self.config.get_column_values(col)
                lo, hi = np.min(all_values), np.max(all_values)
                range_map[col] = (lo, hi)
            (lo, hi) = range_map[col]
            if lo==hi:
                return 0.5
            return (value - lo) / (hi-lo)
        
        logging.info(f'Groups: {group_cols}; Color: {color_col}; X: {x_cols}; Y: {y_cols}')

        fig = go.Figure()

        def plot_group(group_tuple: tuple, df: pl.DataFrame):

            can_use_lines = True
            if len(x_cols) == 0:
                logging.warning(f'No x-columns to plot')
                return
            elif len(x_cols) == 1:
                x = df.get_column(x_cols[0]).to_numpy()
                n_total, n_unique = len(x), len(np.unique(x))
                if n_total > n_unique:
                    logging.warning(f'There are {n_total} X-axis values, but only {n_unique} unique; you probably forgot some grouping or filtering')
                    can_use_lines = False
            else:
                x = [df.get_column(x_col).to_numpy() for x_col in x_cols]
                n_total = max(*[len(x1) for x1 in x])
                n_unique_per_group = [len(np.unique(x1)) for x1 in x]
                n_expected_total = np.prod(n_unique_per_group)
                if n_total > n_expected_total:
                    logging.warning(f'There are {n_total} X-axis values, but only {n_expected_total} unique; you probably forgot some grouping or filtering')
                    can_use_lines = False
            
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
                        individual_colors = [get_discrete_color(elem) for elem in color_values]#
                
                common_markers = None
                individual_markers = None
                if style_col is not None:
                    style_values = df.get_column(style_col)
                    if len(set(style_values)) == 1:
                        common_markers = get_discrete_marker(style_values[0])
                    else:
                        individual_markers = [get_discrete_marker(elem) for elem in style_values]
                
                individual_sizes = None
                if size_col is not None:
                    size_values = df.get_column(size_col)
                    sizes = [get_relative_value(size_col, elem) for elem in size_values]
                    individual_sizes = np.array(sizes)

                line = dict()
                marker = dict()

                use_lines = can_use_lines and self.config.plot.lines
                use_markers = False
                
                if common_color:
                    line['color'] = common_color
                    marker['color'] = common_color
                elif individual_colors is not None:
                    use_markers = True
                    marker['color'] = individual_colors
                
                if common_markers is not None:
                    use_markers = True
                    marker['symbol'] = common_markers
                if individual_markers is not None:
                    use_markers = True
                    marker['symbol'] = individual_markers

                if individual_sizes is not None:
                    use_markers = True
                    marker['size'] = 5 + 15 * individual_sizes
                
                if use_lines and use_markers:
                    mode = 'lines+markers'
                elif use_lines:
                    mode = 'lines'
                else:
                    mode = 'markers'

                fig.add_trace(go.Scatter(x=x, y=y, name=legend, mode=mode, text=infos, line=line, marker=marker))

        if len(group_cols) >= 1:
            for group_tuple,dfg in df.group_by(group_cols, maintain_order=True):
                plot_group(group_tuple, dfg)
        else:
            plot_group(tuple(), df)

        fig.update_layout(xaxis_title=self.config.plot.x_title, yaxis_title=self.config.plot.y_title)
        self.ui_plot(fig)
    

    @staticmethod
    def get_all_plot_colors() -> list:
        return plotly.express.colors.qualitative.Plotly
    

    @staticmethod
    def get_all_plot_markers() -> list:
        all_symbols = plotly.validators.scatter.marker.SymbolValidator().values
        symbols_without_numers = [s for s in all_symbols if not re.match(r'^[0-9].*', str(s))]
        symbols_without_specials = [s for s in symbols_without_numers if '-' not in s]
        return symbols_without_specials


    def need_re_render(self):
        self.apply_filters_and_sorting()
        self.update_plot()
        self.config.save('autosave.json')


    def on_pivot_change(self):
        self.need_re_render()


    def on_lines_change(self):
        self.config.plot.lines = self.ui_get_lines()
        self.need_re_render()
