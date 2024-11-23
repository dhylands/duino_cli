"""
Core plugin functionality.
"""
import argparse
from cmd import Cmd
from fnmatch import fnmatch
from typing import cast, List, Union

from duino_bus.packet import ErrorCode, Packet
from duino_cli.command_line_base import CommandLineBase
from duino_cli.cli_plugin_base import add_arg, trim, CliPluginBase

PING = 0x01  # Check to see if the device is alive.


class CorePlugin(CliPluginBase):
    """Defines core plugin functions used with duino_cli."""

    def help_command_list(self) -> None:
        """Prints the list of commands."""
        commands = sorted(self.cli.get_commands())
        self.cli.print_topics(
                'Type "help <command>" to get more information on a command:',
                commands,
                0,
                80
        )

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

    def do_help(self, arg: str) -> Union[bool, None]:
        """help [-v] [CMD]...

           List available commands with "help" or detailed help with "help cmd".
        """
        # arg isn't really a string but since Cmd provides a do_help
        # function we have to match the prototype.
        args = cast(argparse.Namespace, arg)
        if len(args.command) <= 0 and not args.verbose:
            self.help_command_list()
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
                        self.cli.stdout.write(f"{trim(str(doc))}\n")
                        continue
                except AttributeError:
                    pass
                self.cli.stdout.write(f'{str(Cmd.nohelp % (cmd,))}\n')
        if not cmd_found:
            self.print(f'No command found matching "{help_cmd}"')
        return None

    def do_args(self, args: List[str]) -> Union[bool, None]:
        """args [arguments...]

           Debug function for verifying argument parsing. This function just
           prints out each argument that it receives.
        """
        for idx, arg in enumerate(args):
            self.print(f"arg[{idx}] = '{arg}'")

    def do_echo(self, args: List[str]) -> Union[bool, None]:
        """echo [STRING]...

           Similar to linux echo.
        """
        line = ' '.join(args[1:])
        self.print(line)

    def do_exit(self, _) -> bool:
        """exit

           Exits from the program.
        """
        CommandLineBase.quitting = True
        return True

    def do_ping(self, _) -> None:
        """ping

           Sends a PING packet to the arduino and reports a response.
        """
        ping = Packet(PING)
        err, _rsp = self.cli.bus.send_command_get_response(ping)
        if err != ErrorCode.NONE:
            return
        self.print('Device is alive')

    def do_quit(self, _) -> bool:
        """quit

           Exits from the program.
        """
        CommandLineBase.quitting = True
        return True
