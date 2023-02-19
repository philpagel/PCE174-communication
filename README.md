# PCE-174 light meter communication

This script implements the serial communication protocol used by the PCE-174
logging light meter.

The
[PCE-174](https://www.pce-instruments.com/english/measuring-instruments/test-meters/lux-meter-pce-instruments-lux-meter-pce-174-det_60937.htm)
appears to be identical to/compatible with the [Extech
HD450](https://www.flir.com/products/HD450/) light meter. The user manual
for the Extech version of the instrument is quite a bit better than the PCE
version, so try and find it online...

Update 2023-02-19: The PCE-174 has been delisted by the manufacturer, that is why the link above no longer works. However, it is still available at some retailers.

The meter features 99 registers of manual storage memory plus stand alone
logging capabilities. Data can be retrieved via a USB interface.

See [`protocol.md`](protocol.md) for a detailed description of the
communication protocol as far as I could figure it out.

# Usage in a nutshell

Check instrument settings

    > pce174.py get status
    date:       2022-02-14
    time:       15:55:40
    unit:       lux
    range:      400
    mode:       normal
    apo:        off
    power:      ok
    view:       time
    memstat:    None
    read_no:    1

Get current reading from the meter

    > pce174.py read live
    date,weekday,time,value,rawvalue,unit,range,mode,hold,apo,power,view,memstat,mem_no,read_no
    2019-03-10,7,17:18:32,14.600000000000001,14.600000000000001,lux,400,normal,cont,off,ok,sampling,None,6,1

Start live logging

    > pce174.py log
    date,weekday,time,value,rawvalue,unit,range,mode,hold,apo,power,view,memstat,mem_no,read_no
    2019-03-10,7,17:18:06,15.200000000000001,15.200000000000001,lux,400,rel,cont,off,ok,sampling,None,6,1
    2019-03-10,7,17:18:07,18.3,18.3,lux,400,rel,cont,off,ok,sampling,None,6,1
    2019-03-10,7,17:18:08,18.5,18.5,lux,400,rel,cont,off,ok,sampling,None,6,1
    2019-03-10,7,17:18:10,18.5,18.5,lux,400,rel,cont,off,ok,sampling,None,6,1
    [...]

Read manually stored data

    > pce174.py read saved
    pos,date,weekday,time,value,unit,range,mode,hold,apo,power,view,memstat
    1,2019-03-04,1,15:00:57,0.0,lux,4k,max,cont,off,ok,time,mem
    2,2019-03-04,1,15:56:58,0.0,lux,400,normal,cont,off,ok,time,mem
    [...]

Read data from stand-alone logging session

    > pce174.py read logger
    groupno,id,date,weekday,time,value,unit,range,mode,hold,apo
    1,0,2019-03-10,7,17:22:00,8.700000000000001,lux,400,normal,cont,off
    1,1,2019-03-10,7,17:22:02,8.4,lux,400,normal,cont,off
    [...]


# Status

Compared to v0.6, the command structure has changed! Commands are no longer
compatible with older releases. I believe it's much cleaner now, but that's
*my* opinion.

The script can send commands to control the instrument and request data from it:

* Live data: the current reading
* Saved data: the 99 registers for manually saved values
* Logging data: entire logging sessions stored in instrument memory
* Also, tethered logging is supported. I.e. the program keeps requesting
  live-data from the instrument.

All functionality that can be derived from the manufacturer protocol
documentation has been implemented. It is possible, however, that there are
undocumented functions that I haven't found.

I have tested all commands and they seem to do what I intended. However, I did
not systematically test invalid input. I also didn't implement any error
handling so you will be presented with Python's error traceback when something
goes wrong.

Feedback and bug reports are welcome.


## Known issues

Software issues

* Mysteriously, the `up` and `down` commands do not seem to work in setup mode.
  This implicates, that you cannot `set` `date`, `time` or `sampling`
* The values for `apo` are often in disagreement with the apo icon on the display.
  I have no idea what is going on, here. Any hints are welcome. I also found
  command codes that toggle the apo icon (see protocol.md) but I do not trust
  that they actually change apo mode. Therefore, the code for the `set apo {on|off}`
  command is currently commented out.
* Timing in tethered logging (`log`) is not accurate – in fact, all I did was
  to `sleep` for the number of seconds specified in `-I` between samples.  The
  timestamps, however are correct – it's just that the intervals are not
  necessarily precise. I think that's good enough in most situations.
* The instrument encodes many things in BCD. Some BCD values cannot be
  represented exactly in binary representation. E.g. 110.3 turns into
  110.30000000000001.

Firmware/instrument issues

* In standalone logging mode, the instrument does not honor `rel` mode but
  rather records absolute values. This is kind of inconsistent as the `rel`
  flag *is* recorded. However, tethered logging carried out by this program
  does treat `rel` mode as expected – so don't confuse the two.
* Sometimes the instrument stores invalid data like seconds >59. This causes
  data processing to fail. You can still use `raw`, `hex` or `construct` format
  but `repr` and `csv` do not work in those cases...  This is a bug in the
  instruments firmware – there is nothing I can do about it.
* The `weekday` recorded by the instrument does not necessarily match the
  recorded date: `weekday` is a number between 1 and 7 and can be set manually
  in setup. If you need the true weekday I recommend computing it from `date`.


## Credits

Github user *FRISAK* tested this with an Extech HD450 and also contributed some
changes to code and documentation.

# Compatibility

This program has been successfully tested with both a PCE-174 and Extech HD450
light meter under Linux.

The program was developed under Linux but it *should* work under Windows and
MacOS as well.  However, this is untested. Please let me know if you have tried
this and I'll at least update this statement.


# Connecting to a computer

The light meter has a mini USB port. Upon connection to the computer the
instrument identifies as a CP2102 USB to UART bridge (device ID `10c4:ea60`). 

On my Debian Linux system, it is recognized out of the box; under Windows you
may need to install the respective driver (from the web or the Windows
software CD that comes with the instrument). Mac anyone?

Serial communication parameters are `9600bps8N1`.

On Linux, you may need to configure your user account to have access to
/dev/ttyUSB0 (or similar). Alternatively you can run using `sudo`.


# Dependencies

You need Python 3 for this to work.

The program uses the `construct` library for parsing binary data which has
undergone major redesign during the switch to v2.8 that lead to loss of
backwards compatibility. Accordingly, versions of `construct` <2.8 will not
work!  Development and testing was carried out with v2.9.

Finally, you need `pyserial`. 

You can install all dependencies like

    pip install -r requirements.txt


# Usage

To communicate with the light meter connect through USB and run the command
like this:

    usage: pce174.py [-h] [-p PORT] [-f {csv,repr,construct,raw,hex}]
                     [-i SAMPLINGINT] [-n SAMPLENO] [-F FILE] [-s SEP]
                     [command] [args [args ...]]

    Talk to a PCE-174 lightmeter/logger

    positional arguments:
      command               command to send to instrument
      args                  arguments to command

    optional arguments:
      -h, --help            show this help message and exit
      -p PORT               port to connect to (default:/dev/ttyUSB0)
      -f {csv,repr,construct,raw,hex}
                            specify output format for read commands (default:csv)
      -i SAMPLINGINT, --samplingint SAMPLINGINT
                            set sampling interval for tethered logging [s]
                            (default:1).
      -n SAMPLENO, --sampleno SAMPLENO
                            set number of samples for tethered logging [s]
                            (default: -1).
      -F FILE, --file FILE  parse previously saved raw data instead of reading
                            from the instrument
      -s SEP, --sep SEP     separator for csv (default:',')


## Command summary

    Simulating button presses on the instrument:

        press {units|light|load|range|apo|rec|setup|peak|rel|max|min|hold|off|up|down|left|right}
        press {REC|PEAK|REL|LOAD}

    Button identifiers are case sensitive: 
        lower case: short press
        upper case: hold/long press

    Getting status/mode information:

        get status
        get {date|weekday|time|unit|range|mode|apo|power|view|memstat|read_no}

    Setting modes:

        set mode {normal|rel|min|max|pmin|pmax}
        set range {400|4k|40k|400k}      # for lux
        set range {40|400|4k|40k}        # for fc
        set unit {lux|fc}
        set apo {on|off}
        set view {time|day|year|sampling}

    Valid `range` values depend on the current value of `unit` and will change
    magically, when the unit is changed. I.e. always set `unit` before `range`.

    Enter/exit setup mode
        
        setup

    Reading data from the instrument:

        read {live|saved|logger}

    Live logging - i.e. repeatedly reading live data:

        log

Below, all commands that are available as of now are described.

## Simulate button presses

For convenience, some key press commands are redundant in that they refer to
the same button by different names (as printed on the button).  You can generate
button press events over usb using the `press` command:
    
    > pce174.py press rel

Essentially, all buttons of the instrument are supported: `units`, `light`,
`load`, `range`, `apo`, `rec`, `setup`, `peak`, `rel`, `max`, `min`, `hold`,
`off`, `up`, `down`, `left`, `right`.

Some buttons have special functions when pressed long (hold). These events can
be triggered by using the upper case version of the buttons: `REC`, `PEAK`,
`REL`, `LOAD`

See instrument manual for what these buttons do.

## Getting status information

In order to get the value of instrument parameters use the `get` command. The
following parameters are supported: `date`, `weekday`, `time`, `unit`, `range`,
`mode`, `apo`, `power`, `view`, `memstat`, `read_no`. E.g.:

    > pce174.py get unit
    lux

In addition, you can request the `status` which shows all of the above in human
readable form:

    > pce174.py get status
    date:       2019-03-10
    time:       15:55:40
    unit:       lux
    range:      400
    mode:       normal
    apo:        off
    power:      ok
    view:       time
    memstat:    None
    read_no:    1

All of the above is also included in the data returned by `read live` but if
all you want is checking status, this command is more convenient.


## Setting parameters

You can set parameters like `rel` or `peak` by pressing the respective buttons
on the instrument and by emulating button presses as described above but this is
suboptimal in a scripted environment, because you need to know the current
state and then press the right buttons the correct number of times. To ease the
process of setting things to the desired value the program can do this for you
and figure out the details by itself.

To set unit and range use the following commands:

    set unit {lux|fc}
    set range {400|4k|40k|400k}      # valid ranges for lux
    set range {40|400|4k|40k}        # valid ranges for fc

As the valid arguments to `range` depend on `unit` it is wise to set `unit` first.
In addition, you can set the measurement mode with

    set mode {normal|rel|min|max|pmin|pmax}

To set the desired view mode (what you see on the instrument display) use:

    set view {time|day|year|sampling}

In theory, you can turn `apo` on and off with

    set apo {on|off}

However, this does not work, and I am confused about the apo state in general
so I have commented out this part of the code, for now.


## Reading data from the instrument

The program supports all three different types of data stored in the
instrument:

1. Live data (`read live`) – i.e. the current reading
2. Saved data (`read saved`) – i.e. the content of the 99 storage registers
   that one can manually store readings in
3. Logger data (`read logger`) – i.e. all stand-alone logging sessions

In addition, you can perform tethered logging – i.e. the program polls live
data repeatedly (`log`).

### read live

This command reads live data from the instrument. I.e. the current readings.
By default, the command returns comma separated data (CSV) to `STDOUT`.
Example:

    > pce174.py read live
    date,weekday,time,value,rawvalue,unit,range,mode,hold,apo,power,view,memstat,mem_no,read_no
    2019-03-10,7,17:18:32,14.600000000000001,14.600000000000001,lux,400,normal,cont,off,ok,sampling,None,6,1

The first row contains column headers with the following meaning:

Column    | Description
----------|-----------------------------------------------------
date      | Date in ISO-8601 format (YYYY-MM-DD)
weekday   | int (1-7) caution: does not necessarily match date
time      | Time (HH:MM:SS)
value     | Numerical value of reading
rawvalue  | raw numerical value 
unit      | Unit of measurement (lux/fc)
range     | Measurement range used (40, 400, ... 4000k)
mode      | normal/Pmin/Pmax/min/max/rel 
hold      | hold or continuous measurement? (hold/cont)
apo       | Auto-power-off (on/off)
power     | Power status (ok/low)
dispmode  | Active display mode (time/day/sampling/year)
memstat   | storing/viewing of data (None/store/recall)
mem_no    | Number of manually saved records in memory. (See `read saved`)
read_no   | Manual storage cursor position (in the 99 storage registers)

In normal mode, `value` and `rawvalue` are identical. In `rel` mode however,
`rawvalue` contains the absolute reading (that would be measured without `rel`
mode) and `value` is the relative reading as displayed on the screen.

The binary data from the instrument includes a numeric `weekday` field in the
data which has a few issues: `weekday` is manually set – i.e. the instrument
does not try to ensure that the weekday entry matches the date. If you need the 
weekday, better compute it from the date.


### log

This command calls `read live` repeatedly to do tethered live logging. By
default it will log every second until interrupted. You can set the logging
interval with the `-i` / `--samplingint` option and limit the number of readings with `-n`.
Negative values of `-n` / `--sampleno` mean that the program will keep logging
until interrupted.

    > pce174.py -i 1 -n 4 log
    date,weekday,time,value,rawvalue,unit,range,mode,hold,apo,power,view,memstat,mem_no,read_no
    2019-03-10,7,17:18:06,15.200000000000001,15.200000000000001,lux,400,rel,cont,off,ok,sampling,None,6,1
    2019-03-10,7,17:18:07,18.3,18.3,lux,400,rel,cont,off,ok,sampling,None,6,1
    2019-03-10,7,17:18:08,18.5,18.5,lux,400,rel,cont,off,ok,sampling,None,6,1
    2019-03-10,7,17:18:10,18.5,18.5,lux,400,rel,cont,off,ok,sampling,None,6,1

As for `read live`, the first row contains the column headers in csv
format. All other formats are simply written to `STDOUT` without any record
separators.


### read saved

This command reads a table of manually saved data from the instrument.
By default, the command returns comma separated data (CSV) to `STDOUT`.
Example:

    > pce174.py read saved
    pos,date,weekday,time,value,unit,range,mode,hold,apo,power,view,memstat
    1,2019-03-04,1,15:00:57,0.0,lux,4k,max,cont,off,ok,time,mem
    2,2019-03-04,1,15:56:58,0.0,lux,400,normal,cont,off,ok,time,mem
    3,2019-03-04,1,15:56:59,0.0,lux,400,normal,cont,off,ok,time,mem
    4,2019-03-10,7,13:45:39,0.0,lux,400,normal,cont,off,ok,time,mem
    5,2019-03-10,7,13:45:42,0.0,lux,400,normal,cont,off,ok,time,mem
    6,2019-03-10,7,13:45:46,0.0,lux,400,normal,cont,off,ok,time,mem

The first row contains column headers with the following meaning:

Column    | Description
----------|----------------------------------------------------
pos       | Number of the storage position
date      | Date in ISO-8601 format (YYYY-MM-DD)
weekday   | int (1-7) caution: does not necessarily match date
time      | Time (HH:MM:SS)
value     | Numerical value
unit      | Unit of measurement (lux/fc)
range     | Measurement range used (40, 400, ... 400k)
mode      | normal/Pmin/Pmax/min/max/rel 
hold      | Was hold active? (hold/cont)
apo       | Auto-power-off (on/off)
power     | Power status (ok/low)
dispmode  | Active display mode (time/day/sampling/year)
memstat   | storing/viewing of data (None/store/recall)

See `read live` for details on other formats and weekday handling.


### read logger

This command reads logger data from the instrument.
By default, the command returns comma separated data (CSV) to `STDOUT`.
Example:

    > pce174.py read logger
    groupno,id,date,weekday,time,value,unit,range,mode,hold,apo
    1,0,2019-03-10,7,17:22:00,8.700000000000001,lux,400,normal,cont,off
    1,1,2019-03-10,7,17:22:02,8.4,lux,400,normal,cont,off
    1,2,2019-03-10,7,17:22:04,8.4,lux,400,normal,cont,off
    1,3,2019-03-10,7,17:22:06,8.200000000000001,lux,400,normal,cont,off
    2,0,2019-03-10,7,17:22:35,9.0,lux,400,normal,cont,off
    2,1,2019-03-10,7,17:22:37,8.9,lux,400,normal,cont,off
    2,2,2019-03-10,7,17:22:39,8.700000000000001,lux,400,normal,cont,off

The first row contains column headers with the following meaning:

Column    | Description
----------|-----------------------------------------------------
groupno   | numerical id of the logging group [1, 2, ...]
id        | measurement number within the group [0, 1, ...]
date      | YYYY-MM-DD
weekday   | int (1-7) caution: does not necessarily match date
time      | HH:MM:SS
value     | measurement
unit      | Unit of measurement (lux/fc)
range     | Measurement range used (40, 400, ... 400k)
mode      | normal/Pmin/Pmax/min/max/rel 
hold      | Was hold active? (hold/cont)
apo       | Auto-power-off (on/off)

See `read live` for details on other formats and weekday handling.


## Data formats

Through the -f option you can choose from several output formats for the
`read XXX` functions.

### csv

This is the most useful format for most purposes, as it can easily be imported
into other software.  The first row is the header declaring the column names.
The field separator is a comma (`','`), by default and can be chosen with the
`-s` option. Lines are separated by a single newline character (`\n`).


### repr

This format is the Python representation of the data. It is mostly useful for
debugging and possibly for use in other python programs although in the latter
case it's probably better to import the script as a module and use the data
returned from the `read_data` function. See below for details.


### construct

This is the container representation of the construct library. Probably only
useful for debugging.


### raw

This format simply writes the binary blob to `STDOUT` as it is received from
the instrument.


### hex

Similar to raw but transcribed to hex representation.


## Saving raw data and parsing it later

If you write raw data blobs into a file you can later parse it:

    pce174.py read saved -f raw > foo.dat
    pce174.py read saved -F foo.dat
    pce174.py read saved -F foo.dat -f repr

This may be useful, if you are not sure if you want the data in different
formats, later or for debugging.  Also, it may help for bug reports in order to
reproduce the problem based on actual raw data.

**Caution:** this only works with raw data! If you forget to specify `-f raw`
you will not be able to read it later.

As the different data types have incompatible formats you must use the correct
argument to `read`.


# Entering setup

To enter or exit setup mode use
    
    pce174.py setup

This is not all that useful as I haven't figured out how to make the `up` and
`down` button press commands work in this mode. So you have to do the actual
setup using the buttons on the instrument.


# Usage as a module

You can import this script as a module and call its functions directly. This
may be handy if you want to write your own software that needs access to the
instrument.

Example session:

    >>> import pce174 as p
    >>> p.press_button("/dev/ttyUSB0", "light")
    >>> dat = p.read_data("/dev/ttyUSB0", "live")
    >>> dat
    {'weekday': 1, 'date': '2019-03-11', 'value': 37.6, 'rawvalue': 37.6, 'memstat': None, 'read_no': 1, 'time': '21:43:50', 'hold': 'cont', 'mem_no': 11, 'unit': 'lux', 'view': 'time', 'range': '400', 'mode': 'normal', 'power': 'ok', 'apo': 'off'}
    >>> p.getvar("/dev/ttyUSB0", "unit")
    'lux'
    >>> p.setvar("/dev/ttyUSB0", "unit", "fc")
    >>> p.read_data("/dev/ttyUSB0", "live", outformat="csv")
    '2019-03-11,1,21:47:38,3.5,3.5,fc,40,normal,cont,off,ok,time,None,11,1'
    >>> dat2 = p.read_data("/dev/ttyUSB0", "saved")
    >>> dat3 = p.read_data("/dev/ttyUSB0", "logger")

See pydoc and/or source code for function documentation.


# Some useful things from the manual

Press `REC + UNITS` to enter setup.

Pulse min/max mode is able to detect short high/low peaks with a 10ms
resolution.  Normal min/max mode is much slower than that.


## Manual value storage

Press `REC` to store current value in the next free position.

Long-Press `REC + LOAD` to clear the storage.

Press & hold `LOAD` to view stored values.


## Data logger 

To start/stop logging press & hold `REC`.

To clear logger memory, press `REC` + Power while the meter is off.

