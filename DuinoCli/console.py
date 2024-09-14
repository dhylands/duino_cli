"""
Base class for a console .
"""

import logging
from typing import Callable, List

LOGGER = logging.getLogger(__name__)


class Console:

    def __init__(self, history_filename: str) -> None:
        """Constructor."""
        self.history_filename = history_filename
        self.history: List[str] = []
        self.history_idx = -1
#        self.line_entered_cb = self.default_line_entered_cb

    def quit(self) -> None:
        """Function called to quit."""

#    def line_entered(self, line) -> None:
#        """Called when the user completes entering a line."""
#        self.add_line_to_history(line)

#    def set_line_entered_callback(self, callback: Callable[[str], None]) -> None:
#        """Sets the function that will be called whenever a line is entered."""
#        self.line_entered_cb = callback

#    def default_line_entered_cb(self, line: str) -> None:  # pylint: disable=no-self-use
#        """Default callback function when no user-supplie one is set"""
#        LOGGER.info('Line Entered: %s', line)

