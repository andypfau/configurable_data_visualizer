from .main_window_ui import MainWindowUi
from lib.config import Config

import os, pathlib
import sys
import logging
import polars as pl
import plotly.graph_objects as go



class MainWindow(MainWindowUi):

    def __init__(self, filenames: list[str]):
        super().__init__()

        config = Config.load('config_test.json')
        print(config.files)
        print(config.plot.x_title)
        #config = Config()
        #config.plot.x_title = 'f / GHz'

        # load files
        wdir = pathlib.Path('samples')
        dfs = []
        for path in wdir.glob('*.csv'):
            #config.files.append(path)
            dfs.append(pl.read_csv(path, separator=';', comment_prefix='#'))
        df: pl.DataFrame = pl.concat(dfs)

        fig = go.Figure()
        for (xparam,),dfg in df.group_by(['XParam']):
            freq = dfg.get_column('f/GHz').to_numpy()
            pset = dfg.get_column('PSet/dBm').to_numpy()
            pmeas = dfg.get_column('PMeas/dBm').to_numpy()
            name = f'X={xparam:.5g}'
            
            fig.add_trace(go.Scatter(x=[pset,freq/1e9], y=pmeas, name=name, mode='markers'))
        fig.update_layout(xaxis_title=config.plot.x_title, yaxis_title=config.plot.y_title)
        self.uiPlot(fig)
        
        #config.save('config_test.json')
