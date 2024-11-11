#!/usr/bin/env python3
"""
Front-end script for launching the CLI
"""

import traceback
from duino_cli.duino_cli import main

try:
    main()
except:  # pylint: disable=bare-except
    traceback.print_exc()
