#!/usr/bin/env python3
"""
A CLI program for working with microcontrollers.
"""

import argparse
import logging
import os
import sys

try:
    import termios
except ModuleNotFoundError:
    termios = None  # pylint: disable=invalid-name

from typing import Any, Dict, Optional, Type

from pathlib import Path
import serial.tools.list_ports
from serial import SerialException

from duino_bus.bus import IBus
from duino_bus.serial_bus import SerialBus
from duino_bus.socket_bus import SocketBus

from duino_cli.colors import set_nocolor
from duino_cli.command_line import CommandLine
from duino_cli.log_setup import log_setup
from duino_cli.plugins import PluginManager

HOME = Path.home()
HISTORY_FILENAME = HOME / '.cli_history'


def extra_info(port):
    """Collects the serial nunber and manufacturer into a string, if
       the fields are available."""
    extra_items = []
    if port.manufacturer:
        extra_items.append(f"vendor '{port.manufacturer}'")
    if port.product:
        extra_items.append(f"product '{port.product}'")
    if port.serial_number:
        extra_items.append(f"serial '{port.serial_number}'")
    if port.interface:
        extra_items.append(f"intf '{port.interface}'")
    if extra_items:
        return ' with ' + ' '.join(extra_items)
    return ''


def list_ports():
    """Displays all of the detected serial ports."""
    detected = False
    for port in serial.tools.list_ports.comports():
        detected = True
        if port.vid:
            print(f'USB Serial Device {port.vid:04x}:{port.pid:04x}{extra_info(port)} '
                  f'found @{port.device}')
    if not detected:
        print('No serial devices detected')


class BusContext:
    """A context manager which takes care of closing the bus."""

    def __init__(self, args: argparse.Namespace, plugin_manager: PluginManager) -> None:
        self.args = args
        self.plugin_manager = plugin_manager
        self.bus = None

    def __enter__(self) -> Optional[IBus]:
        if self.args.net:
            self.bus = SocketBus()
            print(f'Connecting to localhost:{SocketBus.DEFAULT_PORT}')
            self.bus.connect_to_server('localhost', SocketBus.DEFAULT_PORT)
        elif self.args.port:
            self.bus = SerialBus()
            try:
                print(f'Connecting to {self.args.port} @ {self.args.baud}')
                self.bus.open(self.args.port, baudrate=self.args.baud)
            except SerialException as err:
                print(err)
        else:
            self.bus = self.plugin_manager.get_serial_bus()
        return self.bus

    def __exit__(self, _exc_type: Optional[Type[BaseException]],
                 _exc_value: Optional[BaseException], _traceback: Optional[Any]) -> bool:
        if self.bus is not None:
            self.bus.close()
        return False  # Propagate exceptions


def real_main() -> None:
    """Real main"""
    default_baud = 115200
    default_baud_str = os.getenv('CLI_BAUD')
    try:
        if default_baud_str is not None:
            default_baud = int(default_baud_str)
    except ValueError:
        pass
    default_port = os.getenv('CLI_PORT')
    default_color = sys.stdout.isatty()
    default_nocolor = not default_color
    # default_plugins_dir = os.getenv("CLI_PLUGINS_DIR") or 'plugins'

    parser = argparse.ArgumentParser(
        prog='duino_cli',
        usage='%(prog)s [options] [command]',
        description='Command Line Interface for Arduino boards.',
        epilog='You can specify the default serial port using the '
        'CLI_PORT environment variable.\n',
        #'You can specify the defaut plugin directory using the '
        #'CLI_PLUGINS_DIR environment variable.',
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-p',
                        '--port',
                        dest='port',
                        help=f'Set the serial port to use (default = {default_port})',
                        default=default_port)
    parser.add_argument('-b',
                        '--baud',
                        dest='baud',
                        action='store',
                        type=int,
                        help=f'Set the baudrate used (default = {default_baud})',
                        default=default_baud)
    parser.add_argument('-l',
                        '--list',
                        dest='list',
                        action='store_true',
                        help='Display serial ports',
                        default=False)
    parser.add_argument('-n',
                        '--net',
                        dest='net',
                        action='store_true',
                        help=f'Connect to a duino_cli_server (localhost:{SocketBus.DEFAULT_PORT})')
    parser.add_argument('-d',
                        '--debbug',
                        dest='debug',
                        action='store_true',
                        help='Turn on some debug')
    parser.add_argument("--nocolor",
                        dest="nocolor",
                        action="store_true",
                        help="Turn off colorized output",
                        default=default_nocolor)
    parser.add_argument("cmd", nargs=argparse.REMAINDER, help="Optional command to execute")

    try:
        args = parser.parse_args(sys.argv[1:])
    except SystemExit:
        return

    if args.list:
        list_ports()
        return

    if args.debug:
        level = logging.DEBUG
        timestamp = True
    else:
        level = logging.INFO
        timestamp = False

    if args.nocolor:
        set_nocolor()
        color = False
    else:
        color = True
    log_setup(level=level, color=color, timestamp=timestamp, cfg_path='logging.cfg')

    params: Dict[str, Any] = {}
    params['history_filename'] = HISTORY_FILENAME
    params['debug'] = args.debug

    cli = CommandLine(params)

    cmd_line = ' '.join(args.cmd)
    with BusContext(args, cli.plugin_manager) as bus:
        if args.debug and bus:
            bus.set_debug(True)

        if bus:
            params['bus'] = bus
            cli.plugin_manager.set_plugin_bus(bus)
        cli.auto_cmdloop(cmd_line)


def main():
    """This main function saves the stdin termios settings, calls real_main,
       and restores stdin termios settings when it returns.
    """
    save_settings = None
    stdin_fd = -1
    if termios:
        stdin_fd = sys.stdin.fileno()
        save_settings = termios.tcgetattr(stdin_fd)
    try:
        real_main()
    finally:
        if save_settings is not None:
            termios.tcsetattr(stdin_fd, termios.TCSANOW, save_settings)  # type: ignore


if __name__ == '__main__':
    main()
