import logging


def get_logger(log_fp: str, logger_name: str = 'inspector') -> logging.Logger:
    logger = logging.getLogger(logger_name)
    sh = logging.StreamHandler()
    fh = logging.FileHandler(log_fp, mode='a')
    fmt = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    logger.setLevel(logging.INFO)
    sh.setLevel(logging.INFO)
    fh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    fh.setFormatter(fmt)
    logger.addHandler(sh)
    logger.addHandler(fh)
    return logger


Logger = logging.Logger
