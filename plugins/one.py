from typing import List, Union

from duino_bus.packet import ErrorCode, Packet
from duino_cli.cli_plugin_base import CliPluginBase
from duino_cli.command_line_base import CommandLineBase

PING = 0x01  # Check to see if the device is alive.

class CliPlugin(CliPluginBase):

    def __init__(self, cli: CommandLineBase):
        super().__init__(cli)

    def do_args(self, args: List[str]) -> Union[bool, None]:
        """args [arguments...]

           Debug function for verifying argument parsing. This function just
           prints out each argument that it receives.
        """
        for idx, arg in enumerate(args):
            self.print(f"arg[{idx}] = '{arg}'")

    def do_echo(self, args: List[str]) -> Union[bool, None]:
        """echo [STRING]...

           Similar to linux echo.
        """
        line = ' '.join(args[1:])
        self.print(line)

    def do_ping(self, _) -> None:
        """ping

           Sends a PING packet to the arduino and reports a response.
        """
        ping = Packet(PING)
        err, _rsp = self.cli.bus.send_command_get_response(ping)
        if err != ErrorCode.NONE:
            return
        self.print('Device is alive')

