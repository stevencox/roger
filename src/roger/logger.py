import logging

import sys

from typing import Optional

from roger.config import get_default_config



logger: Optional[logging.Logger] = None

# HTTP plumbing that logs per-request at DEBUG. requests_cache alone emitted
# ~84% of the lines in an annotate task (5 per HTTP call: cache directives,
# pre-read, post-read, pre-write, skipping-write), which is how a single
# long-running task produced a 2.9 GB log file -- big enough to evict the
# api-server, whose ephemeral-storage limit is 750Mi, when someone opened it
# in the UI. Silenced independently of roger's own level so that
# logging.level: DEBUG stays usable for debugging roger.
NOISY_LOGGERS = (
    'requests_cache',
    'httpcore',
    'httpx',
    'urllib3.connectionpool',
    'elastic_transport',
)
NOISY_LOGGER_LEVEL = logging.WARNING


def quiet_noisy_loggers(level: int = NOISY_LOGGER_LEVEL) -> None:
    """Cap the per-request DEBUG chatter from HTTP libraries.

    Children are set explicitly rather than left to inherit: a child that
    already has a level of its own ignores the parent, and these libraries
    log from submodules (requests_cache.policy.actions, httpcore.http11).
    """
    existing = list(logging.root.manager.loggerDict)
    for prefix in NOISY_LOGGERS:
        logging.getLogger(prefix).setLevel(level)
        for name in existing:
            if name.startswith(prefix + '.'):
                logging.getLogger(name).setLevel(level)


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

        config = get_default_config()

        logger = logging.getLogger(name)

        handler = logging.StreamHandler(sys.stdout)

        formatter = logging.Formatter(config['logging']['format'])

        handler.setFormatter(formatter)

        logger.addHandler(handler)

        logger.setLevel(config['logging']['level'])

        logger.propagate = True

    return logger

