"""
Implements a GUI based app.
"""

import signal

import tkinter as tk
from tkinter import ttk, HORIZONTAL

from duino_bus.bus import IBus
from duino_cli.command_line import CommandLine
from duino_cli.gui_console import GuiConsole


class App:  # pylint: disable=too-few-public-methods
    """The class for the main application."""

    def __init__(self, root, bus: IBus, history_filename: str) -> None:
        self.root = root
        root.title('Command Line Interface')
        root.minsize(400, 400)
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)

        horizontal_pane = ttk.PanedWindow(self.root, orient=HORIZONTAL)
        horizontal_pane.grid(row=0, column=0, sticky='NSEW')

        console_frame = ttk.Labelframe(horizontal_pane, width=1000, text="Console")
        console_frame.columnconfigure(0, weight=1)
        console_frame.rowconfigure(0, weight=1)
        horizontal_pane.add(console_frame, weight=1)
        console_frame.grid_propagate(False)
        self.cli = CommandLine(bus, history_filename=history_filename)
        self.console = GuiConsole(self.cli, console_frame, self.root, history_filename)
        self.console.focus_set()

        self.root.protocol('WM_DELETE_WINDOW', self.quit)
        self.root.bind('<Control-q>', self.quit)
        signal.signal(signal.SIGINT, self.quit)

    def quit(self, *_args) -> None:
        """Callback used for various ways of quitting."""
        self.root.destroy()
        self.cli.save_history()


class GuiApp:  # pylint: disable=too-few-public-methods
    """Creates objects needed to run a GUI app."""

    def __init__(self, history_filename: str) -> None:
        """Constructor."""
        self.history_filename = history_filename

    def run(self, bus: IBus) -> None:
        """Runs the main application."""
        root = tk.Tk()
        app = App(root, bus, self.history_filename)
        app.root.mainloop()
