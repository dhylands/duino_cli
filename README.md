# duino_cli
Python CLI for interfacing with Arduino projects

This is a simple CLI for interacting with software running on an Arduino (or similar) microcontroller.

# Installation

You can install duino_cli using the command:
```bash
pip install duino_cli
```
The CLI uses a plugin mechanism for adding commands and the default commands are fairly limited, so you'll probably also want to install
`duino_littlefs` which allows interacting with the LittleFS filesystem
found on modern ESP32's running Arduino.
```bash
pip install duino-littlefs
```

# Usage

You need to specify the serial port when launching the CLI. You can optionally specify the baud rate (which defaults to 115200).

```
$ cli --help
usage: duino_cli [options] [command]

Command Line Interface for Arduino boards.

optional arguments:
  -h, --help            show this help message and exit
  -p PORT, --port PORT  Set the serial port to use (default = None)
  -b BAUD, --baud BAUD  Set the baudrate used (default = 115200)
  -l, --list            Display serial ports
  -n, --net             Connect to a duino_cli_server (localhost:8888)
  -d, --debbug          Turn on some debug
  --nocolor             Turn off colorized output

You can specify the default serial port using the CLI_PORT environment variable.
```
The `--list` option will show available USB serial ports. The output under windows will look something like:
```bash
c:\Users\dhyla>cli --list
USB Serial Device 0403:6015 with vendor 'FTDI' serial 'DN02Z2XCA' found @COM3
```
and under linux, it will look like:
```bash
$ cli --list
USB Serial Device 0403:6015 with vendor 'FTDI' serial 'DN02Z2XC' intf 'Micropython Sparkfun ESP32 Thing' found @/dev/ttyUSB0
```

Once you launch the CLI, you will be present with a CLI prompt:
```bash
$ cli --port /dev/ttyUSB0
Reading history from /home/dhylands/.cli_history
Loading Plugin littlefs ...
Loading Plugin core ...
All plugins loaded
CLI>
```

# Core Commands

Now you can enter a command. `help` will show all available commands:
```
CLI> help
Type "help <command>" to get more information on a command:
===========================================================
args      echo  format  history  info  mkdir  quit  remove  upload
download  exit  help    hls      ls    ping   read  rmdir   write
```
and `help command` will show help for a particular command.

The `read` and `write` commands are for debug only and will be removed shortly.

## echo

## help

## history

## ping

## quit or exit

```
CLI> help ping
ping

Sends a PING packet to the arduino and reports a response.
```

# LittleFS Commands

## download

## format

## info

## hls

## ls

## mkdir

## remove

## upload
