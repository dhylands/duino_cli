#!/usr/bin/env python3
"""Print nicely formatted columns."""

from typing import cast, Callable, List, Union


def align_cell(fmt: str, elem: str, width: int) -> str:
    """Returns an aligned element."""
    if fmt == '<':
        return elem + ' ' * (width - len(elem))
    if fmt == '>':
        return ' ' * (width - len(elem)) + elem
    return elem


def default_print(line: str) -> None:
    """Print routine used if none is supplied."""
    print(line)


def column_print(
        fmt: str,
        rows: List[Union[str,
                         List[str]]],
        print_func: Callable[[str],
                             None] = default_print
) -> None:
    """Prints a formatted list, adjusting the width so everything fits.
    fmt contains a single character for each column. < indicates that the
    column should be left justified, > indicates that the column should
    be right justified. The last column may be a space which imples left
    justification and no padding.

    """
    # Figure out the max width of each column
    num_cols = len(fmt)
    # yapf: disable
    width = [
        max(0 if isinstance(row,
                            str) else len(row[i]) for row in rows) for i in range(num_cols)
    ]
    # yapf: enable
    for row in rows:
        if isinstance(row, str):
            sep = cast(str, row)
            # Print a seperator line
            print_func(' '.join([sep * width[i] for i in range(num_cols)]))
        else:
            print_func(' '.join([align_cell(fmt[i], row[i], width[i]) for i in range(num_cols)]))


if __name__ == "__main__":
    FMT = '<> '
    # yapf: disable
    ROWS: List[Union[str, List[str]]] = [
        ['A', 'BBBBB', 'CC'],
        '-',
        ['12', 'a', 'Description'],
        ['1', 'abc', ''],
        '=',
        ['123', 'abcdef', 'WooHoo']
    ]
    # yapf: enable
    column_print(FMT, ROWS)
