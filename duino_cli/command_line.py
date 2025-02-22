#!/usr/bin/env python3
"""
This module implements a command line interface
"""

import argparse
import importlib.metadata
import logging
import shlex
import traceback
from typing import cast, Any, Callable, Dict, IO, List, Tuple, Union

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.history import FileHistory

from duino_cli.cli_plugin_base import CliPluginBase
from duino_cli.colors import Color
from duino_cli.columnize import columnize
from duino_cli.command_argument_parser import add_arg, CommandArgumentParser
from duino_cli.command_line_error import CommandLineError
from duino_cli.command_line_output import CommandLineOutput
from duino_cli.completer import CliCompleter

MAX_HISTORY_LINES: int = 40
LOGGER = logging.getLogger(__name__)


class CommandLine:  # pylint: disable=too-many-instance-attributes,too-many-public-methods
    """Class for managing the command line."""

    def __init__(self, params: Dict[str, Any], *args, log=None, filename=None, **kwargs) -> None:
        self.params = params
        self.params['cli'] = self
        self.cmd_stack = []
        self.quitting = False
        self.output = CommandLineOutput(log=log)
        self.session = PromptSession(history=FileHistory(params['history_filename']))
        self.filename = filename
        self.line_num = 0
        self.command = None
        if len(self.cmd_stack) == 0:
            self.cmd_prompt = "CLI"
        else:
            self.cmd_prompt = self.cmd_stack[-1].command
        self.cmdloop_executed = False
        self.redirect_filename = ''
        self.redirect_handler = None
        self.plugins = {}
        self.prompt = ''
        self.update_prompt()
        self.load_plugins()

    def load_plugins(self) -> None:
        """Loads plugins which have been installed."""
        plugin_entry_points = importlib.metadata.entry_points()['duino_cli.plugin']
        for plugin_entry_point in plugin_entry_points:
            plugin_name = plugin_entry_point.name
            LOGGER.info('Loading Plugin %s ...', plugin_name)
            if self.params['debug']:
                LOGGER.info('  %s', plugin_entry_point)
            try:
                plugin_class = plugin_entry_point.load()
                plugin = plugin_class(self.output, self.params)
                self.plugins[plugin_name] = plugin
            except Exception:  # pylint: disable=broad-exception-caught
                LOGGER.error('Error encountered while loading plugin %s', plugin_name)
                traceback.print_exc()
        LOGGER.info('All plugins loaded')

    def add_completion_funcs(self, names, complete_func_name):
        """Helper function which adds a completion function for an array of
        command names.

        """
        for name in names:
            name = name.replace("-", "_")
            func_name = "complete_" + name
            cls = self.__class__
            try:
                getattr(cls, func_name)
            except AttributeError:
                setattr(cls, func_name, getattr(cls, complete_func_name))

    def update_prompt(self):
        """Sets the prompt based on the current command stack."""
        prompts = [cmd.cmd_prompt for cmd in self.cmd_stack]
        self.prompt = ANSI(Color.PROMPT_COLOR + 'CLI' + ' '.join(prompts) + '> ' + Color.END_COLOR)

    def preloop(self):
        """Update the prompt before cmdloop, which is where the prompt
        is used.

        """
        self.update_prompt()

    def postcmd(self, stop, line):
        """We also update the prompt here since the command stack may
        have been modified.

        """
        if self.redirect_handler is not None:
            self.redirect_handler.close()
            logging.getLogger().removeHandler(self.redirect_handler)
            self.redirect_handler = None
        self.update_prompt()
        return stop

    def auto_cmdloop(self, line):
        """If line is empty, then we assume that the user wants to enter
        commands, so we call cmdloop. If line is non-empty, then we assume
        that a command was entered on the command line, and we'll just
        execute it, and not hang around for user input. Things get
        interesting since we also used nested cmd loops. So if the user
        passes in "servo 15" we'll process the servo 15 using onecmd, and
        then enter a cmdloop to process the servo specific command. The
        logic in this function basically says that if we ever waited for
        user input (i.e. called cmdloop) then we should continue to call
        cmdloop until the user decides to quit. That way if you run
        "bioloid.py servo 15" and then press Control-D you'll get to the
        servo prompt rather than exiting the program.

        """
        # print('auto_cmdloop')
        self.cmd_stack.append(self)
        stop = self.auto_cmdloop_internal(line)
        self.cmd_stack.pop()
        return stop

    def auto_cmdloop_internal(self, line) -> Union[bool, None]:
        """The main code for auto_cmdloop."""
        parser = self.create_argparser('upload')
        # print('-----')
        # print(parser)
        # parser.print_help()
        # print('-----')
        while not self.quitting:
            cmds = self.get_commands()
            cmds.sort()
            completer = CliCompleter(self.get_pretty_commands(), self.create_argparser)
            try:
                line = self.session.prompt(self.prompt, completer=completer)
            except EOFError:
                self.debug('Got EOF')
                self.quitting = True
                return True
            except KeyboardInterrupt:
                print('')
                self.degbug('Got Keyboard Interrupt')
                self.quitting = True
                return True
            if self.quitting:
                return True
            self.debug(f'Got line {line}')
            self.execute_cmd(line)
        return True

    def handle_exception(self, err, log=None) -> bool:
        """Common code for handling an exception."""
        if not log:
            log = self.output.error
        base = self.cmd_stack[0]
        if base.filename is not None:
            log("File: %s Line: %d Error: %s", base.filename, base.line_num, err)
            self.quitting = True
            return True
        log("Error: %s", err)
        return False

    def execute_cmd(self, line) -> bool:
        """Executes a single command."""
        # print(f'execute_cmd line = {line}')
        self.line_num += 1
        if line == "EOF":
            # This means that we printed a prompt, and we'll want to
            # print a newline to pretty things up for the caller.
            print('')
            return True
        # Strip comments
        comment_idx = line.find("#")
        if comment_idx >= 0:
            line = line[0:comment_idx]
        line = line.strip()
        if not line:
            # Empty line
            return False
        try:
            args = self.parseline(line)
            # print(f'parseline returned {args}')
            plugin, fn = self.get_command(args.cmd)
            if plugin is None or fn is None:
                raise ValueError(f"Unrecognized command: '{args.cmd}'")
            return plugin.execute_cmd(fn, args)
        except CommandLineError as err:
            return self.handle_exception(err)
        except ValueError as err:
            return self.handle_exception(err)

    def cmdloop(self, intro=None):
        """We override this to support auto_cmdloop."""
        self.cmdloop_executed = True
        try:
            print('About to call session.prompt')
            line = self.session.prompt(self.prompt)
        except CommandLineError:
            print("Got CommandLineError")
            return 1
        except EOFError:
            # print('Got EOF')
            self.quitting = True
            return 0
        # print(f'Got line ?{line}')
        self.execute_cmd(line)

    def parseline(  # type: ignore
            self,
            line
    ) -> argparse.Namespace:
        """Record the command that was executed. This also allows us to
        transform dashes back to underscores, and to convert the command line into a
        a list of arguments.

        """
        return self.line_to_args(line)

    def line_to_args(self, line: str) -> argparse.Namespace:
        """This will convert the line passed into the do_xxx functions into
        an array of arguments and handle the Output Redirection Operator.
        """
        # Note: using shlex.split causes quoted substrings to stay together.
        try:
            argv = shlex.split(line)
        except ValueError as err:
            raise CommandLineError(str(err)) from err
        cmd = argv[0].replace('-', '_')
        self.redirect_filename = ''
        redirect_index = -1
        if '>' in argv:
            redirect_index = argv.index('>')
        elif '>>' in argv:
            redirect_index = argv.index('>>')
        if redirect_index >= 0:
            if redirect_index + 1 >= len(argv):
                raise CommandLineError("> requires a filename")
            self.redirect_filename = argv[redirect_index + 1]
            if argv[redirect_index] == '>':
                redirect_mode = 'w'
                self.debug(f'Redirecting (write) to {self.redirect_filename}')
            else:
                redirect_mode = 'a'
                self.debug(f'Redirecting (append) to {self.redirect_filename}')
            try:
                self.redirect_handler = logging.FileHandler(
                        self.redirect_filename,
                        mode=redirect_mode,
                        encoding='utf-8'
                )
            except FileNotFoundError as err:
                raise CommandLineError(str(err)) from err
            logging.getLogger().addHandler(self.redirect_handler)

            # Remove the '> filename' or '>> filename' from the argument list.
            del argv[redirect_index + 1]
            del argv[redirect_index]

        parser = self.create_argparser(cmd)
        args = parser.parse_args(argv[1:])
        args.cmd = cmd
        args.argv = argv
        return args

    def create_argparser(self, cmd: str) -> CommandArgumentParser:
        """Sets up and parses the command line if an argparse_xxx object exists."""
        argparse_args = self.get_command_args(cmd)
        doc_lines = self.get_command_help(cmd).expandtabs().splitlines()
        if '' in doc_lines:
            blank_idx = doc_lines.index('')
            usage = doc_lines[:blank_idx]
            description = doc_lines[blank_idx + 1:]
        else:
            usage = doc_lines
            description = []
        # pylint: disable=unexpected-keyword-arg
        parser = CommandArgumentParser( \
            self,
            prog=cmd,
            usage='\n'.join(usage),
            description='\n'.join(description),
            add_help=False,
            exit_on_error=False)
        # print(f'create_argparser: argparse_args: {argparse_args}')
        for args, kwargs in argparse_args:
            if 'completer' in kwargs:
                completer = kwargs['completer']
                del kwargs['completer']
                # print(f'Adding completer {completer}')
                parser.add_argument(*args, **kwargs).completer = completer  # type: ignore
            else:
                parser.add_argument(*args, **kwargs)
        # print(f'create_argparser: cmd: {cmd} parser: {repr(parser)}')
        return parser

    def get_commands(self) -> List[str]:
        """Gets a list of all of the commands."""
        commands = []
        for plugin in self.plugins.values():
            commands.extend(plugin.get_commands())
        return commands

    def get_pretty_commands(self) -> List[str]:
        """Gets a list of all the commands, as the user sees them."""
        return [command.replace('_', '-') for command in self.get_commands()]

    def get_command(self, command: str) -> Union[Tuple[CliPluginBase, Callable], Tuple[None, None]]:
        """Retrieves the function object associated with a command."""
        for plugin in self.plugins.values():
            cmd = plugin.get_command(command)
            if cmd:
                return plugin, cmd
        return None, None

    def get_command_help(self, command: str) -> str:
        """Retrieves the documentation associated with a command."""
        plugin, fn = self.get_command(command)
        if plugin is None or fn is None:
            return ''
        return fn.__doc__ or ''

    def get_command_args(self, cmd: str) -> Tuple:
        """Retrievers the argparse arguments for a command."""
        for plugin in self.plugins.values():
            args = plugin.get_command_args(cmd)
            if args:
                return args
        # No args, create one
        return (
            add_arg(
                'argv',
                metavar="ARGV",
                nargs='*',
                help='Arguments'
            ),
        )
        return None

    def print(self, *args, **kwargs) -> None:
        """Like print, but allows for redirection."""
        self.output.print(*args, **kwargs)

    def error(self, *args, **kwargs) -> None:
        """Like print, but allows for redirection."""
        self.output.error(*args, **kwargs)

    def dump_mem(self, buf, prefix='', addr=0) -> None:
        """Like dump_mem, but allows for redirection."""
        self.output.dump_mem(buf, prefix, addr)

    def debug(self, *args, **kwargs) -> None:
        """Prints only when DEBUG is set to true"""
        self.output.debug(*args, **kwargs)

    def help_command_list(self) -> None:
        """Prints the list of commands."""
        commands = sorted(self.get_commands())
        self.print_topics(
                'Type "help <command>" to get more information on a command:',
                commands,
                0,
                80
        )

    def print_topics(
            self,
            header: str,
            cmds: List[str],
            cmdlen: int,
            maxcol: int
    ) -> None:
        """Transform underscores to dashes when we print the command names."""
        if isinstance(cmds, list):
            for i, cmd in enumerate(cmds):
                cmds[i] = cmd.replace("_", "-")
        self.print(header)
        self.print('-' * maxcol)
        columnize(cmds, maxcol - 1, self.print)
