"""
Class for managing all command line output.
"""

import logging
import sys
from typing import List, Tuple, Union

from duino_bus.dump_mem import dump_mem

DEBUG = False


class CommandLineOutput:
    """A class which allows easy integration of printed output into logging
    and also allows for easy capture of the output for testing purposes.

    """

    def __init__(self, log: Union[logging.Logger, None] = None) -> None:
        self.captured_output: Union[List[Tuple[str, str]], None] = None
        self.error_count: int = 0
        self.fatal_count: int = 0
        self.buffered_output: str = ""
        self.log: logging.Logger = log or logging.getLogger(__name__)

    def set_capture_output(self, capture_output: bool) -> None:
        """Sets capture_output flag, which determines whether the logging
        output is captured or not.

        """
        if capture_output:
            self.captured_output = []
        else:
            self.captured_output = None

    def get_captured_output(self) -> Union[List[Tuple[str, str]], None]:
        """Returns the logging output which has been captured so far."""
        return self.captured_output

    def get_error_count(self) -> int:
        """Returns the number of errors which have been recorded in the
        currently captured output.

        """
        return self.error_count

    def get_fatal_count(self) -> int:
        """Returns the number of fatal errors which have been recorded in the
        currently captured output.

        """
        return self.fatal_count

    def print(self, *args, **kwargs) -> None:
        """Like print, but allows for redirection."""
        line = ' '.join(str(arg) for arg in args)
        self.log.info(line, **kwargs)

    def dump_mem(self, buf, prefix='', addr=0) -> None:
        """Like dump_mem, but allows for redirection."""
        dump_mem(buf, prefix, addr, log=self.print)

    def debug(self, msg: str, *args, **kwargs) -> None:
        """Captures and logs a debug level message."""
        self.log.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        """Captures and logs an info level message."""
        if self.captured_output is not None:
            self.captured_output.append(('info', msg % args))
        self.log.info(msg, *args, **kwargs)

    def good(self, msg: str, *args, **kwargs) -> None:
        """Logs a GOOD level string, which the color formatter prints as
        a green color..

        """
        self.log.good(msg, *args, **kwargs)  # type: ignore

    def error(self, msg: str, *args, **kwargs) -> None:
        """Captures and logs an error level message."""
        if self.captured_output is not None:
            self.captured_output.append(('error', msg % args))
        self.error_count += 1
        self.log.error(msg, *args, **kwargs)

    def fatal(self, msg: str, *args, **kwargs) -> None:
        """Captures and logs an fatal level message."""
        if self.captured_output is not None:
            self.captured_output.append(('fatal', msg % args))
        self.fatal_count += 1
        self.log.fatal(msg, *args, **kwargs)

    def write(self, string: str) -> None:
        """Characters to output. Lines will be delimited by newline
        characters.

        This routine breaks the output into lines and logs each line
        individually.

        """
        if len(self.buffered_output) > 0:
            string = self.buffered_output + string
            self.buffered_output = ""
        while True:
            nl_index = string.find('\n')
            if nl_index < 0:
                self.buffered_output = string
                return
            self.info(string[0:nl_index])
            string = string[nl_index + 1:]

    def reset(self) -> None:
        """Resets output."""
        sys.stdout.flush()
        self.captured_output = []
        self.error_count = 0
        self.fatal_count = 0
