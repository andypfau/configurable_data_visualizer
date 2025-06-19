from .files_window import FilesWindow
from .plot_window import PlotWindow
from lib.config import Config

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

import plotly.graph_objects as go



class MainWindowManager:

    def __init__(self):
        self._files_window = FilesWindow(self.show_plot)
        self._plot_window = PlotWindow(self.show_files)

    
    def show_files(self, config: Config):
        self._plot_window.hide()
        self._files_window.show(config)

    
    def show_plot(self, config: Config):
        self._files_window.hide()
        self._plot_window.show(config)
