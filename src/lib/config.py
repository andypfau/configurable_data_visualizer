from __future__ import annotations

from .base_config import BaseConfig

import enum
import polars
import pathlib
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



class FilterMode(enum.StrEnum):
    Off = 'off'
    Values = 'values'
    Expression = 'expression'
    Comparison = 'comparison'



class TraceStyle(enum.StrEnum):
    Lines = 'lines'
    Markers = 'markers'
    Both = 'both'



class ColumnRole(enum.IntFlag):
    Off = 0
    Group = 1
    X = 2
    Y = 4
    Color = 8
    Style = 16
    Size = 32



class ConfigInput(BaseConfig):
    glob_dir: str = None
    glob_pattern: str = ''
    glob_regex_include: str = ''
    glob_regex_exclude: str = ''
    files: list[str] = []



class ConfigPlot(BaseConfig):
    x_title: str = 'X'
    y_title: str = 'Y'



class ConfigFilter(BaseConfig):
    
    mode: FilterMode = FilterMode.Off
    values: list[Any] = []
    expression: str = ''
    rel: Relation = Relation.Equal
    value: Any = 0
    value2: Any = 0
    

    def as_str(self) -> str:
        if self.mode == FilterMode.Expression:
            return self.expression
        elif self.mode == FilterMode.Values:
            return ','.join([str(v) for v in self.values])
        elif self.mode == FilterMode.Comparison:
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
        return ''



class ConfigColumnSetup(BaseConfig):
    col: str = ''
    filter: ConfigFilter = ConfigFilter()
    sort: Sort = Sort.Off
    assignment: ColumnRole = ColumnRole.Off
    activation: ColumnRole = ColumnRole.Off
    continuous: bool = False  # TODO: implement
    
    error: bool = BaseConfig.Volatile(False)



class Config(BaseConfig):
    
    input: ConfigInput = ConfigInput()
    all_files: list[pathlib.Path] = BaseConfig.Volatile([])
    
    raw_df: polars.LazyFrame = BaseConfig.Volatile(polars.LazyFrame())
    columns: list[str] = BaseConfig.Volatile([])
    df: polars.DataFrame = BaseConfig.Volatile(polars.DataFrame())

    col_setups: list[ConfigColumnSetup] = []

    plot: ConfigPlot = ConfigPlot()


    def __init__(self):
        super().__init__(format_version_str='Plot Experiment Config v0.1')

    def ensure_all_col_setups_exist(self):
        for col in self.columns:
            found = False
            for col_setup in self.col_setups:
                if col_setup.col == col:
                    found = True
                    break
            if not found:
                self.col_setups.append(ConfigColumnSetup())

    def find_setup(self, col: str) -> ConfigColumnSetup:
        for col_setup in self.col_setups:
            if col_setup.col == col:
                return col_setup
        raise RuntimeError(f'No setup for column "<{col}>" found.')
