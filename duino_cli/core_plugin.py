"""
Core plugin functionality.
"""
import argparse
from cmd import Cmd
from fnmatch import fnmatch
import shlex
from typing import Any, Dict, List, Union

from duino_bus.packet import ErrorCode, Packet
from duino_cli.command_line import CommandLine
from duino_cli.command_line_output import CommandLineOutput
from duino_cli.cli_plugin_base import trim, CliPluginBase
from duino_cli.command_argument_parser import add_arg

PING = 0x01  # Check to see if the device is alive.


class CorePlugin(CliPluginBase):
    """Defines core plugin functions used with duino_cli."""

    def __init__(self, output: CommandLineOutput, params: Dict[str, Any]) -> None:
        super().__init__(output, params)
        self.bus = params['bus']
        self.cli: CommandLine = params['cli']

    #argparse_args = (
    #    add_arg(
    #        'argv',
    #        nargs='*',
    #    ),
    #)

    def do_args(self, args: argparse.Namespace) -> Union[bool, None]:
        """args [arguments...]

           Debug function for verifying argument parsing. This function just
           prints out each argument that it receives.
        """
        for idx, arg in enumerate(args.argv):
            self.print(f"arg[{idx}] = '{arg}'")

    def do_args_2(self, args: argparse.Namespace) -> Union[bool, None]:
        """args-2 [arguments...]

           Debug function for verifying argument parsing. This function just
           prints out each argument that it receives.
        """
        for idx, arg in enumerate(args.argv):
            self.print(f"arg[{idx}] = '{arg}'")

    def do_echo(self, args: argparse.Namespace) -> Union[bool, None]:
        """echo [STRING]...

           Similar to linux echo.
        """
        line = ' '.join(args.argv[1:])
        self.print(line)

    def do_exit(self, _) -> bool:
        """exit

           Exits from the program.
        """
        self.cli.quitting = True
        return True

    argparse_help = (
            add_arg(
                    '-v',
                    '--verbose',
                    dest='verbose',
                    action='store_true',
                    help='Display more help for each command',
                    default=False
            ),
            add_arg(
                    'command',
                    metavar='COMMAND',
                    nargs='*',
                    type=str,
                    help='Command to get help on'
            ),
    )

    def do_help(self, args: argparse.Namespace) -> Union[bool, None]:
        """help [-v] [CMD]...

           List available commands with "help" or detailed help with "help cmd".
        """
        # arg isn't really a string but since Cmd provides a do_help
        # function we have to match the prototype.
        if len(args.command) <= 0 and not args.verbose:
            self.cli.help_command_list()
            return None
        if len(args.command) == 0:
            help_cmd = ''
        else:
            help_cmd = args.command[0]
        help_cmd = help_cmd.replace("-", "_")

        if not help_cmd:
            help_cmd = '*'

        cmds = self.cli.get_commands()
        cmds.sort()

        cmd_found = False
        for cmd in cmds:
            if fnmatch(cmd, help_cmd):
                if cmd_found:
                    self.print('--------------------------------------------------------------')
                cmd_found = True
                parser = self.cli.create_argparser(cmd)
                if parser:
                    # Need to figure out how to strip out the `usage:`
                    # Need to figure out how to get indentation to work
                    parser.print_help()
                    continue

                try:
                    doc = self.cli.get_command_help(cmd)
                    if doc:
                        doc = doc.format(command=cmd)
                        self.print(f"{trim(str(doc))}")
                        continue
                except AttributeError:
                    pass
                self.print(f'{str(Cmd.nohelp % (cmd,))}')
        if not cmd_found:
            self.print(f'No command found matching "{help_cmd}"')
        return None

    def do_history(self, args: argparse.Namespace) -> Union[bool, None]:
        """history [FILTER]

           Shows the history of commands executed.
        """
        if len(args.argv) > 1:
            history_filter = args.argv[1]
        else:
            history_filter = '*'
        for line in self.cli.session.history.get_strings():
            argv = shlex.split(line)
            if fnmatch(argv[0], history_filter):
                self.print(line)

    def do_ping(self, _) -> None:
        """ping

           Sends a PING packet to the arduino and reports a response.
        """
        ping = Packet(PING)
        if self.bus is None:
            self.error('No device connected')
            return
        if not self.bus.is_open():
            self.error('No device open')
            return
        err, _rsp = self.bus.send_command_get_response(ping)
        if err != ErrorCode.NONE:
            return
        self.print('Device is alive')

    def do_quit(self, _) -> bool:
        """quit

           Exits from the program.
        """
        self.cli.quitting = True
        return True
