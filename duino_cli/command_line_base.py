#!/usr/bin/env python3
"""
This module implements a command line interface
"""

import argparse
from cmd import Cmd
from fnmatch import fnmatch
import importlib.metadata
import logging
import os
import shlex
import stat
import sys
import traceback
from typing import cast, Any, Callable, Dict, IO, List, NoReturn, Tuple, Union

from duino_bus.dump_mem import dump_mem
from duino_cli.colors import Color

MAX_HISTORY_LINES: int = 40
LOGGER = logging.getLogger(__name__)

# argparse added exit_on_error support in 3.9
if sys.version_info >= (3, 9, 0):
    EXIT_ON_ERROR_FALSE = {'exit_on_error': False}
else:
    EXIT_ON_ERROR_FALSE = {}

try:
    import readline
except ImportError:

    class ReadLine:
        """Fake readine implementation to keep the linter happy"""

        def get_completer_delims(self) -> str:
            """Gets characters which delimit words"""
            return ''

        def set_completer_delims(self, _delims: str) -> None:
            """Sets characters which delimit words"""

        def read_history_file(self, _filename: str) -> None:
            """Reads history from a file."""

    readline = ReadLine()

GOOD = logging.INFO + 1

DEBUG = False


class CommandLineError(Exception):
    """Error raised by this module when a CLI error occurs."""


class CommandArgumentParser(argparse.ArgumentParser):
    """Helper class to prevent argument parsing from calling sys.exit()"""

    def __init__(self, cli, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.cli = cli

    def exit(self, status=0, message=None) -> NoReturn:
        """Called when a parsing error occurs."""
        #if message:
        #    self.cli.print(message)
        raise ValueError(message)


def add_arg(*args, **kwargs) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
    """Returns a list containing args and kwargs."""
    return (args, kwargs)


class CommandLineOutput:
    """A class which allows easy integration of Cmd output into logging
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

    def flush(self) -> None:
        """Used by Cmd just after printing the prompt."""
        prompt = self.buffered_output
        self.buffered_output = ""
        self.write_prompt(prompt)

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
        self.log.log(GOOD, msg, *args, **kwargs)

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

    def write_prompt(self, prompt: str) -> None:
        """A derived class can override this method to split out the
        prompt from regular output.

        """
        sys.stdout.write(prompt)
        sys.stdout.flush()
        self.captured_output = []
        self.error_count = 0
        self.fatal_count = 0


class CommandLineBase(Cmd):  # pylint: disable=too-many-instance-attributes,too-many-public-methods
    """Contains common customizations to the Cmd class."""

    cmd_stack = []
    quitting = False
    output = None

    def __init__(self, params: Dict[str, Any], *args, log=None, filename=None, **kwargs) -> None:
        self.params = params
        self.bus = params['bus']
        self.debug = params['debug']
        if 'stdin' in kwargs:
            Cmd.use_rawinput = False
        if not CommandLineBase.output:
            CommandLineBase.output = CommandLineOutput(log=log)
        self.log = CommandLineBase.output
        Cmd.__init__(self, stdout=cast(IO[str], self.log), *args, **kwargs)
        if '-' not in Cmd.identchars:
            Cmd.identchars += '-'
        self.filename = filename
        self.line_num = 0
        self.command = None
        if len(CommandLineBase.cmd_stack) == 0:
            self.cmd_prompt = "CLI"
        else:
            self.cmd_prompt = CommandLineBase.cmd_stack[-1].command
        self.cmdloop_executed = False
        if 'readline' in sys.modules:
            delims = readline.get_completer_delims()
            readline.set_completer_delims(delims.replace("-", ""))
        self.redirect_filename = ''
        self.history = []
        self.history_filename = params['history_filename']
        self.read_history()
        self.plugins = {}
        self.load_plugins()

    def load_plugins(self) -> None:
        """Loads plugins which have been installed."""
        plugin_entry_points = importlib.metadata.entry_points()['duino_cli.plugin']
        for plugin_entry_point in plugin_entry_points:
            plugin_name = plugin_entry_point.name
            LOGGER.info('Loading Plugin %s ...', plugin_name)
            if self.debug:
                LOGGER.info('  %s', plugin_entry_point)
            try:
                plugin_class = plugin_entry_point.load()
                plugin = plugin_class(self)
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

    def default(self, line):
        """Called when a command isn't recognized."""
        raise ValueError(f"Unrecognized command: '{line}'")

    def emptyline(self) -> bool:
        """We want empty lines to do nothing. By default they would repeat the
        previous command.

        """
        return False

    def update_prompt(self):
        """Sets the prompt based on the current command stack."""
        if Cmd.use_rawinput:
            prompts = [cmd.cmd_prompt for cmd in CommandLineBase.cmd_stack]
            self.prompt = Color.PROMPT_COLOR + " ".join(prompts) + "> " + Color.END_COLOR
        else:
            self.prompt = ""

    def preloop(self):
        """Update the prompt before cmdloop, which is where the prompt
        is used.

        """
        Cmd.preloop(self)
        self.update_prompt()

    def postcmd(self, stop, line):
        """We also update the prompt here since the command stack may
        have been modified.

        """
        stop = Cmd.postcmd(self, stop, line)
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
        CommandLineBase.cmd_stack.append(self)
        stop = self.auto_cmdloop_internal(line)
        CommandLineBase.cmd_stack.pop()
        return stop

    def auto_cmdloop_internal(self, line) -> Union[bool, None]:
        """The main code for auto_cmdloop."""
        try:
            if len(line) == 0:
                self.cmdloop()
            else:
                self.onecmd(line)
                if (self.cmdloop_executed and not CommandLineBase.quitting):
                    self.cmdloop()
        except KeyboardInterrupt:
            print('')
            CommandLineBase.quitting = True
            return True
        if CommandLineBase.quitting:
            return True
        return None

    def handle_exception(self, err, log=None) -> bool:
        """Common code for handling an exception."""
        if not log:
            log = self.log.error
        base = CommandLineBase.cmd_stack[0]
        if base.filename is not None:
            log("File: %s Line: %d Error: %s", base.filename, base.line_num, err)
            CommandLineBase.quitting = True
            return True
        log("Error: %s", err)
        return False

    def onecmd(self, line) -> bool:
        """Override onecmd.

        1 - So we don't have to have a do_EOF method.
        2 - So we can strip comments
        3 - So we can track line numbers

        """
        self.line_num += 1
        if line == "EOF":
            if Cmd.use_rawinput:
                # This means that we printed a prompt, and we'll want to
                # print a newline to pretty things up for the caller.
                print('')
            return True
        # Strip comments
        comment_idx = line.find("#")
        if comment_idx >= 0:
            line = line[0:comment_idx]
            line = line.strip()
        try:
            # We would normally use Cmd.onecmd here, but that doesn't work with
            # plugins, so we duplicate the functionality here instead
            cmd, arg, line = self.parseline(line)
            if not line:
                return self.emptyline()
            if cmd is None or cmd == '':
                return self.default(line)
            fn = self.get_command(cmd)
            if fn:
                return fn(arg)
            return self.default(line)
        except ValueError as err:
            return self.handle_exception(err)

    def cmdloop(self, intro=None):
        """We override this to support auto_cmdloop."""
        self.cmdloop_executed = True
        return Cmd.cmdloop(self, intro)

    def parseline(  # type: ignore
            self,
            line
    ) -> Tuple[Union[str,
                     None],
               Union[List[str],
                     None],
               str]:
        """Record the command that was executed. This also allows us to
        transform dashes back to underscores, and to convert the command line into a
        a list of arguments.

        """
        cmd, arg, line = Cmd.parseline(self, line)
        if cmd:
            cmd = cmd.replace("-", "_")
        if cmd and cmd != 'history':
            self.add_line_to_history(line)
            # We prefer to have a list of arguments, and deal with redirection
            # automatically, so do that now.
            try:
                args = self.line_to_args(cmd, cast(str, arg))
            except CommandLineError:
                return None, None, ''
        else:
            args = []
        return cmd, args, line  # type: ignore

    def completenames(self, text, *ignored) -> List[str]:
        """Override completenames so we can support names which have a dash
        in them.

        """
        real_names = Cmd.completenames(self, text.replace("-", "_"), *ignored)
        return [string.replace("_", "-") for string in real_names]

    def line_to_args(self, cmd: str, arg: str) -> Union[argparse.Namespace, List[str]]:
        """This will convert the line passed into the do_xxx functions into
        an array of arguments and handle the Output Redirection Operator.
        """
        # Note: using shlex.split causes quoted substrings to stay together.
        try:
            args = shlex.split(arg)
        except ValueError as err:
            raise CommandLineError(str(err)) from err
        self.redirect_filename = ''
        redirect_index = -1
        if '>' in args:
            redirect_index = args.index('>')
        elif '>>' in args:
            redirect_index = args.index('>>')
        if redirect_index >= 0:
            if redirect_index + 1 >= len(args):
                raise CommandLineError("> requires a filename")
            self.redirect_filename = args[redirect_index + 1]
            try:
                # Since this function runs remotely, it can't depend on other functions,
                # so we can't call stat_mode.
                mode = os.stat(self.redirect_filename).st_mode
            except OSError:
                mode = 0
            if not stat.S_ISDIR(mode):
                raise CommandLineError( \
                    f"Unable to redirect to '{self.redirect_filename}', directory doesn't exist")
            if args[redirect_index] == '>':
                redirect_mode = 'w'
                self.pr_debug(f'Redirecting (write) to {self.redirect_filename}')
            else:
                redirect_mode = 'a'
                self.pr_debug(f'Redirecting (append) to {self.redirect_filename}')
            self.stdout = open(self.redirect_filename, redirect_mode, encoding='utf-8')  # pylint: disable=consider-using-with
            del args[redirect_index + 1]
            del args[redirect_index]

        args.insert(0, cmd)
        parser = self.create_argparser(cmd)
        if parser:
            args = parser.parse_args(args[1:])
        return args

    def create_argparser(self, command) -> Union[None, CommandArgumentParser]:
        """Sets up and parses the command line if an argparse_xxx object exists."""
        argparse_args = self.get_command_args(command)
        if not argparse_args:
            return None
        doc_lines = self.get_command_help(command).expandtabs().splitlines()
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
            prog=command,
            usage='\n'.join(usage),
            description='\n'.join(description),
            exit_on_error=False)
        for args, kwargs in argparse_args:
            parser.add_argument(*args, **kwargs)
        return parser

    def get_commands(self) -> List[str]:
        """Gets a list of all of the commands."""
        commands = []
        for plugin in self.plugins.values():
            commands.extend(plugin.get_commands())
        return commands

    def get_command(self, command: str) -> Union[Callable, None]:
        """Retrieves the function object associated with a command."""
        for plugin in self.plugins.values():
            cmd = plugin.get_command(command)
            if cmd:
                return cmd
        return None

    def get_command_help(self, command: str) -> str:
        """Retrieves the documentation associated with a command."""
        fn = self.get_command(command)
        if fn:
            return fn.__doc__ or ''
        return ''

    def get_command_args(self, command: str) -> Union[None, Tuple]:
        """Retrievers the argparse arguments for a command."""
        for plugin in self.plugins.values():
            args = plugin.get_command_args(command)
            if args:
                return args
        return None

    def print(self, *args, end='\n', file=None) -> None:
        """Like print, but allows for redirection."""
        if file is None:
            file = self.stdout
        line = ' '.join(str(arg) for arg in args) + end
        file.write(line)
        file.flush()

    def error(self, *args, end='\n', file=None) -> None:
        """Like print, but allows for redirection."""
        if file is None:
            file = self.stdout
        line = ' '.join(str(arg) for arg in args) + end

        file.write(line)
        file.flush()

    def dump_mem(self, buf, prefix='', addr=0) -> None:
        """Like print, but allows for redirection."""
        dump_mem(buf, prefix, addr, log=self.print)

    def pr_debug(self, *args, end='\n', file=None) -> None:
        """Prints only when DEBUG is set to true"""
        if DEBUG:
            self.print(*args, end, file)

    def print_topics(
            self,
            header: str,
            cmds: Union[List[str],
                        None],
            cmdlen: int,
            maxcol: int
    ) -> None:
        """Transform underscores to dashes when we print the command names."""
        if isinstance(cmds, list):
            for i, cmd in enumerate(cmds):
                cmds[i] = cmd.replace("_", "-")
        Cmd.print_topics(self, header, cmds, cmdlen, maxcol)

    def add_line_to_history(self, line: str) -> None:
        """Adds a line into the history."""
        prev_line = ''
        if len(self.history) > 0:
            prev_line = self.history[-1]
        if line and prev_line != line:
            if len(self.history) >= MAX_HISTORY_LINES:
                del self.history[0]
            self.history.append(line)

    def read_history(self) -> None:
        """Reads history from the history file."""
        print(f'Reading history from {self.history_filename}')
        self.history = []
        if not self.history_filename:
            return
        try:
            with open(self.history_filename, 'r', encoding='utf-8') as file:
                for line in file:
                    self.history.append(line.strip())
            readline.read_history_file(self.history_filename)
        except FileNotFoundError:
            pass

    def save_history(self) -> None:
        """Saves history to the history file."""
        print(f'Saving history to {self.history_filename}')
        if not self.history_filename:
            return
        with open(self.history_filename, 'w', encoding='utf-8') as file:
            for line in self.history:
                file.write(line)
                file.write('\n')

    def do_history(self, args: List[str]) -> Union[bool, None]:
        """history [FILTER]

           Shows the history of commands executed.
        """
        if len(args) > 1:
            history_filter = args[1]
        else:
            history_filter = '*'
        for line in self.history:
            if fnmatch(line, history_filter):
                self.print(line)
