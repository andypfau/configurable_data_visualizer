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
        self._ui_lines_cb = QCheckBox('Lines')
        self._ui_lines_cb.checkStateChanged.connect(self.on_lines_change)
        self._ui_label = QLineEdit()
        self._ui_label.setReadOnly(True)
        self._ui_pivot_grid = PivotGrid(self)
        self._ui_pivot_grid.setMinimumSize(200,200)
        self._ui_pivot_grid.userChange.connect(self.on_pivot_change)
        
        self._ui_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self._ui_splitter.addWidget(QtHelper.layout_widget_v(
            QtHelper.layout_h(self._ui_lines_cb, self._ui_label),
            self._ui_webview
        ))
        self._ui_splitter.addWidget(self._ui_pivot_grid)
        self._ui_splitter.setStretchFactor(0, 5)
        self.setCentralWidget(QtHelper.layout_widget_h(self._ui_splitter))
        
        self.ui_set_label(None)


    def ui_pivot_grid(self) -> PivotGrid:
        return self._ui_pivot_grid


    def ui_plot(self, fig: go.Figure):
        htm = fig.to_html(include_plotlyjs='cdn', full_html=True)
        self._ui_webview.setHtml(htm)

    
    def ui_set_label(self, value: str):
        if value:
            self._ui_label.setText(value)
            self._ui_label.setVisible(True)
        else:
            self._ui_label.setVisible(False)
    

    def ui_get_lines(self) -> bool:
        return self._ui_lines_cb.isChecked()
    def ui_set_lines(self, value: bool):
        self._ui_lines_cb.checkStateChanged.disconnect(self.on_lines_change)
        self._ui_lines_cb.setChecked(value)
        self._ui_lines_cb.checkStateChanged.connect(self.on_lines_change)



    def on_pivot_change(self):
        pass
    def on_lines_change(self):
        pass
