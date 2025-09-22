#!/usr/bin/env python3
"""
This module implements a command line interface
"""

import argparse
import logging
import shlex
from typing import Any, Dict, Union

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.history import FileHistory

from duino_cli.colors import Color
from duino_cli.command_line_error import CommandLineError
from duino_cli.command_line_output import CommandLineOutput
from duino_cli.completer import CliCompleter
from duino_cli.plugins import PluginManager

MAX_HISTORY_LINES: int = 40
LOGGER = logging.getLogger(__name__)


class CommandLine:  # pylint: disable=too-many-instance-attributes,too-many-public-methods
    """Class for managing the command line."""

    def __init__(self, params: Dict[str, Any], log=None, filename=None) -> None:
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
        self.prompt = ''
        self.update_prompt()
        self.plugin_manager = PluginManager(params, self.output)
        self.plugin_manager.load_plugins()

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

    def postcmd(self, stop, _line):
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
        if line:
            self.execute_cmd(line)
            return True
        self.cmd_stack.append(self)
        stop = self.auto_cmdloop_internal(line)
        self.cmd_stack.pop()
        return stop

    def auto_cmdloop_internal(self, line) -> Union[bool, None]:
        """The main code for auto_cmdloop."""
        # parser = self.create_argparser('upload')
        # print('-----')
        # print(parser)
        # parser.print_help()
        # print('-----')
        while not self.quitting:
            cmds = self.plugin_manager.get_commands()
            cmds.sort()
            completer = CliCompleter(self.plugin_manager.get_pretty_commands(),
                                     self.plugin_manager.create_argparser)
            try:
                line = self.session.prompt(self.prompt, completer=completer)
            except EOFError:
                self.debug('Got EOF')
                self.quitting = True
                return True
            except KeyboardInterrupt:
                print('')
                self.debug('Got Keyboard Interrupt')
                self.quitting = True
                return True
            if self.quitting:
                return True
            self.debug(f'Got line {line}')
            self.execute_cmd(line)
        return True

    def handle_exception(self, err, log=None) -> bool:
        """Common code for handling an exception."""
        print('handle exception')
        if not log:
            log = self.output.error
        base = self.cmd_stack[0]
        if base.filename is not None:
            log("File: %s Line: %d Error: %s", base.filename, base.line_num, err)
            self.quitting = True
            return True
        log("Error: %s", err)
        return False

    # pylint: disable=too-many-return-statements
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
            # print(f'About to call parseline({line})')
            args = self.parseline(line)
            # print(f'parseline returned {args}')
            plugin, fn = self.plugin_manager.get_command(args.cmd)
            if plugin is None or fn is None:
                raise ValueError(f"Unrecognized command: '{args.cmd}'")
            res = plugin.execute_cmd(fn, args)
            if res is None:
                return False
            return res
        except argparse.ArgumentError as err:
            print('argparse.ArgumentParser')
            return self.handle_exception(err)
        except CommandLineError as err:
            print('CommandLineError')
            return self.handle_exception(err)
        except ValueError as err:
            return self.handle_exception(err)

    def parseline(  # type: ignore
            self, line) -> argparse.Namespace:
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
                self.redirect_handler = logging.FileHandler(self.redirect_filename,
                                                            mode=redirect_mode,
                                                            encoding='utf-8')
            except FileNotFoundError as err:
                raise CommandLineError(str(err)) from err
            logging.getLogger().addHandler(self.redirect_handler)

            # Remove the '> filename' or '>> filename' from the argument list.
            del argv[redirect_index + 1]
            del argv[redirect_index]

        # print(f'Creating argparser for "{cmd}"')
        parser = self.plugin_manager.create_argparser(cmd)
        # print(f'parser.parse_args')
        args = parser.parse_args(argv[1:])
        # print(f'argparser args = {args}')
        args.cmd = cmd
        args.argv = argv
        return args

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
