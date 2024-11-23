"""
Implements a Text based app.
"""

from typing import Any, Dict

from duino_cli.command_line import CommandLine


class TextApp:  # pylint: disable=too-few-public-methods
    """Traditional console based application."""

    def __init__(self, params: Dict[str, Any]) -> None:
        """Constructor."""
        self.params = params

    def run(self) -> None:
        """Runs the application."""
        cli = CommandLine(self.params)
        cli.auto_cmdloop('')
        cli.save_history()
