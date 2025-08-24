"""Common setup code for logging."""

import os
import logging
import logging.config
import yaml

# Provide a default logging config that will be used if the user doesn't
# provide one.
DEFAULT_LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(message)s',
        },
        'simple-color': {
            '()': 'duino_cli.colored_formatter.ColoredFormatter',
            'format': '%(color)s%(message)s%(nocolor)s',
        },
    },
    'handlers': {
        'console-simple': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'simple',
            'stream': 'ext://sys.stdout',
        },
        'console-simple-color': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'simple-color',
            'stream': 'ext://sys.stdout',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console-simple-color'],
    }
}


def log_setup(cfg_path='logging.cfg', level=logging.INFO, cfg_env='LOG_CFG', color=True):
    """Sets up the logging based on the logging.cfg file. You can
    override the path using the LOG_CFG environment variable.

    """
    value = os.getenv(cfg_env, None)
    if value:
        cfg_path = value
    if os.path.exists(cfg_path):
        with open(cfg_path, 'r', encoding='utf-8') as cfg_file:
            config = yaml.safe_load(cfg_file.read())
        logging.config.dictConfig(config)
    else:
        if color:
            handler = 'console-simple-color'
        else:
            handler = 'console-simple'
        DEFAULT_LOGGING_CONFIG['root']['level'] = logging.getLevelName(level)
        DEFAULT_LOGGING_CONFIG['root']['handlers'] = [handler]
        logging.config.dictConfig(DEFAULT_LOGGING_CONFIG)
    logging.getLogger().setLevel(level)
    add_logging_level('GOOD', logging.INFO + 1)


def add_logging_level(level_name, level_num, method_name=None):
    """
    Comprehensively adds a new logging level to the `logging` module and the
    currently configured logging class.

    `level_name` becomes an attribute of the `logging` module with the value
    `level_num`. `methodName` becomes a convenience method for both `logging`
    itself and the class returned by `logging.getLoggerClass()` (usually just
    `logging.Logger`). If `methodName` is not specified, `level_name.lower()` is
    used.

    To avoid accidental clobberings of existing attributes, this method will
    raise an `AttributeError` if the level name is already an attribute of the
    `logging` module or if the method name is already present

    Example
    -------
    >>> ad_lLogging_level('TRACE', logging.DEBUG - 5)
    >>> logging.getLogger(__name__).setLevel("TRACE")
    >>> logging.getLogger(__name__).trace('that worked')
    >>> logging.trace('so did this')
    >>> logging.TRACE
    5

    This function orignated from:
    https://stackoverflow.com/questions/2183233/how-to-add-a-custom-loglevel-to-pythons-logging-facility/35804945#35804945
    """
    if not method_name:
        method_name = level_name.lower()

    if hasattr(logging, level_name):
        raise AttributeError(f'{level_name} already defined in logging module')
    if hasattr(logging, method_name):
        raise AttributeError(f'{method_name} already defined in logging module')
    if hasattr(logging.getLoggerClass(), method_name):
        raise AttributeError(f'{method_name} already defined in method_name class')

    # This method was inspired by the answers to Stack Overflow post
    # http://stackoverflow.com/q/2183233/2988730, especially
    # http://stackoverflow.com/a/13638084/2988730
    def log_for_level(self, message, *args, **kwargs):
        if self.isEnabledFor(level_num):
            self._log(level_num, message, args, **kwargs)  # pylint: disable=protected-access

    def log_to_root(message, *args, **kwargs):
        logging.log(level_num, message, *args, **kwargs)

    logging.addLevelName(level_num, level_name)
    setattr(logging, level_name, level_num)
    setattr(logging.getLoggerClass(), method_name, log_for_level)
    setattr(logging, method_name, log_to_root)
