"""
   ANSI color sequences.
"""

# Attributes
# 0 Reset all attributes
# 1 Bright
# 2 Dim
# 4 Underscore
# 5 Blink
# 7 Reverse
# 8 Hidden

LT_BLACK = "\x1b[1;30m"
LT_RED = "\x1b[1;31m"
LT_GREEN = "\x1b[1;32m"
LT_YELLOW = "\x1b[1;33m"
LT_BLUE = "\x1b[1;34m"
LT_MAGENTA = "\x1b[1;35m"
LT_CYAN = "\x1b[1;36m"
LT_WHITE = "\x1b[1;37m"

DK_BLACK = "\x1b[2;30m"
DK_RED = "\x1b[2;31m"
DK_GREEN = "\x1b[2;32m"
DK_YELLOW = "\x1b[2;33m"
DK_BLUE = "\x1b[2;34m"
DK_MAGENTA = "\x1b[2;35m"
DK_CYAN = "\x1b[2;36m"
DK_WHITE = "\x1b[2;37m"

NO_COLOR = "\x1b[0m"
BG_LT_BLACK = "\x1b[1;40m"
BG_LT_RED = "\x1b[1;41m"
BG_LT_GREEN = "\x1b[1;42m"
BG_LT_YELLOW = "\x1b[1;43m"
BG_LT_BLUE = "\x1b[1;44m"
BG_LT_MAGENTA = "\x1b[1;45m"
BG_LT_CYAN = "\x1b[1;46m"
BG_LT_WHITE = "\x1b[1;47m"

BG_DK_BLACK = "\x1b[2;40m"
BG_DK_RED = "\x1b[2;41m"
BG_DK_GREEN = "\x1b[2;42m"
BG_DK_YELLOW = "\x1b[2;43m"
BG_DK_BLUE = "\x1b[2;44m"
BG_DK_MAGENTA = "\x1b[2;45m"
BG_DK_CYAN = "\x1b[2;46m"
BG_DK_WHITE = "\x1b[2;47m"


class Color:  # pylint: disable=too-few-public-methods
    """
        ANSI color sequences.
    """
    DIR_COLOR: str = LT_CYAN
    PROMPT_COLOR: str = LT_GREEN
    PY_COLOR: str = DK_GREEN
    END_COLOR: str = NO_COLOR

    NO_COLOR: str = NO_COLOR

    WARNING_COLOR: str = LT_YELLOW
    INFO_COLOR: str = ''
    DEBUG_COLOR: str = LT_BLUE
    CRITICAL_COLOR: str = LT_RED
    ERROR_COLOR: str = LT_RED


def set_nocolor() -> None:
    """Disables color sequences."""
    for key in Color.__dict__:
        if key.endswith('_COLOR'):
            setattr(Color, key, '')
