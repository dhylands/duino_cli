"""
Function for printing a list of items in multiple columns.
"""

from typing import Callable, List
from duino_cli.column import align_cell, default_print


def columnize(items: List[str],
              display_width=80,
              print_func: Callable[[str], None] = default_print) -> None:
    """Prints a columnar list, adjusting the width of each column so everything fits.
    Unlike column_print, which prints a list of rows, this function prints
    several columns of a single entitiy (in a similar fashion to ls).

    This function is essentially a copy of Cmd.columnize with a pluggable print_func
    """
    # Start out with a single row, and then increase the number of rows
    # until everything fits.
    num_items = len(items)
    column_sep = '  '
    for nrows in range(1, num_items):
        ncols = (num_items + nrows - 1) // nrows
        column_width = []
        total_width = -len(column_sep)
        for col in range(ncols):
            col_width = 0
            for row in range(nrows):
                i = nrows * col + row
                if i >= num_items:
                    break
                col_width = max(col_width, len(items[i]))
            column_width.append(col_width)
            total_width += col_width + len(column_sep)
            if total_width > display_width:
                # This number of rows is too wide
                break
        if total_width <= display_width:
            # We found a number of columns that will fit
            break
    else:
        # Nothing fits, use a single column
        nrows = num_items
        ncols = 1
        column_width = [0]
    for row in range(nrows):
        line_items = []
        for col in range(ncols):
            i = nrows * col + row
            if i < num_items:
                line_items.append(align_cell('<', items[i], column_width[col]))
        print_func(column_sep.join(line_items))


if __name__ == "__main__":
    print('===== Empty List =====')
    columnize([])
    print('===== List with 1 item =====')
    columnize(['one'])
    print('===== List with 2 items =====')
    columnize(['one', 'two'])
    print('===== List which should print on 1 line =====')
    columnize([
        '12345678', '12345678', '12345678', '12345678', '12345678', '12345678', '12345678',
        '12345678 <'
    ])
    print('===== List which should print on 2 lines =====')
    columnize([
        '12345678', '12345678', '12345678', '12345678', '12345678', '12345678', '12345678',
        '12345678  <'
    ])
    print('===== List that should print in one column =====')
    columnize(['12345678', '12345678', '123456789abc<', '12345678'], display_width=8)
