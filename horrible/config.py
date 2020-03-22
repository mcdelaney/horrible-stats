import logging
from pathlib import Path

def get_logger() -> logging.Logger:
    log = logging.getLogger('horrible')
    log.setLevel(logging.INFO)
    logFormatter = logging.Formatter(
        "%(asctime)s [%(name)s] [%(levelname)-5.5s]  %(message)s")
    file_path = Path(f"log/{log.name}.log")
    if not file_path.parent.exists():
        file_path.parent.mkdir()
    fileHandler = logging.FileHandler(file_path, 'w')
    fileHandler.setFormatter(logFormatter)
    log.addHandler(fileHandler)
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    log.addHandler(consoleHandler)
    log.propagate = False
    return log

log = get_logger()