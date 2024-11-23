"""
Base class used for plugins.
"""

import sys
from typing import Any, Callable, Dict, List, Tuple, Union

# TODO(dhylands): SHould probably get dump_mem from duino_log
from duino_bus.dump_mem import dump_mem
from duino_cli.command_line_base import CommandLineBase


def add_arg(*args, **kwargs) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
    """Returns a list containing args and kwargs."""
    return (args, kwargs)


def trim(docstring: str) -> str:
    """Trims the leading spaces from docstring comments.

    From http://www.python.org/dev/peps/pep-0257/

    """
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxsize
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxsize:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)


class CliPluginBase:
    """Base class used for all plugins."""

    def __init__(self, cli: CommandLineBase):
        self.cli = cli

    def get_commands(self) -> List[str]:
        """Gets a list of all of the commands."""
        cmds = [x[3:] for x in dir(self.__class__) if x.startswith('do_')]
        return cmds

    def get_command(self, command: str) -> Union[Callable, None]:
        """Retrieves the function object associated with a command."""
        try:
            fn = getattr(self, "do_" + command)
            return fn
        except AttributeError:
            return None

    def get_command_args(self, command: str) -> Union[None, Tuple]:
        """Retrievers the argparse arguments for a command."""
        try:
            argparse_args = getattr(self, "argparse_" + command)
        except AttributeError:
            return None
        return argparse_args

    def print(self, *args, end='\n', file=None) -> None:
        """Like print, but allows for redirection."""
        if file is None:
            file = self.cli.stdout
        line = ' '.join(str(arg) for arg in args) + end
        file.write(line)
        file.flush()

    def dump_mem(self, buf, prefix='', addr=0) -> None:
        """Like print, but allows for redirection."""
        dump_mem(buf, prefix, addr, log=self.print)

    def pr_debug(self, *args, end='\n', file=None) -> None:
        """Prints only when DEBUG is set to true"""
        if self.cli.params['debug']:
            self.print(*args, end, file)
