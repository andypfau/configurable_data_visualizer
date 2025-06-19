from gui.main_window_manager import MainWindowManager
from lib.config import Config

from PyQt6 import QtWidgets

import sys
import logging


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    try:
        app = QtWidgets.QApplication(sys.argv)
        filenames = sys.argv[1:]

        config = Config()
        if len(filenames) >= 1:
            initial_file = filenames[0]
            try:
                config = Config().load(initial_file)
                config.filename = initial_file
            except Exception as ex:
                logging.error(f'Unable to load <{initial_file}> ({ex})')
        
        MainWindowManager().show_files(config)
        app.exec()

    except Exception as ex:
        logging.exception(f'Unhandled error: {ex}')
