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

        self._ui_central_widget = QWidget()
        self.setCentralWidget(self._ui_central_widget)
        self._ui_layout = QVBoxLayout(self._ui_central_widget)

        self.ui_webview = QWebEngineView()
        self._ui_layout.addWidget(self.ui_webview)


    def uiPlot(self, fig: go.Figure):
        htm = fig.to_html(include_plotlyjs='cdn', full_html=True)
        self.ui_webview.setHtml(htm)
