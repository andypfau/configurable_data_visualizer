from .main_window_ui import MainWindowUi
from lib.config import Config, Relation

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


        config = Config.load('config_test.json')
        # config = Config()
        # config.filters.append(Config.Filter('f/GHz', Relation.GrEq, 1.5e9))
        # config.cols_x.append(Config.Col('PSet/dBm'))
        # config.cols_x.append(Config.Col('f/GHz'))
        # config.cols_y.append(Config.Col('PMeas/dBm'))
        # config.cols_group.append(Config.Col('XParam'))
        # config.save('config_test.json')


        files: list[pathlib.Path] = []
        if len(config.files.files) > 0:
            files.extend([pathlib.Path(p) for p in config.files.files])
        else:
            rex_include = re.compile(config.files.glob_regex_include) if config.files.glob_regex_include else None
            rex_exclude = re.compile(config.files.glob_regex_exclude) if config.files.glob_regex_exclude else None
            for path in sorted(pathlib.Path(config.files.glob_dir).glob(config.files.glob_pattern)):
                if rex_include and not rex_include.match(path.name):
                    continue
                if rex_exclude and rex_exclude.match(path.name):
                    continue
                files.append(path)
        
        
        dfs = []
        for path in files:
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
        df: pl.DataFrame = pl.concat(dfs)
        df = df.with_row_index(name='_row_id', offset=1)

        all_cols = df.columns
        
        sort_cols = [col.col for col in config.sort if col.col in all_cols]
        sort_desc = [col.descending for col in config.sort if col.col in all_cols]
        df = df.sort(by=sort_cols, descending=sort_desc)

        # TODO: more checks!
        invalid_x_cols = [col.col for col in config.cols_x if col.col not in all_cols]
        if len(invalid_x_cols) > 0:
            logging.error(f'Invalid X cols: {invalid_x_cols}')
        invalid_y_cols = [col.col for col in config.cols_y if col.col not in all_cols]
        if len(invalid_y_cols) > 0:
            logging.error(f'Invalid X cols: {invalid_y_cols}')
        invalid_group_cols = [col.col for col in config.cols_group if col.col not in all_cols]
        if len(invalid_group_cols) > 0:
            logging.error(f'Invalid group cols: {invalid_group_cols}')

        group_cols = [col.col for col in config.cols_group if col.col in all_cols and col.active]
        x_cols = [col.col for col in config.cols_x if col.col in all_cols and col.active and col.col not in group_cols]
        y_cols = [col.col for col in config.cols_y if col.col in all_cols and col.active]
        
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
                n_total = np.maximum(*[len(x1) for x1 in x])
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

                if config.col_color.active and config.col_color.col in all_cols:
                    color_values = dfg.get_column(config.col_color.col)
                    if len(set(color_values)) == 1:
                        common_color = get_color_from_swatch(color_values[0])
                    else:
                        unique = False
                        individual_colors = [get_color_from_swatch(elem) for elem in color_values]

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
            for group_tuple,dfg in df.group_by(group_cols, maintain_order=True):
                plot_group(group_tuple, dfg)
        else:
            plot_group(tuple(), df.clone())

        fig.update_layout(xaxis_title=config.plot.x_title, yaxis_title=config.plot.y_title)
        self.uiPlot(fig)
