from .files_window_ui import FilesWindowUi
from lib.config import Config, Relation, Sort, FilterMode, ColumnRole, PlotType

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

import os
import pathlib
import re
import logging
from typing import Callable



class FilesWindow(FilesWindowUi):


    def __init__(self, callback_plot: Callable):
        super().__init__()
        self.config: Config = None
        self._callback_plot = callback_plot
    

    def show(self, config: Config):
        self.config = config
        self.ui_set_parameters(self.config.input.glob_dir, self.config.input.glob_pattern, self.config.input.glob_regex_include, self.config.input.glob_regex_exclude)
        self.load_files(select_config_files=True)
        super().show()
    

    def load_files(self, *, select_config_files: bool):
        try:
            if not self.config.input.glob_dir:
                raise RuntimeError(f'No directory defined')
            
            rex_include = re.compile(self.config.input.glob_regex_include) if self.config.input.glob_regex_include else None
            rex_exclude = re.compile(self.config.input.glob_regex_exclude) if self.config.input.glob_regex_exclude else None
            
            all_files = []
            selected_files = []
            for path in sorted(pathlib.Path(self.config.input.glob_dir).glob(self.config.input.glob_pattern)):
                all_files.append(path)
                if not select_config_files:
                    if rex_include and not rex_include.match(path.name):
                        continue
                    if rex_exclude and rex_exclude.match(path.name):
                        continue
                    selected_files.append(path)
            
            if select_config_files:
                selected_files = [pathlib.Path(f) for f in self.config.input.files]
            else:
                self.config.input.files = [str(path) for path in selected_files]
            
            self.ui_set_files(all_files, selected_files)

            self.config.autosave()
        
        except Exception as ex:
            self.config.input.files = []
            self.ui_set_files([], [])

            logging.error(f'Unable to load files ({ex})')


    def on_input_change(self):
        self.config.input.glob_dir, self.config.input.glob_pattern, self.config.input.glob_regex_include, self.config.input.glob_regex_exclude = self.ui_get_parameters()
        self.load_files(select_config_files=False)

    
    def on_plot(self):
        self.config.input.files = [str(p) for p in self.ui_get_selected_files()]
        self._callback_plot(self.config)
