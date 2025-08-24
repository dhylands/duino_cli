"""
Base class used for plugins.
"""

import sys
from typing import Any, Callable, Dict, List, Tuple, Union

import argparse

from duino_cli.command_line_output import CommandLineOutput

# Map of user strings to booleans
BOOL_MAP = {
    'true': True,
    'fasle': False,
    'on': True,
    'off': False,
}


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


def str_to_bool(s: str) -> bool:
    """Determines if a string looks like a boolean value."""
    if s in BOOL_MAP:
        return BOOL_MAP[s]
    raise ValueError(f"Invalid boolean: '{s}'")


class CliPluginBase:
    """Base class used for all plugins."""

    def __init__(self, output: CommandLineOutput, _params: Dict[str, Any]):
        self.output = output

    def get_commands(self) -> List[str]:
        """Gets a list of all of the commands."""
        cmds = [x[3:] for x in dir(self.__class__) if x.startswith('do_')]
        return cmds

    def get_command(self, command: str) -> Union[Callable[[argparse.Namespace], bool], None]:
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
        # print(f'get_command_args: {argparse_args}')
        return argparse_args

    def execute_cmd(self, fn: Callable[[argparse.Namespace], Union[bool, None]],
                    args: argparse.Namespace) -> Union[bool, None]:
        """Executes a command from this plugin.

            Plugins can override this function to do plugin wide checking.
        """
        return fn(args)

    def print(self, *args, **kwargs) -> None:
        """Like print, but allows for redirection."""
        self.output.print(*args, **kwargs)

    def error(self, *args, **kwargs) -> None:
        """Like print, but allows for redirection."""
        self.output.error(*args, **kwargs)

    def debug(self, *args, **kwargs) -> None:
        """Prints only when DEBUG is set to true"""
        self.output.debug(*args, **kwargs)

    def dump_mem(self, buf, prefix='', addr=0) -> None:
        """Like dump_mem, but allows for redirection."""
        self.output.dump_mem(buf, prefix, addr)
