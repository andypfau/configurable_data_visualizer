from lib.config import Config, Relation, Sort, FilterMode, ColumnRole, PlotType, MatrixDiagonalPlotType, MatrixTrianglePlotType
from lib.utils import reverse_lookup

import os, pathlib
import sys
import math
import re
import logging
import polars as pl
import numpy as np
import plotly, plotly.express, plotly.validators.scatter.marker
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Callable
import scipy.stats



class Plot:


    def __init__(self, config: Config):
        self._config = config
        self._color_map = {}
        self._marker_map = {}
        self._range_map = {}


    def plot(self) -> go.Figure:
        match self._config.plot.type:
            case PlotType.Scatter: return self.scatter()
            case PlotType.Heatmap: return self.scatter(segmented_y_axis=True)
            case PlotType.Scatter3D: return self.scatter(three_d=True)
            case PlotType.StatMatrix: return self.scatter_matrix()
            case _: raise RuntimeError()


    def scatter_matrix(self) -> go.Figure:

        df = self._config.df
        cols = self._extract('group', self._config.cols_group, lambda col: col.active, n_min=2)
        dim = len(cols)

        MAX_POINTS = 2_000

        def make_diagonal_plot(i: int):
            if self._config.plot.matrix_diagonal_type == MatrixDiagonalPlotType.Off:
                return
            loc = dict(row=i+1, col=i+1)
            data = df.get_column(cols[i]).to_numpy()
            if self._config.plot.matrix_diagonal_type == MatrixDiagonalPlotType.Histogram:
                hist, bin_edges = np.histogram(data, density=False, bins=math.ceil(5*math.log(len(data))))
                bins = (bin_edges[1:]+bin_edges[:-1])/2
                idx_empty = hist==0
                hist, bins = np.delete(hist,idx_empty), np.delete(bins,idx_empty)
                fig.add_trace(go.Bar(x=bins, y=hist), **loc)
                mean, sdev = np.mean(data), np.std(data,ddof=1)
                fig.add_vline(x=mean-sdev, line=dict(dash='dot', color='black'), **loc, opacity=0.67)
                fig.add_vline(x=mean, line=dict(dash='dashdot', color='black'), **loc, opacity=0.67)
                fig.add_vline(x=mean+sdev, line=dict(dash='dot', color='black'), **loc, opacity=0.67)
            elif self._config.plot.matrix_diagonal_type == MatrixDiagonalPlotType.RunSequence:
                if len(data) <= MAX_POINTS:
                    data_to_plot = data
                else:
                    data_to_plot = np.random.choice(data, size=MAX_POINTS)
                fig.add_trace(go.Scatter(y=data_to_plot), **loc)
                y0, y1 = np.min(data), np.max(data)
                ref_x = [0, len(data)-1]
                ref_y = [y0, y1]
                fig.add_trace(go.Scatter(x=ref_x, y=ref_y, mode='lines', line=dict(dash='dot', color='black'), opacity=0.33), **loc)
            else: raise ValueError()

        def make_triangle_plot(x: int, y: int, typ: MatrixTrianglePlotType):
            if typ == MatrixTrianglePlotType.Off:
                return
            loc = dict(row=x+1, col=y+1)
            data_x = df.get_column(cols[x]).to_numpy()
            data_y = df.get_column(cols[y]).to_numpy()
            x0, x1 = np.min(data_x), np.max(data_x)
            if typ == MatrixTrianglePlotType.Scatter:
                if len(data_x) <= MAX_POINTS:
                    data_x_to_plot, data_y_to_plot = data_x, data_y
                else:
                    indices = np.random.choice(np.linspace(0, len(data_x)-1, len(data_x), dtype=int), size=MAX_POINTS)
                    data_x_to_plot, data_y_to_plot = data_x[indices], data_y[indices]
                fig.add_trace(go.Scatter(x=data_x_to_plot, y=data_y_to_plot, mode='markers', marker=dict(opacity=0.5)), **loc)
                reg = scipy.stats.linregress(data_x, data_y)
                reg_x = [x0, x1]
                reg_y = [reg.intercept, reg.intercept+reg.slope*x1]
                fig.add_trace(go.Scatter(x=reg_x, y=reg_y, mode='lines', line=dict(dash='dash', color='black'), opacity=0.67), **loc)
            elif typ == MatrixTrianglePlotType.QQ:
                quant_x = np.percentile(data_x, np.linspace(0, 100, 101))
                quant_y = np.percentile(data_y, np.linspace(0, 100, 101))
                fig.add_trace(go.Scatter(x=quant_x, y=quant_y), **loc)
                y0, y1 = np.min(data_y), np.max(data_y)
                ref_x = [x0, x1]
                ref_y = [y0, y1]
                fig.add_trace(go.Scatter(x=ref_x, y=ref_y, mode='lines', line=dict(dash='dot', color='black'), opacity=0.33), **loc)
            elif typ == MatrixTrianglePlotType.Off:
                pass
            else: raise ValueError()

        fig = make_subplots(rows=dim, cols=dim)
        for x in range(dim):
            for y in range(dim):
                if x < y:
                    make_triangle_plot(x, y, self._config.plot.matrix_lower_triangle_type)
                elif x > y:
                    make_triangle_plot(x, y, self._config.plot.matrix_upper_triangle_type)
                else:
                    make_diagonal_plot(x)
        
        for x in range(dim):
            fig.update_xaxes(title_text=cols[x], row=dim, col=x+1)
            fig.update_yaxes(title_text=cols[x], row=x+1, col=1)
        
        fig.update_layout(showlegend=False)
        
        return fig


    def scatter(self, *, segmented_y_axis: bool = False, three_d: bool = False) -> go.Figure:

        df = self._config.df
        fig = go.Figure()

        group_cols = self._extract('group', self._config.cols_group, lambda col: col.active)
        x_cols = self._extract('X', self._config.cols_x, lambda col: col.active, n_min=1, n_max=1 if three_d else None)
        y_cols = self._extract('Y', self._config.cols_y, lambda col: col.active, n_min=1, n_max=1 if three_d else None)
        z_cols = self._extract('Z', self._config.cols_z, lambda col: col.active, n_min=1 if three_d else None, n_max=None if three_d else 1)
        color_col = self._extract('color', self._config.col_setups, lambda col: col.as_color, n_max=1, as_list=False)
        style_col = self._extract('style', self._config.col_setups, lambda col: col.as_style, n_max=0 if three_d else 1, as_list=False)
        size_col = self._extract('size', self._config.col_setups, lambda col: col.as_size, n_max=1, as_list=False)

        if len(x_cols)==0 or len(y_cols)==0:
            logging.warning(f'No columns to plot')
            return
        if three_d and style_col is not None:
            logging.warning(f'Style is ignored for 3D')
            style_col = None
        
        logging.info(f'Groups: {group_cols}; X: {x_cols}; Y: {y_cols}; Z: {z_cols}; Color: {color_col}; Style: {style_col}; Size: {size_col}')

        def plot_group(group_tuple: tuple, df: pl.DataFrame):
            
            def format(x):
                if isinstance(x, float):
                    return f'{x:.6g}'
                return str(x)

            def add_to_plot(x: np.ndarray, y: np.ndarray, z: np.ndarray|None=None, *, data_col: str|None=None, can_use_lines: bool=True):

                if len(group_tuple) == 1:
                    legend = format(group_tuple[0])
                else:
                    legend = ', '.join([f'{n}={format(v)}' for (n,v) in zip(group_cols,group_tuple)])
                infos = '<br>'.join([f'{n} = {format(v)}' for (n,v) in zip(group_cols,group_tuple)])

                if data_col is not None:
                    if len(y_cols) > 1:
                        legend = data_col + ' ' + legend
                    infos = data_col + '<br>' + infos
                
                common_color = None
                individual_colors = None
                if color_col is not None:
                    color_values = df.get_column(color_col)
                    if len(set(color_values)) == 1:
                        common_color = self._get_discrete_color(color_values[0])
                    else:
                        individual_colors = [self._get_discrete_color(elem) for elem in color_values]#
                
                common_markers = None
                individual_markers = None
                if style_col is not None:
                    style_values = df.get_column(style_col)
                    if len(set(style_values)) == 1:
                        common_markers = self._get_discrete_marker(style_values[0])
                    else:
                        individual_markers = [self._get_discrete_marker(elem) for elem in style_values]
                
                individual_sizes = None
                if size_col is not None:
                    size_values = df.get_column(size_col)
                    sizes = [self._get_relative_value(size_col, elem) for elem in size_values]
                    individual_sizes = np.array(sizes)

                line = dict()
                marker = dict()

                use_lines = can_use_lines and self._config.plot.scatter_lines
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

                if z is not None:
                    fig.add_trace(go.Scatter3d(x=x, y=y, z=z, name=legend, mode=mode, text=infos, line=line, marker=marker))
                else:
                    fig.add_trace(go.Scatter(x=x, y=y, name=legend, mode=mode, text=infos, line=line, marker=marker))

            x, x_unique = self._get_axis_values(df, x_cols)
            
            if three_d:
                y, y_unique = self._get_axis_values(df, y_cols)
                for z_col in z_cols:
                    z = df.get_column(z_col).to_numpy()
                    add_to_plot(x, y, z, data_col=z_col, can_use_lines=x_unique)

            elif segmented_y_axis:
                y, y_unique = self._get_axis_values(df, y_cols)
                
                add_to_plot(x, y, can_use_lines=x_unique and y_unique)

            else:

                for y_col in y_cols:
                    y = df.get_column(y_col).to_numpy()
                    add_to_plot(x, y, data_col=y_col, can_use_lines=x_unique)

        if len(group_cols) >= 1:
            for group_tuple,dfg in df.group_by(group_cols, maintain_order=True):
                plot_group(group_tuple, dfg)
        else:
            plot_group(tuple(), df)

        if three_d:
            fig.update_layout(scene = dict(
                xaxis = dict(title=self._make_title(self._config.plot.x_title, x_cols)),
                yaxis = dict(title=self._make_title(self._config.plot.y_title, y_cols)),
                zaxis = dict(title=self._make_title(self._config.plot.z_title, z_cols)),
            ))
        else:
            fig.update_layout(
                xaxis_title=self._make_title(self._config.plot.x_title, x_cols),
                yaxis_title=self._make_title(self._config.plot.y_title, y_cols)
            )
        return fig    
        

    def _get_color_swatch(self) -> list:
        return plotly.express.colors.qualitative.Plotly
    

    def _get_all_markers(self) -> list:
        all_symbols = plotly.validators.scatter.marker.SymbolValidator().values
        symbols_without_numers = [s for s in all_symbols if not re.match(r'^[0-9].*', str(s))]
        symbols_without_specials = [s for s in symbols_without_numers if '-' not in s]
        return symbols_without_specials
    

    def _get_discrete_color(self, col):
        if col not in self._color_map:
            available = self._get_color_swatch()
            self._color_map[col] = available[len(self._color_map) % len(available)]
        return self._color_map[col]


    def _get_discrete_marker(self, col):
        if col not in self._marker_map:
            available = self._get_all_markers()
            self._marker_map[col] = available[len(self._marker_map) % len(available)]
        return self._marker_map[col]


    def _get_relative_value(self, col, value):
        if col not in self._range_map:
            all_values = self._config.get_column_values(col)
            lo, hi = np.min(all_values), np.max(all_values)
            self._range_map[col] = (lo, hi)
        (lo, hi) = self._range_map[col]
        if lo==hi:
            return 0.5
        return (value - lo) / (hi-lo)


    def _get_axis_values(self, df: pl.DataFrame, cols: list[str]) -> tuple[np.ndarray,bool]:
        if len(cols) > 1:
            values = np.array([df.get_column(col).to_numpy() for col in cols])
            n_total = max(*[len(x1) for x1 in values])
            n_unique_per_group = [len(np.unique(x1)) for x1 in values]

        else:
            values = df.get_column(cols[0]).to_numpy()
            n_total = len(values)
            n_unique_per_group = [len(np.unique(values))]

        n_expected_total = np.prod(n_unique_per_group)
        if n_total == n_expected_total:
            unique = True
        else:
            cols_str = '"' + '"/"'.join(cols) + '"'
            logging.warning(f'In the axis values of column {cols_str}, there are {n_total} values, but only {n_expected_total} unique; you probably forgot some grouping or filtering')
            unique = False
        
        return values, unique

    
    def _make_title(self, config_str: str, cols: list[str]) -> str:
        if config_str:
            return config_str
        return ' | '.join(cols)

    
    def _extract(self, name: str, cols: list[str], predicate: Callable, n_min: int|None = None, n_max: int|None = None, as_list: bool = True):
        active_cols = [c for c in cols if predicate(c)]
        
        valid_cols = [c for c in active_cols if c.col in self._config.all_columns]
        for col in active_cols:
            if col not in valid_cols:
                logging.warning(f'Ignoring invalid column "{col.col}" for {name}')
        
        col_names = [c.col for c in valid_cols]
        
        if n_min is not None and len(col_names) < n_min:
            raise RuntimeError(f'Need at least {n_min} column(s) for {name}')
        if n_max is not None and len(col_names) > n_max:
            logging.warning(f'Ignoring multiple assignments for {name}; using "{col_names[0]}"')
        
        if as_list:
            return col_names
        else:
            assert n_max <= 1
            if len(col_names) == 0:
                return None
            else:
                return col_names[0]
