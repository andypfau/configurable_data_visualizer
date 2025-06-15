from gui.main_window import MainWindow

from PyQt6 import QtWidgets

import sys
import logging


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    try:
        app = QtWidgets.QApplication(sys.argv)
        filenames = sys.argv[1:]
        MainWindow(filenames).show()
        app.exec()

    except Exception as ex:
        logging.exception(f'Unhandled error: {ex}')
