#!/usr/bin/env python3
"""
Front-end script for launching the CLI
"""

import traceback
from duino_cli import main

try:
    main.main()
except:  # pylint: disable=bare-except
    traceback.print_exc()
