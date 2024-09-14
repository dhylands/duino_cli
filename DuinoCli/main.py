#!/usr/bin/env python3
"""
A CLI program for working with microcontrollers.
"""

import argparse
import os
import sys

from gui_app import GuiApp
from log_setup import log_setup
from txt_app import TextApp

HOME = os.getenv('HOME')
HISTORY_FILENAME = f'{HOME}/.cli_history'

def main_gui() -> None:
    """Main program when run as a GUI."""
    gui_app = GuiApp(HISTORY_FILENAME)
    gui_app.run()

def main_no_gui() -> None:
    """Main program when no as a text console."""
    txt_app = TextApp(HISTORY_FILENAME)
    txt_app.run()

def real_main() -> None:
    """Real main"""
    log_setup()
    print('real_main')
    log_setup()
    default_baud = 115200
    try:
        default_baud_str = os.getenv('CLI_BAUD')
        if default_baud_str is not None:
            default_baud = int(default_baud_str)
    except:
        pass
    default_port = os.getenv('CLI_PORT')

    parser = argparse.ArgumentParser(
        prog="pycli",
        usage="%(prog)s [options] [command]",
        description="Python Shell for a Microcontroller board.",
        epilog=("You can specify the default serial port using the " +
                "CLI_PORT environment variable.")
    )
    parser.add_argument(
        "-p", "--port",
        dest="port",
        help="Set the serial port to use (default '%s')" % default_port,
        default=default_port
    )
    parser.add_argument(
        "-b", "--baud",
        dest="baud",
        action="store",
        type=int,
        help="Set the baudrate used (default = %d)" % default_baud,
        default=default_baud
    )
    parser.add_argument(
        "-l", "--list",
        dest="list",
        action="store_true",
        help="Display serial ports",
        default=False
    )
    gui_parser = parser.add_mutually_exclusive_group(required=False)
    gui_parser.add_argument('--gui', dest='gui', action='store_true')
    gui_parser.add_argument('--no-gui', dest='gui', action='store_false')
    parser.set_defaults(gui=False)

    args = parser.parse_args(sys.argv[1:])

    if args.gui:
        main_gui()
    else:
        main_no_gui()


def main():
    """This main function saves the stdin termios settings, calls real_main,
       and restores stdin termios settings when it returns.
    """
    save_settings = None
    stdin_fd = -1
    try:
        import termios
        stdin_fd = sys.stdin.fileno()
        save_settings = termios.tcgetattr(stdin_fd)
    except:
        pass
    try:
        real_main()
    finally:
        if save_settings is not None:
            termios.tcsetattr(stdin_fd, termios.TCSANOW, save_settings)  # type: ignore

if __name__ == '__main__':
    main()
