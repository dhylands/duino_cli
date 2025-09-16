#!/usr/bin/env python3
"""
Implements a logging handler which output above the prompt, and doesn't mess up
the prompt as output is occurring.
"""

import logging

from prompt_toolkit import print_formatted_text, ANSI
from prompt_toolkit.patch_stdout import patch_stdout


class PromptTkLoggingHandler(logging.Handler):
    """Logging handler which doesn't mess up the prompt."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def emit(self, record):
        """Outputs one logging message."""
        # Format the record using the handler's formatter (if set)
        log_message = self.format(record)
        with patch_stdout():
            print_formatted_text(ANSI(log_message))
