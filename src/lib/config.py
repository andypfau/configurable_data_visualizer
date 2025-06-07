from __future__ import annotations
from .base_config import BaseConfig



class Config(BaseConfig):

    class Plot(BaseConfig):
        def __init__(self):
            super().__init__()
            self.fields: list[str] = []
            self.x_title: str = 'X'
            self.y_title: str = 'Y'

    def __init__(self):
        super().__init__(format_version_str='Plot Experiment Config v0.1')
        self.files: list[str] = []
        self.plot: Config.Plot = Config.Plot()
