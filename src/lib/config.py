from __future__ import annotations

from .base_config import BaseConfig

import enum
from typing import Any



class Relation(enum.StrEnum):
    Equal = '=='
    NotEqual = '!='
    Greater = '>'
    GreaterOrEqual = '>='
    Less = '<'
    LessOrEqual = '<='
    In = 'in'
    NotIn = 'not in'



class Sort(enum.StrEnum):
    Off = 'off'
    Asc = 'ascending'
    Desc = 'descending'



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


    class Filter(BaseConfig):
        
        def __init__(self, col: str = '', rel: Relation = Relation.Equal, value: Any = 0, value2: Any = 0, active: bool = True, expression: str = ''):
            super().__init__()

            self.active: bool = active
            self.col: str = col
            self.rel: Relation = rel
            self.value: Any = value
            self.value2: Any = value2
            self.expression: str = expression
        
        def as_str(self, max_len: int = 25) -> str:
            if self.expression:
                if len(self.expression) > max_len - 1:
                    return self.expression[:max_len-1] + '…'
                else:
                    return self.expression
            else:
                value_str = f'{self.value:.5g}' if isinstance(self.value,(int,float)) else str(self.value)
                value2_str = f'{self.value2:.5g}' if isinstance(self.value2,(int,float)) else str(self.value2)
                match self.rel:
                    case Relation.Equal: return f'= {value_str}'
                    case Relation.NotEqual: return f'≠ {value_str}'
                    case Relation.Greater: return f'> {value_str}'
                    case Relation.GreaterOrEqual: return f'≥ {value_str}'
                    case Relation.Less: return f'< {value_str}'
                    case Relation.LessOrEqual: return f'≤ {value_str}'
                    case Relation.In: return f'{value_str}..{value2_str}'
                    case Relation.NotIn: return f'!{value_str}..{value2_str}'
            raise RuntimeError()



    class PlotCol(BaseConfig):
        
        def __init__(self, col: str = '', active: bool = True):
            super().__init__()

            self.active: bool = active
            self.col: str = col



    class SortablePlotCol(BaseConfig):
        
        def __init__(self, col: str = '', sort: Sort = Sort.Off, active: bool = True):
            super().__init__()

            self.active: bool = active
            self.col: str = col
            self.sort: Sort = sort


    def __init__(self):
        super().__init__(format_version_str='Plot Experiment Config v0.1')
        
        self.files = Config.Files()
        self.filters: list[Config.Filter] = BaseConfig.ConfigList[Config.Filter](Config.Filter)
        self.cols_group: list[Config.SortablePlotCol] = BaseConfig.ConfigList[Config.SortablePlotCol](Config.SortablePlotCol)
        self.cols_color: list[Config.SortablePlotCol] = BaseConfig.ConfigList[Config.SortablePlotCol](Config.SortablePlotCol)
        self.cols_x: list[Config.SortablePlotCol] = BaseConfig.ConfigList[Config.SortablePlotCol](Config.SortablePlotCol)
        self.cols_y: list[Config.PlotCol] = BaseConfig.ConfigList[Config.PlotCol](Config.PlotCol)
        self.plot = Config.Plot()
