"""
Implements a GUI console with an input
"""

import logging
import queue
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import ttk, HORIZONTAL

from duino_cli.command_line import CommandLine
from duino_cli.console import Console
from duino_cli.redirect import RedirectStdoutStderr

LOGGER = logging.getLogger(__name__)


class LogHandler(logging.Handler):
    """
    Class to send logging records to a queue

    It can be used from different threads
    The Console class polls this queue to display records in a ScrolledText widget
    """

    # Example from Moshe Kaplan: https://gist.github.com/moshekaplan/c425f861de7bbf28ef06
    # (https://stackoverflow.com/questions/13318742/python-logging-to-tkinter-text-widget) is not thread safe!            # pylint: disable=line-too-long
    # See https://stackoverflow.com/questions/43909849/tkinter-python-crashes-on-new-thread-trying-to-log-on-main-thread  # pylint: disable=line-too-long

    def __init__(self, log_queue) -> None:
        """Constructor"""
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record) -> None:
        """Adds a log record to the queue."""
        self.log_queue.put(record)


class GuiConsole(Console):  # pylint: disable=too-many-instance-attributes
    """Poll messages from a logging queue and display them in a scrolled text widget"""

    def __init__(self, cli: CommandLine, frame, root, history_filename: str) -> None:
        """Constructor."""
        super().__init__(history_filename)
        self.cli = cli
        self.frame = frame
        self.root = root
        # Create a ScrolledText wdiget
        self.scrolled_text = ScrolledText(frame, state='disabled', height=12)
        self.scrolled_text.grid(column=0, row=0, sticky="NSWE")
        self.scrolled_text.configure(font='TkFixedFont')
        self.scrolled_text.tag_config('INFO', foreground='black')
        self.scrolled_text.tag_config('DEBUG', foreground='gray')
        self.scrolled_text.tag_config('WARNING', foreground='orange')
        self.scrolled_text.tag_config('ERROR', foreground='red')
        self.scrolled_text.tag_config('CRITICAL', foreground='red', underline=True)

        self.input_pane = ttk.PanedWindow(self.frame, orient=HORIZONTAL)
        self.input_pane.grid(column=0, row=1, sticky='WE')

        self.prompt_str = tk.StringVar()
        self.prompt_str.set('CLI>')
        self.prompt = ttk.Label(self.input_pane, textvariable=self.prompt_str)
        self.prompt.grid(column=0, row=0, sticky='W')
        self.input_pane.add(self.prompt, weight=0)

        self.message = tk.StringVar()
        self.input = ttk.Entry(self.input_pane, textvariable=self.message)
        self.input.bind('<Return>', self.gui_line_entered)
        self.input.bind('<Up>', self.key_entered)
        self.input.bind('<Down>', self.key_entered)
        self.input.grid(column=1, row=0, sticky='E')
        self.input_pane.add(self.input, weight=1)

        # Create a logging handler using a queue
        self.log_queue = queue.Queue()
        self.queue_handler = LogHandler(self.log_queue)
        formatter = logging.Formatter('%(asctime)s.%(msecs)03d: %(message)s', datefmt='%H:%M:%S')
        self.queue_handler.setFormatter(formatter)
        logging.getLogger('').addHandler(self.queue_handler)
        # Start polling messages from the queue
        self.frame.after(100, self.poll_log_queue)

    def gui_line_entered(self, _ev) -> str:
        """Called when the user presses ENTER."""
        line = self.message.get()

        self.history_idx = -1
        self.message.set('')
        if line:
            LOGGER.info('CLI> %s', line)
            with RedirectStdoutStderr(self.cli.log):
                stop = self.cli.auto_cmdloop(line)
                if stop:
                    self.quit()
        return "break"

    def key_entered(self, evt) -> str:
        """Called when the up/down arrow keys are entered."""
        if evt.keysym == 'Up':
            if self.history_idx < 0:
                self.history_idx = len(self.history)
            self.history_idx = max(0, self.history_idx - 1)
        elif evt.keysym == 'Down':
            self.history_idx = min(len(self.history), self.history_idx + 1)
        if self.history_idx < 0 or self.history_idx >= len(self.history):
            line = ''
        else:
            line = self.history[self.history_idx]
        self.message.set(line)
        self.input.icursor(len(line))
        return "break"

    def focus_set(self) -> None:
        """Sets the focus to the input area."""
        self.input.focus_set()

    def display(self, record) -> None:
        """Displays a log record into the scrollable window area."""
        msg = self.queue_handler.format(record)
        self.scrolled_text.configure(state='normal')
        self.scrolled_text.insert(tk.END, msg + '\n', record.levelname)
        self.scrolled_text.configure(state='disabled')
        # Autoscroll to the bottom
        self.scrolled_text.yview(tk.END)

    def poll_log_queue(self) -> None:
        """Periodically pulls log records from the queue."""
        # Check every 100ms if there is a new message in the queue to display
        while True:
            try:
                record = self.log_queue.get(block=False)
            except queue.Empty:
                break
            else:
                self.display(record)
        self.frame.after(100, self.poll_log_queue)

    def quit(self) -> None:
        """Quits the program."""
        self.root.quit()
