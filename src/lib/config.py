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
    Selection = 'selection'
    Expression = 'expression'
    Comparison = 'comparison'



class PlotType(enum.StrEnum):
    Scatter = 'scatter'
    StatMatrix = 'stat-matrix'
    Heatmap = 'heatmap'
    Scatter3D = 'scatter-3d'



class MatrixDiagonalPlotType(enum.StrEnum):
    Off = 'off'
    Histogram = 'histogram'
    RunSequence = 'run-sequence'



class MatrixTrianglePlotType(enum.StrEnum):
    Off = 'off'
    Scatter = 'scatter'
    QQ = 'qq'



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
    csv_separator: str = ','



class ConfigPlot(BaseConfig):
    type: PlotType = PlotType.Scatter
    matrix_diagonal_type: MatrixDiagonalPlotType = MatrixDiagonalPlotType.Histogram
    matrix_lower_triangle_type: MatrixTrianglePlotType = MatrixTrianglePlotType.Off
    matrix_upper_triangle_type: MatrixTrianglePlotType = MatrixTrianglePlotType.Scatter
    scatter_lines: bool = True
    x_title: str = ''
    y_title: str = ''
    z_title: str = ''



class ConfigFilter(BaseConfig):
    
    mode: FilterMode = FilterMode.Off
    expression: str = ''
    cmp_rel: Relation = Relation.Equal
    cmp_value: Any = 0
    cmp_value2: Any = 0
    selection: list[Any] = []
    

    @staticmethod
    def _format(value, precision: int = 10):
        return f'{value:.{precision}g}' if isinstance(value,(int,float)) else str(value)
    
    def format(self) -> str:
        
        if self.mode == FilterMode.Expression:
            return self.expression
        
        elif self.mode == FilterMode.Selection:
            if len(self.selection) >= 3:
                return f'[{len(self.selection)}x]'
            else:
                return '[' + ','.join([ConfigFilter._format(v,3) for v in self.selection]) + ']'
        
        elif self.mode == FilterMode.Comparison:
            return self.format_comparison()

        return ''

    def format_comparison(self) -> str:
        value_str, value2_str = ConfigFilter._format(self.cmp_value), ConfigFilter._format(self.cmp_value2)
        match self.cmp_rel:
            case Relation.Equal: return f'= {value_str}'
            case Relation.NotEqual: return f'≠ {value_str}'
            case Relation.Greater: return f'> {value_str}'
            case Relation.GreaterOrEqual: return f'≥ {value_str}'
            case Relation.Less: return f'< {value_str}'
            case Relation.LessOrEqual: return f'≤ {value_str}'
            case Relation.In: return f'{value_str} … {value2_str}'
            case Relation.NotIn: return f'! {value_str} … {value2_str}'
        raise ValueError()

    def parse_comparison(self, s: str, set_mode_to_comparison: bool = True) -> Self:
        
        REX_FLOAT = r'[-+]?(?:\d+\.?|\.\d)\d*(?:[Ee][-+]?\d+)?'

        s_stripped = s.strip()
        mode = FilterMode.Comparison if set_mode_to_comparison else self.mode

        for op,rel in [('=',Relation.Equal), ('!=',Relation.NotEqual), ('>',Relation.Greater), (r'≥|>=',Relation.GreaterOrEqual), ('<',Relation.Less), (r'≤|<=',Relation.LessOrEqual)]:
            if m := re.match(r'^(' + op + r')\s*(' + REX_FLOAT + r')$', s_stripped):
                self.mode, self.cmp_rel = mode, rel
                self.cmp_value = float(m.group(2))
                return self
        
        for op,rel in [('',Relation.In), ('!|~',Relation.NotIn)]:
            if m := re.match(r'^(' + op + r')\s*(' + REX_FLOAT + r')\s*(\.\.\.?|…)\s*(' + REX_FLOAT + r')$', s_stripped):
                self.mode, self.cmp_rel = mode, rel
                self.cmp_value, self.cmp_value2 = float(m.group(2)), float(m.group(4))
                return self

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
    Unassigned = enum.auto()
    Group = enum.auto()
    X = enum.auto()
    Y = enum.auto()
    Z = enum.auto()



class Config(BaseConfig):
    
    input: ConfigInput = ConfigInput()
    col_setups: list[ConfigColumnSetup] = []
    cols_group: list[ColumnSwitch] = []
    cols_x: list[ColumnSwitch] = []
    cols_y: list[ColumnSwitch] = []
    cols_z: list[ColumnSwitch] = []
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
        all_cols = set(self._all_columns)
        available_cols = set([setup.col for setup in self.col_setups])
        missing_cols = all_cols - available_cols
        for col in missing_cols:
            setup = ConfigColumnSetup()
            setup.col = col
            self.col_setups.append(setup)


    def find_setup(self, col: str) -> ConfigColumnSetup:
        for col_setup in self.col_setups:
            if col_setup.col == col:
                return col_setup
        raise RuntimeError(f'No setup for column "{col}" found.')

    def get_switches(self, role: ColumnRole) -> list[ColumnSwitch]:
        match role:
            case ColumnRole.Group: return self.cols_group
            case ColumnRole.X: return self.cols_x
            case ColumnRole.Y: return self.cols_y
            case ColumnRole.Z: return self.cols_z
        raise ValueError()

    def set_switches(self, role: ColumnRole, switches: list[ColumnSwitch]):
        match role:
            case ColumnRole.Group: self.cols_group = switches
            case ColumnRole.X: self.cols_x = switches
            case ColumnRole.Y: self.cols_y = switches
            case ColumnRole.Z: self.cols_z = switches
            case _: raise ValueError()

    def get_switch(self, role: ColumnRole, index: int) -> ColumnSwitch:
        list = self.get_switches(role)
        if index >= len(list):
            raise ValueError()  # TODO: return None instead?
        return list[index]

    def get_column_values(self, col: str) -> list[str]:
        if col not in self._column_values:
            if col not in self._all_columns:
                raise RuntimeError()
            self._column_values[col] = list(sorted(self.raw_df.get_column(col).unique()))
        return self._column_values[col]
