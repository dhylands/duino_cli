"""
Helper classes/functions for working with argparse.
"""

import argparse
import sys
from typing import NoReturn

from duino_cli.command_line_error import CommandLineError

# argparse added exit_on_error support in 3.9
if sys.version_info >= (3, 9, 0):
    EXIT_ON_ERROR_FALSE = {'exit_on_error': False}
else:
    EXIT_ON_ERROR_FALSE = {}


class Arg:
    """Encapsulates an argument added to a parser (using add_argument)."""

    def __init__(self, *args, **kwargs):
        self.args = []
        self.sub_parsers = []
        self.sub_parser = []
        self.arguments = []
        for a in args:
            if isinstance(a, SubParser):
                self.sub_parser.append(a)
            elif isinstance(a, SubParsers):
                self.sub_parsers.append(a)
            elif isinstance(a, Arg):
                self.arguments.append(a)
            else:
                self.args.append(a)
        self.kwargs = kwargs

    def dump(self, indent: int = 0) -> None:
        """Dumps the contents of this object."""
        indent_str = ''
        for _ in range(indent):
            indent_str += '  '
        print(f'{indent_str}{self.__class__.__name__}(')
        for arg in self.args:
            print(f'{indent_str}  {repr(arg)},')
        for a in self.arguments:
            a.dump(indent + 1)
        for a in self.sub_parsers:
            a.dump(indent + 1)
        for a in self.sub_parser:
            a.dump(indent + 1)
        for key, value in self.kwargs.items():
            print(f'{indent_str}  {key}={repr(value)},')
        if isinstance(self, Parser):
            print(f'{indent_str})')
        else:
            print(f'{indent_str}),')

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Adds argumenst to a parser or sub-parser."""
        for a in self.arguments:
            kwargs = a.kwargs.copy()
            if 'completer' in kwargs:
                completer = kwargs['completer']
                del kwargs['completer']
                parser.add_argument(*a.args, **kwargs).completer = completer  # type: ignore
            else:
                parser.add_argument(*a.args, **kwargs)


class SubParser(Arg):
    """Encapsulates a SubParser."""

    def add_subparser(self, cli, subparsers: argparse._SubParsersAction) -> None:
        """Adds a"""
        subparser = subparsers.add_parser(*self.args, cli=cli, **self.kwargs, add_help=False)
        self.add_arguments(subparser)


class SubParsers(Arg):
    """Encapsulates SubParsers."""

    def add_subparsers(self, cli, parser: argparse.ArgumentParser) -> None:
        """Adds the SubParsers stored in this object into the parser passed in."""
        subparsers = parser.add_subparsers(*self.args, **self.kwargs, dest='sub_cmd')
        for sp in self.sub_parser:
            sp.add_subparser(cli, subparsers)


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


class Parser(Arg):
    """Encapsulates a Parser."""

    # def create_parser(self) -> argparse.ArgumentParser:
    #     """Creates an argument parser from the data structures saved by
    #        Parser, SubParsers, SubParser, and Arg.
    #     """
    #     parser = argparse.ArgumentParser(*self.args, **self.kwargs)
    #     self.populate_parser(parser)
    #     return parser

    def populate_parser(self, cli, parser: CommandArgumentParser) -> CommandArgumentParser:
        """Populates an already constructed parser using the data structure from this object."""
        # Add an argument for the command
        self.add_arguments(parser)
        if len(self.sub_parsers) > 0:
            sps = self.sub_parsers[0]
            sps.add_subparsers(cli, parser)
        return parser
