from __future__ import annotations

from .base_config import BaseConfig

import enum
from typing import Any



class Relation(enum.StrEnum):
    Eq = enum.auto()
    NEq = enum.auto()
    Gr = enum.auto()
    GrEq = enum.auto()
    Le = enum.auto()
    LeEq = enum.auto()
    In = enum.auto()
    NIn = enum.auto()



class Config(BaseConfig):


    class Files(BaseConfig):
        
        def __init__(self):
            super().__init__()

            self.glob_dir: str = None
            self.glob_pattern: str = ''
            self.glob_regex_include: str = ''
            self.glob_regex_exclude: str = ''
            self.files: list[str] = []


    class Plot(BaseConfig):
        
        def __init__(self):
            super().__init__()

            self.x_title: str = 'X'
            self.y_title: str = 'Y'


    class ColFilter(BaseConfig):
        
        def __init__(self, col: str = '', rel: Relation = Relation.Eq, value: Any = 0, value2: Any = 0, active: bool = True, expression: str = ''):
            super().__init__()

            self.active: bool = active
            self.col: str = col
            self.rel: Relation = rel
            self.value: Any = value
            self.value2: Any = value2
            self.expression: str = expression


    class PlotCol(BaseConfig):
        
        def __init__(self, col: str = '', unit: str = '', active: bool = True):
            super().__init__()

            self.active: bool = active
            self.col: str = col


    class SortCol(BaseConfig):
        
        def __init__(self, col: str = '', descending: bool = False):
            super().__init__()

            self.col: str = col
            self.descending: bool = descending


    def __init__(self):
        super().__init__(format_version_str='Plot Experiment Config v0.1')
        
        self.files = Config.Files()
        self.sort: list[Config.SortCol] = BaseConfig.ConfigList(Config.SortCol)
        self.filters: list[Config.ColFilter] = BaseConfig.ConfigList[Config.ColFilter](Config.ColFilter)
        self.cols_group: list[Config.PlotCol] = BaseConfig.ConfigList[Config.PlotCol](Config.PlotCol)
        self.cols_x: list[Config.PlotCol] = BaseConfig.ConfigList[Config.PlotCol](Config.PlotCol)
        self.cols_y: list[Config.PlotCol] = BaseConfig.ConfigList[Config.PlotCol](Config.PlotCol)
        self.cols_color: list[Config.PlotCol] = BaseConfig.ConfigList[Config.PlotCol](Config.PlotCol)
        self.plot = Config.Plot()
