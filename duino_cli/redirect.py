"""Implements a context manager which allows stdout and stderr to be redirected to a log"""

import sys
from typing import Union


class RedirectStdoutStderr:
    """Redirects stdout and stderr to a stream"""

    def __init__(self, stream) -> None:
        # Save the old std streams
        self.old_stream = sys.stdout
        self.old_error_stream = sys.stderr
        self.fstream = stream

    def __enter__(self) -> None:
        # Change the std streams to your streams when entering
        sys.stdout = self.fstream
        sys.stderr = self.fstream

    def __exit__(self, exc_type, exc_value, exc_traceback) -> Union[bool, None]:
        # Change the std streams back to the original streams while exiting
        sys.stdout = self.old_stream
        sys.stderr = self.old_error_stream

        if exc_type == SystemExit:
            # argparse calls sys.exit when it prints help
            # returning True supresses re-raising the exception
            return True
        return None
