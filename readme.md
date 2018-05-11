# PCE-174 light meter communication

This script implements the serial communication protocol used by the PCE-174
logging light meter.

The PCE-174 appears to be identical to the Extech HD450 light meter but as I
don't own the latter I have no way to test this.  The user manual for the
Extech version of the instrument is quite a bit better than the PCE version, so
try and find it online...

See `protocol.md` for a detailed description of the communication protocol.


## Status

Currently, the script can send control commands and read both live-data and the
storage of manually aved data from the instrument.

Reading timing data and logger memory does not work, yet.

Known issues:

* I am not quite sure what `memload` from the `Stat0` byte does. Once I find
  out I may change the name so reflect its meaning. I'll leave that to a later
  release.
* Reading logger data is not implemented, yet.
* I have tested the features that are implemented, but not extensively.
  Feedback/bug reports are welcome.


## Compatibility

The program was developed under Linux but it *should* work under Windows and
MacOS as well.  However this is untested. Please let me know if you have tried
this and I'll at least update this statement.

## Connecting to a computer

The light meter has a mini USB port. Upon connection to the computer the
instrument identifies as a CP2102 USB to UART bridge (device ID `10c4:ea60`). 

On my Debian Linux system, it is recognized out of the box; under Windows you
may need to install the respective driver (from the web or the Windows
software CD that comes with the instrument). Mac anyone?

Serial communication parameters are `9600bps8N1`. Or more verbosely:

parameter | value
----------|---------
baudrate  | 9600
byte size | 8
parity    | None
stop bits | 1
timeout   | None
xon/xoff  | False
rts/cts   | False


## Dependencies

You need Python 3 for this to work.

The program uses the `construct` library for parsing binary data which has
undergone major redesign during the switch to v2.8 that lead to loss of
backwards compatibility. Accordingly, versions of `construct` <2.8 will not
work!  Development and testing was carried out with v2.9.

You can find the construct library and documentation here:

https://github.com/construct/construct

https://construct.readthedocs.io/en/latest/

If it is not provided by your distribution just install a local version:

    pip install construct


## Usage

To communicate with the light meter connect through USB and run the command
like this:

    usage: pce174 [-h] [-l] [-i INTERFACE] [-b BAUD] [-f {csv,raw,hex}] [command]

    Talk to a PCE-174 lightmeter/logger

    positional arguments:
      command           command to send to instrument

    optional arguments:
      -h, --help        show this help message and exit
      -l, --list        List all available commands
      -i INTERFACE      interface to connect to (/dev/ttyUSB0)
      -b BAUD           baudrate (9600)
      -t TIMEOUT        serial communication timeout [s] (3)
      -f {csv,raw,hex}  return data in the specified format (csv)

Typically you can stick to the defaults, maybe with the exception of the
interface specification (in case `/dev/ttyUSB0` is not what you need, certainly
under Windows). In my hands, the default TIMEOUT is enough for reading saved
data.  For live data 0.3s work for me. If timeout is too short, you will get
truncated data.

The following list describes all commands that are available as of now. The
command names were chosen to reflect what they do. Most of them correspond to
key presses on the instrument. See *Button* entry for this information.

    Available commands:

      units
          Toggle units between lux and fc
          Button: UNITS

      light
          Toggle backlight
          Button: Light/LOAD

      range
          Cycle through measurement ranges
          Button: RANGE/APO

      save
          Save reading to memory
          Button: REC/Setup

      peak
          Toggle peak value display
          Button: PEAK/LEFT

      rel
          Toggle realtive reading
          Button: REL/RIGHT

      minmax
          Toggle Min/Max/current value display 
          Button: MAX/MIN/UP

      hold
          Toggle hold
          Button: HOLD/DOWN

      off
          Turn off the instrument
          Button: POWER

      logging
          Start/stop data logging
          Button: REC-hold

      prevview
          Switch to previous display view mode
          Button: PEAK-hold

      nextview
          Switch to next display view mode
          Button: REL-hold

      viewsaved
          Toggle view mode for saved data
          Button: LIGHT/LOAD-hold

      get-live-data
          Read live data.
          Button: None
          Returns data in the specified format (-f)

      get-saved-data
          Read manually saved data
          Button: None
          Returns data in the specified format (-f)


## get-live-data

This command reads live data from the instrument. I.e. the current readings.
This can be used for single readings or automated logging from a computer
without using the logging feature of the instrument.  By default, the command
returns comma separated data (CSV) to `STDOUT`.  Example:

    date, time, value, relvalue, unit, range, mode, hold, APO, power, dispmode, memload, mem_no, read_no
    2007-08-15, 23:49:58, 21.1, 21.1, lux, 400, normal, cont, on, ok, time, mem, 27, 12

The first row contains table headers with the following meaning:

Column    | Description
----------|-----------------------------------------------
date      | Date in ISO-8601 format (YYYY-MM-DD)
time      | Time (HH:MM:SS)
value     | Numerical value of reading
rawvalue  | raw numerical value 
unit      | Unit of measurement (lux/fc)
range     | Measurement range used (40, 400, ... 4000k)
mode      | normal/Pmin/Pmax/min/max/rel 
hold      | Was hold active? (hold/cont)
APO       | Auto-power-off (on/off)
power     | Power status (ok/low)
dispmode  | Active display mode (time/day/sampling/year)
memload   | No idea what this is (0/1/2). Name may change in the future.
mem_no    | Number of manually saved records in memory. (See get-saved-data)
read_no   | ?

In normal mode, `value` and `rawvalue` are identical. In *rel* mode however,
`rawvalue` contains the absolute reading (that would be measured with out *rel*
mode) and `value` is the relative reading as displayed on the screen.

In raw mode (`-f raw`), a binary blob is written to `STDOUT`. This may be useful
for debugging or if you want to deal with the data yourself.

Hex mode (`-f hex`) is similar to raw mode but encodes the raw blob in
hexadecimal.  Again – useful for debugging.

The script ignores the `weekday` field in the data, because it has a few
issues: The weekday is set and returned as a number (1-7) and manually set –
i.e. the instrument does not try to ensure that the weekday entry matches the
date. In order to avoid confusion, I decided to ignore the weekday. If you need
the weekday, better compute it from the date.


## get-saved-data

This command reads a table of manually saved data from the instrument.
By default, the command returns comma separated data (CSV) to `STDOUT`.
Example:

    pos, date, time, value, unit, range, mode, hold, APO, power, dispmode, memload
    1, 2007-08-15, 20:11:34, 20.1, lux, 400, normal, cont, on, ok, time, 1
    2, 2007-08-15, 20:11:37, 4.0, lux, 4k, normal, cont, on, ok, time, 1
    3, 2007-08-15, 20:11:40, 0, lux, 40k, normal, cont, on, ok, time, 1
    4, 2007-08-15, 20:11:43, 0, lux, 400k, normal, cont, on, ok, time, 1

The first row contains table headers with the following meaning:

Column    | Description
----------|-----------------------------------------------
pos       | Number of the storage position
date      | Date in ISO-8601 format (YYYY-MM-DD)
time      | Time (HH:MM:SS)
value     | Numerical value
unit      | Unit of measurement (lux/fc)
range     | Measurement range used (40, 400, ... 4000k)
mode      | normal/Pmin/Pmax/min/max/rel 
hold      | Was hold active? (hold/cont)
APO       | Auto-power-off (on/off)
power     | Power status (ok/low)
dispmode  | Active display mode (time/day/sampling/year)
memload   | No idea what this is (0/1/2). Name may change in the future.

See get-live-data for details oin other formats and weekday handling.


# Some useful things from the manual

Press `REC + UNITS` to enter setup.

Peak min/max mode is able to detect short high/low peaks with a 10ms
resolution.  Normal min/max mode is much slower than that.


## Manual value storage

Press `REC` to store current value in the next free position.

Press `REC + LOAD` to clear the storage.

Press & hold `LOAD` to view stored values.


## Data logger 

To start/stop logging press & hold `REC`.

To clear logger memory, press `REC` + Power while the meter is off.

