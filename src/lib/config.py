from __future__ import annotations

from .base_config import BaseConfig

import enum
import polars
import pathlib
import re
from typing import Any, Callable, Self



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
    

    @staticmethod
    def _format(value):
        return f'{value:.8g}' if isinstance(value,(int,float)) else str(value)
    
    def format(self) -> str:
        
        if self.mode == FilterMode.Expression:
            return self.expression
        
        elif self.mode == FilterMode.Values:
            return ','.join([ConfigFilter._format(v) for v in self.values])
        
        elif self.mode == FilterMode.Comparison:
            return self.format_comparison()

        return ''

    def format_comparison(self) -> str:
        value_str, value2_str = ConfigFilter._format(self.value), ConfigFilter._format(self.value2)
        match self.rel:
            case Relation.Equal: return f'= {value_str}'
            case Relation.NotEqual: return f'≠ {value_str}'
            case Relation.Greater: return f'> {value_str}'
            case Relation.GreaterOrEqual: return f'≥ {value_str}'
            case Relation.Less: return f'< {value_str}'
            case Relation.LessOrEqual: return f'≤ {value_str}'
            case Relation.In: return f'{value_str} ... {value2_str}'
            case Relation.NotIn: return f'! {value_str} ... {value2_str}'
        raise ValueError()

    def parse_comparison(self, s: str, set_mode_to_comparison: bool = True) -> Self:
        
        REX_FLOAT = r'[-+]?(?:\d+\.?|\.\d)\d*(?:[Ee][-+]?\d+)?'

        s_stripped = s.strip()
        mode = FilterMode.Comparison if set_mode_to_comparison else self.mode

        for op,rel in [('=',Relation.Equal), ('!=',Relation.NotEqual), ('>',Relation.Greater), ('>=',Relation.GreaterOrEqual), ('<',Relation.Less), ('<=',Relation.LessOrEqual)]:
            if m := re.match(r'^' + op + r'\s*(' + REX_FLOAT + r')$', s_stripped):
                self.mode, self.rel = mode, rel
                self.value = float(m.group(1))
        
        for op,rel in [('',Relation.In), ('!',Relation.NotIn)]:
            if m := re.match(r'^' + op + r'\s*(' + REX_FLOAT + r')\s*\.\.\.?\s*(' + REX_FLOAT + r')$', s_stripped):
                self.mode, self.rel = mode, rel
                self.value, self.value2 = float(m.group(1)), float(m.group(2))

        raise ValueError(f'Unable to parse comparison "{s}"')



class ConfigColumnSetup(BaseConfig):
    col: str = ''
    filter: ConfigFilter = ConfigFilter()
    sort: Sort = Sort.Off
    as_color: bool = False
    as_size: bool = False
    as_style: bool = False
    continuous: bool = False  # TODO: implement
    
    error: bool = BaseConfig.Volatile(False)



class ColumnSwitch(BaseConfig):
    col: str = ''
    active: bool = True



class ColumnRole(enum.Enum):
    AllColumns = enum.auto()
    Group = enum.auto()
    X = enum.auto()
    Y = enum.auto()



class Config(BaseConfig):
    
    input: ConfigInput = ConfigInput()
    col_setups: list[ConfigColumnSetup] = []
    cols_group: list[ColumnSwitch] = []
    cols_x: list[ColumnSwitch] = []
    cols_y: list[ColumnSwitch] = []
    plot: ConfigPlot = ConfigPlot()


    def __init__(self):
        super().__init__(format_version_str='Plot Experiment Config v0.1')
        self._all_files: list[str] = []
        self._raw_df: polars.DataFrame|None = None
        self._df: polars.DataFrame|None = None
        self._all_columns: list[str] = []
        self._column_values: dict[str,list[str]] = {}

    @property
    def all_files(self) -> list[str]:
        return self._all_files
    @all_files.setter
    def all_files(self, value: list[str]):
        self._all_files = value

    @property
    def raw_df(self) -> polars.DataFrame:
        if self._raw_df is None:
            raise RuntimeError()
        return self._raw_df
    @raw_df.setter
    def raw_df(self, value: polars.DataFrame):
        self._raw_df = value
        self._all_columns = self.raw_df.columns
        self._column_values = {}
        self._df = None
        self._ensure_setups_exist()

    @property
    def df(self) -> polars.DataFrame:
        if self._df is None:
            raise RuntimeError()
        return self._df
    @df.setter
    def df(self, value: polars.DataFrame):
        self._df = value

    @property
    def all_columns(self) -> list[str]:
        assert self._all_columns is not None, 'Config not initialized'
        return self._all_columns

    def _ensure_setups_exist(self):
        for col in self._all_columns:
            found = False
            for col_setup in self.col_setups:
                if col_setup.col == col:
                    found = True
                    break
            if not found:
                setup = ConfigColumnSetup()
                setup.col = col
                self.col_setups.append(setup)


    def find_setup(self, col: str) -> ConfigColumnSetup:
        for col_setup in self.col_setups:
            if col_setup.col == col:
                return col_setup
        raise RuntimeError(f'No setup for column "<{col}>" found.')

    def has_role(self, col: str, role: ColumnRole) -> bool:
        match role:
            case ColumnRole.Group: return col in [c.col for c in self.cols_group]
            case ColumnRole.X: return col in [c.col for c in self.cols_x]
            case ColumnRole.Y: return col in [c.col for c in self.cols_y]
            case _: raise ValueError()
    def set_role(self, col: str, role: ColumnRole, has_role: bool = True):
        if has_role and not self.has_role(col, role):
            sw = ColumnSwitch()
            sw.col = col
            sw.active = True
            match role:
                case ColumnRole.Group: self.cols_group = [*self.cols_group, sw]
                case ColumnRole.X: self.cols_x = [*self.cols_x, sw]
                case ColumnRole.Y: self.cols_y = [*self.cols_y, sw]
                case _: raise ValueError()
        elif (not has_role) and self.has_role(col, role):
            match role:
                case ColumnRole.Group: self.cols_group = [c for c in self.cols_group if c.col!=col]
                case ColumnRole.X: self.cols_x = [c for c in self.cols_x if c.col!=col]
                case ColumnRole.Y: self.cols_y = [c for c in self.cols_y if c.col!=col]
                case _: raise ValueError()

    def get_column_values(self, col: str) -> list[str]:
        if col not in self._column_values:
            if col not in self._all_columns:
                raise RuntimeError()
            self._column_values[col] = list(sorted(self.raw_df.get_column(col).unique()))
        return self._column_values[col]
