"""
Helper classes/functions for working with argparse.
"""

import argparse
import sys
from typing import Any, Dict, NoReturn, Tuple

from duino_cli.command_line_error import CommandLineError

# argparse added exit_on_error support in 3.9
if sys.version_info >= (3, 9, 0):
    EXIT_ON_ERROR_FALSE = {'exit_on_error': False}
else:
    EXIT_ON_ERROR_FALSE = {}


class CommandArgumentParser(argparse.ArgumentParser):
    """Helper class to prevent argument parsing from calling sys.exit()"""

    def __init__(self, cli, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.cli = cli

    def exit(self, status=0, message=None) -> NoReturn:
        """Called when a parsing error occurs."""
        #if message:
        #    self.cli.print(message)
        raise CommandLineError(message)


def add_arg(*args, **kwargs) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
    """Returns a list containing args and kwargs."""
    return (args, kwargs)
