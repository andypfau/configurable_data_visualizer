from .helpers.qt_helper import QtHelper
from .components.pivot_grid import PivotGrid

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *

import plotly.graph_objects as go



class MainWindowUi(QMainWindow):


    def __init__(self):
        super().__init__()
        self.setWindowTitle('Plot Experiment')

        self._ui_webview = QWebEngineView(parent=self)
        self._ui_webview.setMinimumSize(500,300)
        self._ui_pivot_grid = PivotGrid(self)
        self._ui_pivot_grid.setMinimumSize(200,200)
        self._ui_pivot_grid.userChange.connect(self.on_pivot_change)
        self._ui_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self._ui_splitter.addWidget(self._ui_webview)
        self._ui_splitter.addWidget(self._ui_pivot_grid)
        self._ui_splitter.setStretchFactor(0, 5)
        self.setCentralWidget(QtHelper.layout_widget_h(self._ui_splitter))


    def uiPivotGrid(self) -> PivotGrid:
        return self._ui_pivot_grid


    def uiPlot(self, fig: go.Figure):
        htm = fig.to_html(include_plotlyjs='cdn', full_html=True)
        self._ui_webview.setHtml(htm)


    def on_pivot_change(self):
        pass
