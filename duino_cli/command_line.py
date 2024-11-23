"""
Sample command line interface for Arduino Projects
"""

import logging
from typing import Any, cast, Dict

# The File class shoul be moved to the duino_littlefs module
from duino_bus.bus import IBus
from duino_cli.command_line_base import CommandLineBase

LOGGER = logging.getLogger(__name__)


class CommandLine(CommandLineBase):  # pylint: disable=too-many-public-methods
    """Command Line Interface (CLI) for the Arduino Boards."""

    def __init__(self, params: Dict[str, Any], *args, capture_output=False, **kwargs):
        super().__init__(params, *args, **kwargs)
        self.bus = cast(IBus, params['bus'])
        self.log.set_capture_output(capture_output)
