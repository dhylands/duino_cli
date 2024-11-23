"""
Base class used for plugins.
"""

from typing import Any, Callable, Dict, List, Tuple, Union

# TODO: SHould probably get dump_mem from duino_log
from duino_bus.dump_mem import dump_mem
from duino_cli.command_line_base import CommandLineBase

def add_arg(*args, **kwargs) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
    """Returns a list containing args and kwargs."""
    return (args, kwargs)

class CliPluginBase:

    def __init__(self, cli: CommandLineBase):
        self.cli = cli

    def get_commands(self) -> List[str]:
        """Gets a list of all of the commands."""
        cmds = [x[3:] for x in dir(self.__class__) if x.startswith('do_')]
        return cmds

    def get_command(self, command:str) -> Union[Callable, None]:
        """Retrieves the function object associated with a command."""
        try:
            fn = getattr(self, "do_" + command)
            return fn
        except AttributeError:
            return None

    def get_command_args(self, command:str) -> Union[None,Tuple]:
        """Retrievers the argparse arguments for a command."""
        try:
            argparse_args = getattr(self, "argparse_" + command)
        except AttributeError:
            return None
        return argparse_args

    def print(self, *args, end='\n', file=None) -> None:
        """Like print, but allows for redirection."""
        if file is None:
            file = self.cli.stdout
        line = ' '.join(str(arg) for arg in args) + end
        file.write(line)
        file.flush()

    def dump_mem(self, buf, prefix='', addr=0) -> None:
        """Like print, but allows for redirection."""
        dump_mem(buf, prefix, addr, log=self.print)

    def pr_debug(self, *args, end='\n', file=None) -> None:
        """Prints only when DEBUG is set to true"""
        if self.cli.params['debug']:
            self.print(*args, end, file)
