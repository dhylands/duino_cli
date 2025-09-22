"""
Class used for managing plugins.
"""

import importlib.metadata
import logging
import traceback

from typing import Any, Callable, Dict, List, Optional, Tuple, Union, TYPE_CHECKING

import serial.tools.list_ports
from serial import SerialException

from duino_bus.bus import IBus
from duino_bus.serial_bus import SerialBus
from duino_cli.cli_plugin_base import CliPluginBase
from duino_cli.columnize import columnize
from duino_cli.command_argument_parser import Arg, CommandArgumentParser, Parser
from duino_cli.command_line_error import CommandLineError
from duino_cli.command_line_output import CommandLineOutput

if TYPE_CHECKING:
    from duino_cli.command_line import CommandLine

LOGGER = logging.getLogger(__name__)


class PluginManager:
    """Class for working with plugins."""

    def __init__(self, params: Dict[str, Any], output: CommandLineOutput) -> None:
        self.params = params
        self.output = output
        self.plugins: Dict[str, CliPluginBase] = {}

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
                plugin = plugin_class(self, self.output, self.params)
                self.plugins[plugin_name] = plugin
            except Exception:  # pylint: disable=broad-exception-caught
                LOGGER.error('Error encountered while loading plugin %s', plugin_name)
                traceback.print_exc()
        LOGGER.info('All plugins loaded')

    def set_plugin_bus(self, bus: IBus) -> None:
        """Sets the bus."""
        for plugin in self.plugins.values():
            plugin.set_bus(bus)

    def set_plugin_cli(self, cli: 'CommandLine') -> None:
        """Sets the CLI."""
        for plugin in self.plugins.values():
            plugin.set_cli(cli)

    def get_serial_bus(self) -> Optional[IBus]:
        """Gets the product names from the plugins and finds a serial port."""
        bus = None
        product_names = self.get_product_names()
        for port in serial.tools.list_ports.comports():
            for product_name in product_names:
                if port.product:
                    if product_name in port.product:
                        bus = SerialBus()
                        try:
                            self.output.print(f'Connecting to {port.product} - {port.device}')
                            bus.open(port.device)
                        except SerialException as err:
                            self.output.error(str(err))
        return bus

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

    def get_command_args(self, cmd: str) -> Parser:
        """Retrievers the argparse arguments for a command."""
        for plugin in self.plugins.values():
            args = plugin.get_command_args(cmd)
            if args:
                return args
        # No args, create one
        return Parser(Arg('argv', metavar="ARGV", nargs='*', help='Arguments'), )

    def get_product_names(self) -> List[str]:
        """Queries loaded plugins to find out what product names are supported."""
        product_names: List[str] = []
        for plugin in self.plugins.values():
            product_name = plugin.get_product_name()
            if product_name:
                product_names.append(product_name)
        return product_names

    def help_command_list(self) -> None:
        """Prints the list of commands."""
        commands = sorted(self.get_commands())
        self.print_topics('Type "help <command>" to get more information on a command:', commands,
                          0, 80)

    def print_topics(self, header: str, cmds: List[str], _cmdlen: int, maxcol: int) -> None:
        """Transform underscores to dashes when we print the command names."""
        if isinstance(cmds, list):
            for i, cmd in enumerate(cmds):
                cmds[i] = cmd.replace("_", "-")
        self.output.print(header)
        self.output.print('-' * maxcol)
        columnize(cmds, maxcol - 1, self.output.print)

    def create_argparser(self, cmd: str) -> CommandArgumentParser:
        """Sets up and parses the command line if an argparse_xxx object exists."""
        argparse_args = self.get_command_args(cmd)
        if not isinstance(argparse_args, Parser):
            raise CommandLineError(
                f'Expecting argparse_{cmd} to be of type Parser. Found {type(argparse_args)}')
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
        parser = argparse_args.populate_parser(cli=self, parser=parser)
        return parser
