
import logging
import sys
from os import path
import json
from typing import Dict, Any, Optional

import requests
import yaml

config: Optional[Dict[str, Any]] = None
logger: Optional[logging.Logger] = None

CONFIG_FILENAME = path.join(path.dirname(path.abspath(__file__)), 'config.yaml')

def get_config(filename: str = CONFIG_FILENAME) -> dict:
    """
    Get config as a dictionary

    Parameters
    ----------
    filename: str
        The filename with all the configuration

    Returns
    -------
    dict
        A dictionary containing all the entries from the config YAML

    """
    global config
    if config is None:
        config = yaml.load(open(filename), Loader=yaml.FullLoader)
    return config

def get_logger(name: str = 'roger') -> logging.Logger:
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
        logger.setLevel(config['logging']['level'])
        logger.propagate = False
    return logger
