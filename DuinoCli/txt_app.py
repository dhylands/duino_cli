"""
Implements a Text based app.
"""

from command_line import CommandLine

class TextApp:
    """Traditional console based application."""

    def __init__(self, history_filename: str) -> None:
        """Constructor."""
        self.history_filename = history_filename

    def run(self) -> None:
        """Runs the application."""
        cli = CommandLine(self.history_filename)
        cli.auto_cmdloop('')
