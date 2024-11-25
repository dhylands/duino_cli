"""Common setup code for logging."""

import os
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
