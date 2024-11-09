"""
Implements a Text based app.
"""

from duino_bus.bus import IBus
from duino_cli.command_line import CommandLine


class TextApp:  # pylint: disable=too-few-public-methods
    """Traditional console based application."""

    def __init__(self, history_filename: str) -> None:
        """Constructor."""
        self.history_filename = history_filename

    def run(self, bus: IBus) -> None:
        """Runs the application."""
        cli = CommandLine(bus, history_filename=self.history_filename)
        cli.auto_cmdloop('')
        cli.save_history()
