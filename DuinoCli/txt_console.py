"""
Implements a text based console.
"""

from console import Console

class TextConsole(Console):
    """Traditional text based console."""

    def __init__(self, history_filename: str) -> None:
        """Constructor."""
        super().__init__(history_filename)

    def quit(self) -> None:
        """Quits the program."""
