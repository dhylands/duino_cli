#!/usr/bin/env python3
"""Implements a logging formatter which produces colorized output, suitable
for use on an ANSI console.

"""

import argparse
import logging
import sys
import time

from duino_cli.colors import Color
from duino_cli.log_setup import log_setup

# Colors to print to the console for a given warning level. %(color)s will be
# replaced with the color indicated for a given warning level.

COLORS = {
        'WARNING': Color.WARNING_COLOR,
        'INFO': Color.INFO_COLOR,
        'DEBUG': Color.DEBUG_COLOR,
        'CRITICAL': Color.CRITICAL_COLOR,
        'ERROR': Color.ERROR_COLOR
}

# Single letter code to print using %(levelchar)s

LEVELCHAR = {'WARNING': 'W', 'INFO': 'I', 'DEBUG': 'D', 'CRITICAL': 'C', 'ERROR': 'E'}


class ColoredFormatter(logging.Formatter):
    """A formatter which produces colized messages (using ANSI escape
    sequences) for the console.

    """

    def __init__(self, *args, use_color=True, **kwargs):
        #if "strm" in kwargs:
        #    kwargs['stream'] = kwargs.pop("strm")
        logging.Formatter.__init__(self, *args, **kwargs)
        self.use_color = use_color

    def format(self, record):
        """Add support for %(color)s and %(nocolor)s where the color is
        determined by the logging level.

        """
        levelname = record.levelname
        record.levelchar = LEVELCHAR[levelname]
        if self.use_color:
            record.color = COLORS[levelname]
            if len(record.color) == 0:  # type: ignore
                record.nocolor = ""
            else:
                record.nocolor = Color.NO_COLOR
        else:
            record.color = ""
            record.nocolor = ""

        return logging.Formatter.format(self, record)

    def formatTime(self, record, datefmt=None):
        """Override the default formatTime because we don't want the
        comma before the milliseconds, and for most stuff, I really
        don't want the date.

        """
        rectime = self.converter(record.created)
        if datefmt:
            return time.strftime(datefmt, rectime)
        return f'{time.strftime("%H:%M:%S", rectime)}{record.msecs}'


def test_main():
    """Test (put into a function so that pylint doesn't complain about
    variables being constants).

    """
    parser = argparse.ArgumentParser(
            prog="log-test",
            usage="%(prog)s [options]",
            description="Testing for the loggind module"
    )
    parser.add_argument(
            "-d",
            "--debug",
            dest="debug",
            action="store_true",
            help="Enable debug features",
            default=False
    )
    args = parser.parse_args(sys.argv[1:])

    log_setup(cfg_path='../logging.cfg')
    log = logging.getLogger()

    if args.debug:
        log.setLevel(logging.DEBUG)

    # You can now start issuing logging statements in your code
    log.debug('debug message')  # This won't print to myapp.log
    log.info('info message')  # Neither will this.
    log.warning('Checkout this warning.')  # This will show up in the log file.
    log.error('An error goes here.')  # and so will this.
    log.critical('Something critical happened.')  # and this one too.


if __name__ == "__main__":
    test_main()
