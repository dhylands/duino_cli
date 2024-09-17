"""
Sample command line interface for Arduino Projects
"""

import logging
from typing import List, Union

from column import column_print
from command_line_base import add_arg, CommandLineBase

LOGGER = logging.getLogger(__name__)


class CommandLine(CommandLineBase):
    """Command Line Interface (CLI) for the Arduino Boards."""

    def __init__(self, history_filename: str, *args, capture_output=False, **kwargs):
        CommandLineBase.__init__(self, history_filename, *args, **kwargs)
        self.log.set_capture_output(capture_output)

    def do_echo(self, args) -> Union[bool, None]:
        """Similar to linux echo."""
        line = ' '.join(args[1:])
        self.print(line)
