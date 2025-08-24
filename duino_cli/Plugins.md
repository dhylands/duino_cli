How plugins work

Uses the python entry_points mechanism and metadata.

entry_points can be used to create a console script by adding something
like the following tp your setup.py
```
    entry_points={
            'console_scripts': ['cli=duino_cli.duino_cli:main'],
    },
```
This causees a script called `cli` to be created when you `pip intall`
your package. The `cli` script will call the function `main` from the
`duino_cli.duino_cli` module. Under linux, the script will typically
look like the following:
```
#!/home/dhylands/Arduino/.direnv/python-3.9.21/bin/python3.9
# -*- coding: utf-8 -*-
import re
import sys
from duino_cli.duino_cli import main
if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0])
    sys.exit(main())
```
The line `from duino_cli.duino_cli import main` is generated using the
portion after `cli=`. The name of the file will be the name before the
`=`. The second to the last line sets up `sys.argv` to be the arguments
passed into the `cli` script and the last line calls the `main` function
(or whatever fucntion you specified after the colon).

You can also export additional meta-data which can be queried from
within your python program. You can use
`importlib.metadata.entry_points()` to get a dictionary of all
entry_points currently installed in your python installation.

The keys from this dictionary come from the `setup.py` script, so the
example console script above would have added an entry to the
`console_scripts` key. If you were to do:
`importlib.metadata.entry_points()['console_scripts']` this would return
a tuple, and one of the entries of that tuple would look something like
this:
```
EntryPoint(name='cli', value='duino_cli.duino_cli:main', group='console_scripts')
```

You can add your own metadata, which is how the plugin mechanism is
implemented. For the duino_cli program, it looks for metadata with the
key `duino_cli.plugin`. Each entry in the tuple corresponds to a plugin
entry point. The value before the `=` is the name of the plugin, the
value after the `=` is considered to be the name of a class derived from
the `CliPluginBase` class.

For example, the following entry:
```
    entry_points={
            'duino_cli.plugin': ['my_name=my_module.filename_base:ClassName']
    },
```
would look for a class named `ClassName` from the filename_base.py file
found in the module named `my_module`

This is the code which loads the plugin:
```py
    def load_plugins(self) -> None:
        """Loads plugins which have been installed."""
        plugin_entry_points = importlib.metadata.entry_points()['duino_cli.plugin']
        for plugin_entry_point in plugin_entry_points:
            plugin_name = plugin_entry_point.name
            LOGGER.info('Loading Plugin %s ...', plugin_name)
            if self.params['debug']:
                LOGGER.info('  %s', plugin_entry_point)
            try:
                plugin_class = plugin_entry_point.load()
                plugin = plugin_class(self.output, self.params)
                self.plugins[plugin_name] = plugin
            except Exception:  # pylint: disable=broad-exception-caught
                LOGGER.error('Error encountered while loading plugin %s', plugin_name)
                traceback.print_exc()
        LOGGER.info('All plugins loaded')
```

The class constructor is called from this line:
```
                plugin = plugin_class(self.output, self.params)
```
which passes in the output class (derived from `CommandLineOutput`), and
a `params` dictionary. `params['bus']` contains a reference to the
bus used to communicate with the board (derived from `duino_bus.IBus`),
typically an instance of `duino_bus.SerialBus`.

## Adding your own commands

The `ClassName` (which is the name of your plugin class) can contain
functions which start with `do_`. Each of these functions will be added
as a function which can be called by the user.

An example of this might look like the following:
```py

READ_TEMPERATURE = 0x80  # ID for the MY_COMMAND packet

class ClassName(CliPluginBase):
    """Defines Custome commands."""

    def __init__(self, output: CommandLineOutput, params: Dict[str,
                                                               Any]) -> None:
        super().__init__(output, params)
        self.bus = params['bus']

    def execute_cmd(self, fn: Callable[[argparse.Namespace], bool],
                    args: argparse.Namespace) -> Union[bool, None]:
        """Executes a command from this plugin.

            Plugins can override this function to do plugin wide checking.
        """
        # All of the commands in this file require a board, so we check for it here.
        if self.bus is None:
            self.error('No board connected')
            return False
        return fn(args)

    argparse_read_temperature = (
        add_arg(
            'sensor_id',
            metavar='SENSOR_ID',
            type=int,
            help='ID of the sensor to read the temperature from',
        ),
    )

    def do_read_temperature(self, args) -> None:
        """read_temperature SENSOR_ID

           Reads the temperature from the temperature sensor given by `SENSOR_ID`.
        """
        self.debug(f'read_temperature called for {args.sensor_id}')
        # If you need to
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

    def read_temperature(self, sensor_id: int) -> float:
        read_temp = Packet(READ_TEMPERATURE)
        packer = Packer(read_temp)
        packer.pack_u8(sensor_id)
        err, rsp = self.bus.send_command_get_response(read_temp)
       if err != ErrorCode.NONE:
            return (err, None)
        if rsp is None:
            return (ErrorCode.TIMEOUT, None)
        unpacker = Unpacker(rsp.get_data())
        err = unpacker.unpack_u8()
        temp = unpacket.unpack_u32()
        if err != ErrorCode.NONE:
            self.print(f'Error: {error_str(err)} reading from {filename}')
            return (err, None)
        return (ErrorCode.NONE, temp)
```
