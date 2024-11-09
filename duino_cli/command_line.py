"""
Sample command line interface for Arduino Projects
"""

import binascii
import logging
from operator import attrgetter
import os
from os import path
import struct
from typing import List, Union, NamedTuple, Tuple

# The File class shoul be moved to the DuinoLittleFs module
from duino_bus.bus import IBus
from duino_bus.packet import ErrorCode, Packet
from duino_bus.packer import Packer
from duino_bus.unpacker import Unpacker
from duino_cli.colors import Color
from duino_cli.command_line_base import add_arg, CommandLineBase


class File(NamedTuple):
    """
    Type information for the File NamedTuple
    """
    filenum: int
    flags: int
    filesize: int
    timestamp: float
    filename: str


FLAGS_DIR = 1

LOGGER = logging.getLogger(__name__)

PING = 0x01  # Check to see if the device is alive.

FORMAT = 0x40  # Format a file system.
INFO = 0x41  # Return info about a file system.
LIST = 0x42  # List files in a directory
MKDIR = 0x43  # Create a new directory.
REMOVE = 0x44  # Remove a file or directory.
RENAME = 0x45  # Rename a file or directory.
COPY = 0x46  # Copy a file
READ = 0x47  # Read data from a file.
WRITE = 0x48  # Write data to a file.
APPEND = 0x49  # Append data to a file.
RMDIR = 0x4a  # Remove a directory.

ERROR_STRS = ['NONE', 'UNABLE_TO_OPEN_FILE', 'WRITE_FAILED', 'READ_FAILED', 'SEEK_FAILED']


def error_str(err: int) -> str:
    """Converts an error code into it's string equivalent."""
    if err < 0 or err > len(ERROR_STRS):
        return '???'
    return ERROR_STRS[err]


class CommandLine(CommandLineBase):  # pylint: disable=too-many-public-methods
    """Command Line Interface (CLI) for the Arduino Boards."""

    def __init__(
            self,
            bus: IBus,
            *args,
            history_filename: str = '',
            capture_output=False,
            **kwargs
    ):
        CommandLineBase.__init__(self, *args, history_filename=history_filename, **kwargs)
        self.bus = bus
        self.log.set_capture_output(capture_output)

    def do_echo(self, args) -> Union[bool, None]:
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
        err, _rsp = self.bus.send_command_get_response(ping)
        if err != ErrorCode.NONE:
            return
        self.print('Device is alive')

    #########################################################################
    ##
    ## The following functions don't really belong here. They should go into
    ## the DuinoLittleFs directory as command_line functions
    ##
    #########################################################################

    argparse_download = (
            add_arg(
                    'filename',
                    metavar='FILE',
                    type=str,
                    help='Name of file to download from Arduino.'
            ),
            add_arg(
                    'dirname',
                    metavar='DIR',
                    type=str,
                    help='Directory on host to place the file in.'
            ),
    )

    def do_download(self, args) -> None:
        """download FILE DIR

           Downloads FILE from the Arduino to the host. The file will
           be placed in the directory DIR.
        """
        src_file = args.filename
        dst_file = path.join(args.dirname, path.basename(src_file))

        self.print(f'Downloading from {src_file} to {dst_file}')

        data_size = self.calc_read_data_size()
        offset = 0
        try:
            # Need to deal with src_file not existing
            with open(dst_file, 'wb') as dst:
                while True:
                    err, data = self.read_file(src_file, offset, data_size)
                    if err != ErrorCode.NONE:
                        break
                    if not data:
                        break
                    offset += len(data)
                    self.print(f'\rRead {offset} bytes', end='')
                    dst.write(data)
                self.print('')
        except FileNotFoundError as err:
            self.print(err)

    def do_format(self, _) -> None:
        """format

            Formats the file system, erasing all data present.
        """
        err = self.format()
        if err == ErrorCode.NONE:
            self.print('Format successful')

    def do_info(self, _) -> None:
        """info

           Sends an INFO request to the Arduino to get information about the LittleFS filesystem.
        """
        info = Packet(INFO)
        err, rsp = self.bus.send_command_get_response(info)
        if err != ErrorCode.NONE or rsp is None:
            return
        total_bytes, used_bytes = struct.unpack('<II', rsp.get_data())
        self.print(
                f'Used: {used_bytes/1024}K of {total_bytes/1024}K '
                f'{round(used_bytes / total_bytes * 100.0, 1)}%'
        )

    argparse_hls = (
            add_arg(
                    'dirname',
                    metavar='DIR',
                    type=str,
                    nargs='*',
                    help='Name of file/directory to list.'
            ),
    )

    def do_hls(self, args) -> None:
        """hls DIR

           Lists the files in a directory from the host computer.
        """
        if not args.dirname:
            args.dirname = ['.']
        for filename in args.dirname:
            files = self.get_host_files(filename)
            for file in files:
                self.print_file(file)

    argparse_ls = (
            add_arg(
                    'dirname',
                    metavar='DIR',
                    type=str,
                    nargs='*',
                    help='Name of file/directory to list.'
            ),
    )

    def do_ls(self, args) -> None:
        """ls DIR

           Lists the files in a directory.
        """
        if not args.dirname:
            args.dirname = ['/']
        for filename in args.dirname:
            files = self.get_files(filename)
            for file in files:
                self.print_file(file)

    def print_file(self, file: File) -> None:
        """Prints a single file."""
        if file.flags & FLAGS_DIR != 0:
            self.print(f'{file.filesize:6d} {Color.DIR_COLOR}{file.filename}{Color.END_COLOR}/')
        else:
            self.print(f'{file.filesize:6d} {file.filename}')

    argparse_mkdir = (
            add_arg('dirname',
                    metavar='DIR',
                    type=str,
                    help='Name of directory to create.'),
    )

    def do_mkdir(self, args) -> None:
        """mkdir DIR

            Creates a directory.
        """
        err = self.mkdir(args.dirname)
        if err == ErrorCode.NONE:
            self.print(f'Created directory {args.dirname}')

    argparse_read = (
            add_arg(
                    '-o',
                    '--offset',
                    dest='offset',
                    action='store',
                    type=int,
                    help='Offset in bytes to write data to.',
                    default=0
            ),
            add_arg('filename',
                    metavar='FILE',
                    type=str,
                    help='Name of file to write into.'),
            add_arg('length',
                    metavar='LENGTH',
                    type=int,
                    help='Number of bytes to read.'),
    )

    def do_read(self, args) -> None:
        """read [-o OFFSET] FILE LENGTH

           Read data from a file.
        """
        length = self.calc_read_data_size()
        err, data = self.read_file(args.filename, args.offset, length)
        if err != ErrorCode.NONE or data is None:
            self.print(f'Error reading from {args.filename}')
        else:
            self.print(f'Read {len(data)} bytes from {args.filename}')
            self.dump_mem(data, 'Read', args.offset)

    argparse_remove = (
            add_arg('filename',
                    metavar='FILE',
                    type=str,
                    help='Name of file to remove.'),
    )

    def do_remove(self, args) -> None:
        """remove FILE

            Removes a file.
        """
        err = self.remove(args.filename)
        if err == ErrorCode.NONE:
            self.print(f'File {args.filename} removed')

    argparse_upload = (
            add_arg('filename',
                    metavar='FILE',
                    type=str,
                    help='Name of file to upload.'),
            add_arg(
                    'dirname',
                    metavar='DIR',
                    type=str,
                    help='Directory on Arduino to place the file in.'
            ),
    )

    argparse_rmdir = (
            add_arg('dirname',
                    metavar='DIR',
                    type=str,
                    help='Name of directory to create.'),
    )

    def do_rmdir(self, args) -> None:
        """rmdir DIR

            Removes a directory.
        """
        err = self.rmdir(args.dirname)
        if err == ErrorCode.NONE:
            self.print(f'Removed directory {args.dirname}')

    def do_upload(self, args) -> None:
        """upload FILE DIR

           Uploads FILE from the host to the Arduino. The file will
           be placed in the directory DIR.
        """
        src_file = args.filename
        dst_file = path.join(args.dirname, path.basename(src_file))

        self.print(f'Uploading from {src_file} to {dst_file}')

        data_size = self.calc_write_data_size(dst_file)
        try:
            with open(src_file, 'rb') as src:
                data = src.read(data_size)
                self.write_file(dst_file, data)
                bytes_written = len(data)
                self.print(f'\rWrote {bytes_written} bytes', end='')
                while (data := src.read(data_size)) != b'':
                    self.append_file(dst_file, data)
                    bytes_written += len(data)
                    self.print(f'\rWrote {bytes_written} bytes', end='')
                self.print('')
        except FileNotFoundError as err:
            self.print(err)

    argparse_write = (
            add_arg(
                    '--hex',
                    dest='hex',
                    action='store_true',
                    help='Interpret data as ASCII Hex data',
                    default=False
            ),
            add_arg(
                    '-o',
                    '--offset',
                    dest='offset',
                    action='store',
                    type=int,
                    help='Offset in bytes to write data to.',
                    default=0
            ),
            add_arg('filename',
                    metavar='FILE',
                    type=str,
                    help='Name of file to write into.'),
            add_arg(
                    'string',
                    metavar='STRING',
                    nargs='+',
                    type=str,
                    help='String data to write into file.'
            ),
    )

    def do_write(self, args) -> None:
        """write [--hex] [-o OFFSET] FILE STRING...

           Write data into a file.
        """
        data = bytes(' '.join(args.string), 'utf-8')
        if args.hex:
            data = binascii.unhexlify(data.replace(b' ', b''))
        else:
            data += b'\n'

        err = self.write_file(args.filename, data)

        if err != ErrorCode.NONE:
            self.print(f'Error: {error_str(err)} writing to {args.filename}')
            return
        self.print(f'Wrote {len(data)} bytes into {args.filename}')

    #########################################################################
    ##
    ## The following functions don't really belong here. They should go into
    ## the DuinoLittleFs directory as bus/packet functions.
    ##
    #########################################################################

    def append_file(self, filename: str, data: Union[bytes, bytearray]) -> int:
        """Sends an APPEND command and parses the reposnee.

           The append operation appends to an existing file.
        """
        return self.write_or_append_file(APPEND, filename, data)

    def calc_read_data_size(self) -> int:
        """Calculates the maximum amount of data that can be included in
           a READ packet.
        """
        # The beginning of the packet has the following fields
        #   1 - Error Code
        #   4 - Offset
        #   4 - Length
        #   The remainder of the packet is the data
        header_len = 1 + 4 + 4
        return Packet.MAX_DATA_LEN - header_len - 20

    def calc_write_data_size(self, filename: str) -> int:
        """Calculates the maximum amount of data that can be included in
           a WRITE or APPEND packet.
        """
        # The beginning of the packet has the following fields
        #   N - Filename (N = length of filename + 2)
        #   4 - Length of data
        #   The remainder of the packet is the data
        header_len = len(filename) + 2 + 4
        return Packet.MAX_DATA_LEN - header_len - 20

    def format(self) -> int:
        """Sends a FORMAT command to the Arduino."""
        fmt = Packet(FORMAT)
        err, rsp = self.bus.send_command_get_response(fmt, timeout=10)
        if err != ErrorCode.NONE:
            self.print(f'Error: {error_str(err)} sending FORMAT command')
            return err
        if rsp is None:
            self.print('Error: timeout sending FORMAT command')
            return ErrorCode.TIMEOUT
        unpacker = Unpacker(rsp.get_data())
        err = unpacker.unpack_u8()
        if err != ErrorCode.NONE:
            self.print(f'Error: {error_str(err)} formatting file system')
            return err
        return ErrorCode.NONE

    def get_host_files(self, dirname: str) -> List[File]:
        """Retrieves a list of files from the host computer."""
        files = []
        filenum = 0
        with os.scandir(dirname) as it:
            for entry in it:
                if entry.is_dir():
                    flags = FLAGS_DIR
                else:
                    flags = 0
                st = entry.stat()
                files.append(File(filenum, flags, st.st_size, st.st_mtime, entry.name))
                filenum += 1
        return sorted(files, key=attrgetter("filename"))

    def get_files(self, dirname: str) -> List[File]:
        """Retrieves a list of files from the device."""
        files = []
        index = 0
        while some_files := self.list_files(index, dirname):
            files.extend(some_files)
            index += len(some_files)
        return sorted(files, key=attrgetter("filename"))

    def list_files(self, index: int, filename: str) -> List[File]:
        """Sends a LIST command and parses the response."""
        files = []
        read = Packet(LIST)
        packer = Packer(read)
        packer.pack_u16(index)
        packer.pack_str(filename)
        err, rsp = self.bus.send_command_get_response(read)
        if err != ErrorCode.NONE or rsp is None:
            self.print(f'Error: {error_str(err)} reading LIST from {filename} index: {index}')
            return []
        unpacker = Unpacker(rsp.get_data())
        while unpacker.more_data():
            filenum = unpacker.unpack_u16()
            flags = unpacker.unpack_u8()
            filesize = unpacker.unpack_u32()
            timestamp = unpacker.unpack_u32()
            filename = str(unpacker.unpack_str())
            files.append(File(filenum, flags, filesize, timestamp, filename))
        return files

    def mkdir(self, dirname: str) -> int:
        """Sends a MKDIR command annd parses the response."""
        mkd = Packet(MKDIR)
        packer = Packer(mkd)
        packer.pack_str(dirname)
        err, rsp = self.bus.send_command_get_response(mkd)
        if err != ErrorCode.NONE:
            self.print(f'Error: {error_str(err)} sending MKDIR command')
            return err
        if rsp is None:
            self.print('Error: timeout sending MKDIR command')
            return ErrorCode.TIMEOUT
        unpacker = Unpacker(rsp.get_data())
        err = unpacker.unpack_u8()
        if err != ErrorCode.NONE:
            self.print(f'Error: {error_str(err)} creating directory {dirname}')
            return err
        return ErrorCode.NONE

    def read_file(self,
                  filename: str,
                  offset: int,
                  length: int) -> Tuple[int,
                                        Union[None,
                                              bytes,
                                              bytearray]]:
        """Sends a READ command and parses the response."""
        read = Packet(READ)
        packer = Packer(read)
        packer.pack_str(filename)
        packer.pack_u32(offset)
        packer.pack_u32(length)
        err, rsp = self.bus.send_command_get_response(read)
        if err != ErrorCode.NONE:
            return (err, None)
        if rsp is None:
            return (ErrorCode.TIMEOUT, None)
        unpacker = Unpacker(rsp.get_data())
        err = unpacker.unpack_u8()
        _r_offset = unpacker.unpack_u32()
        r_length = unpacker.unpack_u32()
        data = unpacker.unpack_data(r_length)

        if err != ErrorCode.NONE:
            self.print(f'Error: {error_str(err)} reading from {filename}')
            return (err, None)
        return (ErrorCode.NONE, data)

    def remove(self, filename: str) -> int:
        """Sends a REMOVE command annd parses the response."""
        rem = Packet(REMOVE)
        packer = Packer(rem)
        packer.pack_str(filename)
        err, rsp = self.bus.send_command_get_response(rem)
        if err != ErrorCode.NONE:
            self.print(f'Error: {error_str(err)} sending REMOVE command')
            return err
        if rsp is None:
            self.print('Error: timeout sending REMOVE command')
            return ErrorCode.TIMEOUT
        unpacker = Unpacker(rsp.get_data())
        err = unpacker.unpack_u8()
        if err != ErrorCode.NONE:
            self.print(f'Error: {error_str(err)} removing {filename}')
            return err
        return ErrorCode.NONE

    def rmdir(self, dirname: str) -> int:
        """Sends a RMDIR command annd parses the response."""
        rmd = Packet(RMDIR)
        packer = Packer(rmd)
        packer.pack_str(dirname)
        err, rsp = self.bus.send_command_get_response(rmd)
        if err != ErrorCode.NONE:
            self.print(f'Error: {error_str(err)} sending RMDIR command')
            return err
        if rsp is None:
            self.print('Error: timeout sending RMDIR command')
            return ErrorCode.TIMEOUT
        unpacker = Unpacker(rsp.get_data())
        err = unpacker.unpack_u8()
        if err != ErrorCode.NONE:
            self.print(f'Error: {error_str(err)} removing directory {dirname}')
            return err
        return ErrorCode.NONE

    def write_file(self, filename: str, data: Union[bytes, bytearray]) -> int:
        """Sends a WRITE command and parses the response.

            The write opeartion will create a file if it doesn't already exist,
            and will erase a file if it exists already.
        """
        return self.write_or_append_file(WRITE, filename, data)

    def write_or_append_file(self, cmd: int, filename: str, data: Union[bytes, bytearray]) -> int:
        """Sends a WRITE or APPEND command and parses the response."""
        write = Packet(cmd)
        length = len(data)

        packer = Packer(write)
        packer.pack_str(filename)
        packer.pack_u32(length)
        packer.pack_data(data)
        err, rsp = self.bus.send_command_get_response(write, timeout=10)
        if err != ErrorCode.NONE:
            return err
        if rsp is None:
            return ErrorCode.TIMEOUT

        unpacker = Unpacker(rsp.get_data())
        return unpacker.unpack_u8()
