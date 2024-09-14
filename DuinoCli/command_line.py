"""
Command line interface for the SkyWalker Simulator
"""

import argparse
import logging
from typing import List, Union

from column import column_print
from command_line_base import add_arg, CommandLineBase
from redirect import RedirectStdoutStderr

LOGGER = logging.getLogger(__name__)


class CommandLine(CommandLineBase):
    """Command Line Interface (CLI) for the SkyWalker Simulator"""

    def __init__(self, history_filename: str, *args, capture_output=False, **kwargs):
        CommandLineBase.__init__(self, history_filename, *args, **kwargs)
        self.log.set_capture_output(capture_output)

#    def line_entered(self, line: str) -> None:
#        """Fucntion called when the used pressed ENTER in the console window"""
#        if not line:
#            return
#        LOGGER.info('CLI> %s', line)
#
#        with RedirectStdoutStderr(self.log):
#            stop = self.auto_cmdloop(line)
#            if stop:
#                self.console.quit()

    def do_echo(self, args) -> Union[bool, None]:
        """Similar to linux echo."""
        line = ' '.join(args[1:])
        self.print(line)
