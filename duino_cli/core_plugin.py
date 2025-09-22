"""
Core plugin functionality.
"""
import argparse
from cmd import Cmd
from fnmatch import fnmatch
import logging
import shlex
import threading
import time
from typing import Any, Dict, NamedTuple, Optional, Tuple, Union

from duino_bus.packet import ErrorCode, Packet
from duino_bus.packer import Packer
from duino_bus.unpacker import Unpacker
from duino_cli.command_line import CommandLine
from duino_cli.command_line_output import CommandLineOutput
from duino_cli.cli_plugin_base import str_to_bool, trim, CliPluginBase
from duino_cli.command_argument_parser import Arg, Parser
from duino_cli.plugins import PluginManager

PING = 0x01  # Check to see if the device is alive.
DEBUG = 0x02  # Enables/disables debug.
# LOG = 0x03    # Log message (declared in bus.py)
STACK_INFO = 0x04  # Information about stack usage.
HEAP_INFO = 0x05  # Information about heap usage.
# EVENT = 0x??  # Event packet (declared in bus.py)


class HeapInfo(NamedTuple):
    """Heap Information from the HW-Tester."""
    size: int  # Total size of the heap (in bytes)
    allocated: int  # Amount of allocated space (in bytes)
    free: int  # Amount of free space (in bytes)
    largest_free: int  # Largest Free block (in bytes)
    growth_potential: int  # Amount heap can grow by (in bytesP)


class StackInfo(NamedTuple):
    """Stack Information from the HW-Tester."""
    size: int  # Size of the stack (in bytes)
    used: int  # Amount of used stack space (in bytes)
    unused: int  # Amount of unused stack space (in bytes)


class CorePlugin(CliPluginBase):
    """Defines core plugin functions used with duino_cli."""

    def __init__(self, plugin_manager: PluginManager, output: CommandLineOutput,
                 params: Dict[str, Any]) -> None:
        super().__init__(plugin_manager, output, params)
        self.cli: Optional[CommandLine] = None
        if 'cli' in params:
            self.cli = params['cli']
        self.bus_debug: int = 0

    #argparse_args = Parser(
    #    Arg(
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

    argparse_debug = Parser(Arg('on_off', choices=['on', 'off'], nargs='?'), )

    def do_debug(self, args: argparse.Namespace) -> Union[bool, None]:
        """debug [on|off]

           Turns bus debugging on or off.
        """
        if args.on_off is not None:
            on_off = args.on_off
            err = self.set_debug(str_to_bool(on_off))
            if err != ErrorCode.NONE:
                self.error(f'Error: {ErrorCode.as_str(err)}')
                return
        debug_str = 'on' if self.bus_debug else 'off'
        self.print(f'Bus debug is {debug_str}')

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
        if self.cli:
            self.cli.quitting = True
        return True

    argparse_help = Parser(
        Arg('-v',
            '--verbose',
            dest='verbose',
            action='store_true',
            help='Display more help for each command',
            default=False),
        Arg('command', metavar='COMMAND', nargs='*', type=str, help='Command to get help on'),
    )

    def do_help(self, args: argparse.Namespace) -> Union[bool, None]:
        """help [-v] [CMD]...

           List available commands with "help" or detailed help with "help cmd".
        """
        print('do_help')
        # arg isn't really a string but since Cmd provides a do_help
        # function we have to match the prototype.
        if len(args.command) <= 0 and not args.verbose:
            self.plugin_manager.help_command_list()
            return None
        if len(args.command) == 0:
            help_cmd = ''
        else:
            help_cmd = args.command[0]
        help_cmd = help_cmd.replace("-", "_")

        if not help_cmd:
            help_cmd = '*'

        cmds = self.plugin_manager.get_commands()
        cmds.sort()

        cmd_found = False
        for cmd in cmds:
            if fnmatch(cmd, help_cmd):
                if cmd_found:
                    self.print('--------------------------------------------------------------')
                cmd_found = True
                parser = self.plugin_manager.create_argparser(cmd)
                if parser:
                    # Need to figure out how to strip out the `usage:`
                    # Need to figure out how to get indentation to work
                    parser.print_help()
                    continue

                try:
                    doc = self.plugin_manager.get_command_help(cmd)
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

    def do_log_test(self, _) -> None:
        """log-test

           Logs some messages in the background to verify that prompt
           behaves properly.
        """
        self.print('Starting log-test')
        # Start a background thread that prints
        thread = threading.Thread(target=self.log_test_thread, daemon=True)
        thread.start()

    def log_test_thread(self):
        """Thread for testing background logging."""
        log = logging.getLogger()
        for i in range(5):
            log.debug('Debug    Message %d', i)
            log.warning('Warning  Message %d', i)
            log.error('Error    Message %d', i)
            log.info(
                'Info     Message %d  123456789 123456789 123456789 123456789 123456789 123456789',
                i)
            log.critical('Critical Message %d', i)
            time.sleep(1)

    def do_ping(self, _) -> None:
        """ping

           Sends a PING packet to the arduino and reports a response.
        """
        err = self.ping()
        if err == ErrorCode.NONE:
            self.print("Device is alive")
        else:
            self.error(f'Error: {ErrorCode.as_str(err)}')

    def do_heap_info(self, _) -> None:
        """heap-info

            Reports heap usage information.
        """
        err, info = self.get_heap_info()
        if err != ErrorCode.NONE or info is None:
            self.error(f'Error: {ErrorCode.as_str(err)}')
            return
        allocated_pct = info.allocated / info.size * 100
        free_pct = info.free / info.size * 100
        largest_free_pct = info.largest_free / info.size * 100
        self.print(f'        Heap Size: {info.size:6}')
        self.print(f'   Heap Allocated: {info.allocated:6} {int(allocated_pct):2}%')
        self.print(f'        Heap Free: {info.free:6} {int(free_pct):2}%')
        self.print(f'Heap Largest Free: {info.largest_free:6} {int(largest_free_pct):2}%')
        self.print(f' Growth Potential: {info.growth_potential:6}')

    def do_stack_info(self, _) -> None:
        """stack-info

            Reports stack usage information.
        """
        err, info = self.get_stack_info()
        if err != ErrorCode.NONE or info is None:
            self.error(f'Error: {ErrorCode.as_str(err)}')
            return
        used_pct = info.used / info.size * 100
        unused_pct = info.unused / info.size * 100
        self.print(f' Stack Size: {info.size:6}')
        self.print(f' Stack Used: {info.used:6} {int(used_pct):2}%')
        self.print(f'Stack Avail: {info.unused:6} {int(unused_pct):2}%')

    def do_quit(self, _) -> bool:
        """quit

           Exits from the program.
        """
        self.cli.quitting = True
        return True

    def get_heap_info(self) -> Tuple[int, Optional[HeapInfo]]:
        """Retrieves heap usage information from the HW-Tester."""
        if self.bus is None:
            return ErrorCode.NO_DEVICE, None
        info_pkt = Packet(HEAP_INFO)
        err, rsp = self.bus.send_command_get_response(info_pkt)
        if err != ErrorCode.NONE:
            return err, None
        unpacker = Unpacker(rsp.get_data())
        size = unpacker.unpack_u32()
        alloc = unpacker.unpack_u32()
        free = unpacker.unpack_u32()
        largest_free = unpacker.unpack_u32()
        growth_potential = unpacker.unpack_u32()
        return ErrorCode.NONE, HeapInfo(size, alloc, free, largest_free, growth_potential)

    def get_stack_info(self) -> Tuple[int, Optional[StackInfo]]:
        """Retrieves stack usage information from the HW-Tester."""
        if self.bus is None:
            return ErrorCode.NO_DEVICE, None
        info_pkt = Packet(STACK_INFO)
        err, rsp = self.bus.send_command_get_response(info_pkt)
        if err != ErrorCode.NONE:
            return err, None
        unpacker = Unpacker(rsp.get_data())
        size = unpacker.unpack_u32()
        used = unpacker.unpack_u32()
        unused = unpacker.unpack_u32()
        return ErrorCode.NONE, StackInfo(size, used, unused)

    def ping(self) -> int:
        """Send a PING packet to the connected device and reports if a response was received."""
        if self.bus is None:
            return ErrorCode.NO_DEVICE
        ping = Packet(PING)
        err, _rsp = self.bus.send_command_get_response(ping)
        return err

    def set_debug(self, on_off: bool) -> int:
        """Sends a DEBUG command to the connected device."""
        if self.bus is None:
            return ErrorCode.NO_DEVICE
        debug_pkt = Packet(DEBUG)
        packer = Packer(debug_pkt)
        packer.pack_u32(on_off)
        err, rsp = self.bus.send_command_get_response(debug_pkt)
        if err != ErrorCode.NONE:
            return err
        unpacker = Unpacker(rsp.get_data())
        self.bus_debug = unpacker.unpack_u32()
        return ErrorCode.NONE
