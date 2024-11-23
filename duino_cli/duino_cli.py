#!/usr/bin/env python3
"""
A CLI program for working with microcontrollers.
"""

import argparse
import os
import sys

try:
    import termios
except ModuleNotFoundError:
    termios = None  # pylint: disable=invalid-name

from typing import Any, Dict\

import serial.tools.list_ports
from serial import SerialException

from duino_bus.serial_bus import SerialBus
from duino_bus.socket_bus import SocketBus

from duino_cli import colors
# from duino_cli.gui_app import GuiApp
from duino_cli.log_setup import log_setup
from duino_cli.txt_app import TextApp

HOME = os.getenv('HOME')
HISTORY_FILENAME = f'{HOME}/.cli_history'


def extra_info(port):
    """Collects the serial nunber and manufacturer into a string, if
       the fields are available."""
    extra_items = []
    if port.manufacturer:
        extra_items.append(f"vendor '{port.manufacturer}'")
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
            print(
                    f'USB Serial Device {port.vid:04x}:{port.pid:04x}{extra_info(port)} '
                    f'found @{port.device}'
            )
    if not detected:
        print('No serial devices detected')


#def main_gui(params: Dict[str, Any]) -> None:
#    """Main program when run as a GUI."""
#    gui_app = GuiApp(params)
#    gui_app.run()


def main_no_gui(params: Dict[str, Any]) -> None:
    """Main program when no as a text console."""
    txt_app = TextApp(params)
    txt_app.run()


def real_main() -> None:
    """Real main"""
    log_setup()
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
            formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
            '-p',
            '--port',
            dest='port',
            help=f'Set the serial port to use (default = {default_port})',
            default=default_port
    )
    parser.add_argument(
            '-b',
            '--baud',
            dest='baud',
            action='store',
            type=int,
            help=f'Set the baudrate used (default = {default_baud})',
            default=default_baud
    )
    parser.add_argument(
            '-l',
            '--list',
            dest='list',
            action='store_true',
            help='Display serial ports',
            default=False
    )
    parser.add_argument(
            '-n',
            '--net',
            dest='net',
            action='store_true',
            help=f'Connect to a duino_cli_server (localhost:{SocketBus.DEFAULT_PORT})'
    )
    parser.add_argument(
            '-d',
            '--debbug',
            dest='debug',
            action='store_true',
            help='Turn on some debug'
    )
    parser.add_argument(
            "--nocolor",
            dest="nocolor",
            action="store_true",
            help="Turn off colorized output",
            default=default_nocolor
    )

    #gui_parser = parser.add_mutually_exclusive_group(required=False)
    #gui_parser.add_argument('--gui', dest='gui', action='store_true')
    #gui_parser.add_argument('--no-gui', dest='gui', action='store_false')
    #parser.set_defaults(gui=False)

    try:
        args = parser.parse_args(sys.argv[1:])
    except SystemExit:
        return

    if args.list:
        list_ports()
        return

    if args.nocolor:
        colors.set_nocolor()

    params = {}
    #params['plugins_dir'] = args.plugins_dir
    params['history_filename'] = HISTORY_FILENAME

    bus = SocketBus()
    if args.net:
        bus = SocketBus()
        bus.connect_to_server('localhost', SocketBus.DEFAULT_PORT)
    else:
        bus = SerialBus()
        try:
            bus.open(args.port, baudrate=args.baud)
        except SerialException as err:
            print(err)
            return

    if args.debug:
        bus.set_debug(True)

    params['bus'] = bus
    params['debug'] = args.debug

    #if args.gui:
    #    main_gui(params)
    #else:
    main_no_gui(params)


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
