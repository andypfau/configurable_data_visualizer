from .main_window_ui import MainWindowUi
from lib.config import Config, Relation, Sort

import os, pathlib
import sys
import re
import logging
import polars as pl
import numpy as np
import plotly.express.colors
import plotly.graph_objects as go



class MainWindow(MainWindowUi):

    def __init__(self, filenames: list[str]):
        super().__init__()
        self.config = Config()
        self.files: list[pathlib.Path] = []
        self.df: pl.DataFrame = pl.DataFrame()
        
        self.config = Config.load('config_test.json')
        # self.config.save('config_test1.json')

        self.load_files()
        self.apply_filters()
        self.uiPivotGrid().setData(self.df.columns, self.config)
        self.update_plot()

    
    def load_files(self):

        self.files.clear()
        if len(self.config.files.files) > 0:
            self.files.extend([pathlib.Path(p) for p in self.config.files.files])
        else:
            rex_include = re.compile(self.config.files.glob_regex_include) if self.config.files.glob_regex_include else None
            rex_exclude = re.compile(self.config.files.glob_regex_exclude) if self.config.files.glob_regex_exclude else None
            for path in sorted(pathlib.Path(self.config.files.glob_dir).glob(self.config.files.glob_pattern)):
                if rex_include and not rex_include.match(path.name):
                    continue
                if rex_exclude and rex_exclude.match(path.name):
                    continue
                self.files.append(path)
        
        dfs = []
        for path in self.files:
            try:
                logging.info(f'Loading <{path}>')
                comment_list = []
                with open(path, 'r') as fp:
                    for line in fp.readline():
                        if line.startswith('#'):
                            comment_list.append(line.strip())
                comment = '\n'.join(comment_list)
                df = pl.read_csv(path, separator=';', comment_prefix='#')
                df.with_columns([
                    pl.lit(comment).alias('_comment'),
                    pl.lit(str(path)).alias('_path'),
                    pl.lit(len(dfs)+1).alias('_file_id'),
                ])
                dfs.append(df)
            except Exception as ex:
                logging.error(f'Loading <{path}> failed ({ex})')
        if len(dfs) == 1:
            self.df = dfs[0]
        elif len(dfs) > 1:
            self.df = pl.concat(dfs)
        else:
            self.df = pl.DataFrame()
        self.df = self.df.with_row_index(name='_row_id', offset=1)


    def apply_filters(self):

        predicates = None
        for f in self.config.filters:
            if f.col not in self.df.columns:
                continue
            match f.rel:
                case Relation.Equal: predicate = pl.col(f.col)==f.value
                case Relation.NotEqual: predicate = pl.col(f.col)!=f.value
                case Relation.Greater: predicate = pl.col(f.col)>f.value
                case Relation.GreaterOrEqual: predicate = pl.col(f.col)>=f.value
                case Relation.Less: predicate = pl.col(f.col)<f.value
                case Relation.LessOrEqual: predicate = pl.col(f.col)<=f.value
                case Relation.In: predicate = pl.col(f.col).is_between(f.value,f.value2,closed=True)
                case Relation.NotIn: predicate = ~pl.col(f.col).is_between(f.value,f.value2,closed=True)
                case _: raise ValueError()

            if predicates is None:
                predicates = predicate
            else:
                predicates = predicates & (predicate)

        if predicates is not None:
            self.df = self.df.filter(predicates)


    def update_plot(self):

        all_cols = self.df.columns

        # TODO: more checks!
        invalid_x_cols = [col.col for col in self.config.cols_x if col.col not in all_cols]
        if len(invalid_x_cols) > 0:
            logging.error(f'Invalid X cols: {invalid_x_cols}')
        invalid_y_cols = [col.col for col in self.config.cols_y if col.col not in all_cols]
        if len(invalid_y_cols) > 0:
            logging.error(f'Invalid X cols: {invalid_y_cols}')
        invalid_group_cols = [col.col for col in self.config.cols_group if col.col not in all_cols]
        if len(invalid_group_cols) > 0:
            logging.error(f'Invalid group cols: {invalid_group_cols}')


        sort_cols, sort_desc = [], []
        for col in [*self.config.cols_group, *self.config.cols_color, *self.config.cols_x]:
            if (col.col not in all_cols) or (not col.active) or (col.sort == Sort.Off):
                continue
            sort_cols.append(col.col)
            sort_desc.append(col.sort == Sort.Desc)
        if len(sort_cols) >= 1:
            self.df = self.df.sort(by=sort_cols, descending=sort_desc)


        group_cols = [col.col for col in self.config.cols_group if col.col in all_cols and col.active]
        color_cols = [col.col for col in self.config.cols_color if col.col in all_cols and col.active]
        x_cols = [col.col for col in self.config.cols_x if col.col in all_cols and col.active and col.col not in group_cols]
        y_cols = [col.col for col in self.config.cols_y if col.col in all_cols and col.active]
        
        color_map = {}
        def get_color_from_swatch(key):
            nonlocal color_map
            if key not in color_map:
                swatch = plotly.express.colors.qualitative.Plotly
                color_map[key] = swatch[len(color_map) % len(swatch)]
            return color_map[key]
        
        print(f'Groups: {group_cols}; X: {x_cols}; Y: {y_cols}')

        fig = go.Figure()

        def plot_group(group_tuple: tuple, dfg: pl.DataFrame):

            unique = True
            if len(x_cols) == 0:
                raise RuntimeError('No cols')
            elif len(x_cols) == 1:
                x = dfg.get_column(x_cols[0]).to_numpy()
                n_total, n_unique = len(x), len(np.unique(x))
                if n_total > n_unique:
                    logging.warning(f'There are {n_total} X-axis values, but only {n_unique} unique; you probably forgot some grouping or filtering')
                    unique = False
            else:
                x = [dfg.get_column(x_col).to_numpy() for x_col in x_cols]
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
                y = dfg.get_column(y_col).to_numpy()

                if len(group_tuple) == 1:
                    legend = format(group_tuple[0])
                else:
                    legend = ', '.join([f'{n}={format(v)}' for (n,v) in zip(group_cols,group_tuple)])
                if len(y_cols) > 1:
                    legend = y_col + ' ' + legend
                text = y_col + '<br>' + '<br>'.join([f'{n} = {format(v)}' for (n,v) in zip(group_cols,group_tuple)])
                common_color = None
                individual_colors = None

                for color_col in color_cols:
                    color_values = dfg.get_column(color_col)
                    if len(set(color_values)) == 1:
                        common_color = get_color_from_swatch(color_values[0])
                    else:
                        unique = False
                        individual_colors = [get_color_from_swatch(elem) for elem in color_values]
                    break # only allow one

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

                fig.add_trace(go.Scatter(x=x, y=y, name=legend, mode=mode, text=text, line=line, marker=marker))

        if len(group_cols) >= 1:
            for group_tuple,dfg in self.df.group_by(group_cols, maintain_order=True):
                plot_group(group_tuple, dfg)
        else:
            plot_group(tuple(), self.df.clone())

        fig.update_layout(xaxis_title=self.config.plot.x_title, yaxis_title=self.config.plot.y_title)
        self.uiPlot(fig)


    def on_pivot_change(self):
        self.apply_filters()
        self.update_plot()
