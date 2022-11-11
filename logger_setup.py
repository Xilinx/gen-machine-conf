import logging
import sys

logger = None
format = logging.Formatter("[%(levelname)s] %(message)s")


def setup_logger():
    global logger
    if logger:
        return logger
    logger = logging.getLogger('')
    logger.setLevel(logging.DEBUG)

    console_h = logging.StreamHandler(sys.stdout)
    console_h.setLevel(logging.INFO)
    console_h.setFormatter(format)
    logger.addHandler(console_h)

    return logger, console_h


def setup_logger_file(filename):
    global logger
    file_h = logging.FileHandler(filename)
    file_h.setLevel(logging.DEBUG)
    file_h.setFormatter(format)
    logger.addHandler(file_h)
