import logging
import sys
from typing import Optional
from roger.roger_util import get_default_config as get_config
logger: Optional[logging.Logger] = None


def get_logger(name: str = 'dug') -> logging.Logger:
    """
    Get an instance of logger.
    Parameters
    ----------
    name: str
        The name of logger
    Returns
    -------
    logging.Logger
        An instance of logging.Logger
    """
    global logger
    if logger is None:
        config = get_config()
        logger = logging.getLogger(name)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(config['logging']['format'])
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel('DEBUG')
        logger.propagate = False
    return logger
