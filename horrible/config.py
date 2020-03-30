import logging
from pathlib import Path

def get_logger(name='horrible') -> logging.Logger:
    log = logging.getLogger(name)
    log.setLevel(logging.INFO)
    logFormatter = logging.Formatter(
        "%(asctime)s [%(name)s] [%(levelname)-5.5s]  %(message)s")
    file_path = Path(f"log/{log.name}.log")

    if not file_path.parent.exists():
        file_path.parent.mkdir()

    if (len(log.handlers) == 2):
        return log

    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    fileHandler = logging.FileHandler(file_path, 'w')
    fileHandler.setFormatter(logFormatter)
    log.addHandler(fileHandler)
    log.addHandler(consoleHandler)
    log.propagate = False
    return log
