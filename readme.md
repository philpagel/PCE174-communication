# PCE-174 light meter communication

This script implements the serial communication protocol used by the PCE-174
logging light meter.

The PCE-174 appears to be identical to the Extech HD450 light meter 
but as I don't own the latter I have no way to test this.

Currently, the script can send all control commands and request data from the
instrument. However, parsing and decoding of the data received is still work in
progress and considered non-functional. I also don't fully understand all
commands, yet so they may have confusing names and/or descriptions.

## Connecting to a computer

The light meter has a mini USB port. Upon connection to the computer the
instrument identifies as a CP2102 USB to UART bridge (device ID 10c4:ea60). 

On my Debian Linux system, it is recognized out of the box; under Windows you
may need to install the respective driver (from the interweb or the Windows
software CD that comes with the instrument). Mac anyone?

Serial communication parameters are 9600bps8N1. Or more verbose:

parameter | value
----------|---------
baudrate  | 9600
byte size | 8
parity    | None
stop bits | 1
timeout   | None
xon/xoff  | False
rts/cts   | False


## Usage

To communicate with the light meter connect through USB and run the command
like this:

    usage: pce174 [-h] [-i INTERFACE] [-b BAUD] [-f {csv,raw,hex}] command

    talk to a PCE-174 lightmeter/logger

    positional arguments:
      command           command to send to instrument

    optional arguments:
      -h, --help        show this help message and exit
      -i INTERFACE      interface to connect to (/dev/ttyUSB0)
      -b BAUD           baudrate (9600)
      -f {csv,raw,hex}  return data in the specified format (csv)


Typically you can stick to the defaults, maybe with the exception of the
interface specification (in case /dev/ttyUSB0 is not what you need).



# Protocol description

The light meter uses a binary protocol over the serial connection. Therefore,
talking to it manually through a terminal program is not convenient.

*Caution:* I am still in the process of putting together a full protocol
description from  the chinglish documentation that I have. Accordingly, I am
updating this as I learn. So don't rely on this, yet. 


## Sending commands

All commands are preceded by sending the two magic bytes:

    0x87 0x83

After that, send a single code byte to run the desired command.  For the most
part, the commands directly correspond to key presses on the instrument (see
manual for details):
                            
Code | Command   |  Key               | Description
-----|-----------|--------------------|------------------------------------
0xfe | units     |  UNITS key         | Toggle units (fc/lux)
0x7f | range     |  RANGE/APO         | Toggle measurement ranges
0xfd | light     |  LIGHT/LOAD key    | Toggle backlight
0xf7 | peak      |  PEAK/LEFT         | Toggle peak min/max mode
0xdf | rel       |  REL/RIGHT         | Toggle rel mode
0xef | hold      |  HOLD/DOWN         | Toggle hold mode
0xbf | minmax    |  MAX/MIN/UP        | Toggle min/max/continuous mode
0xfb | save      |  REC/SETUP         | Save reading
0xf3 | off       |  POWER             | Power off
0xdc | logger    |  REC/SETUP (hold)  | ?
0xdb | relhold   |  REL/RIGHT (hold)  | ?
0xde | lighthold |  LIGHT/LOAD (hold) | ?
0xda | peakhold  |  PEAK/LEFT (hold)  | ?


Commands that request data from the instrument cannot be triggered by button
presses:

Code | Command           | Description
-----|-------------------|-------------------------------------------------
0x11 | get-timing        | ?
0x12 | get-stored-data   | Read manually stored data registers
0x13 | get-logger-data   | Read logger data
0x14 | get-data-protocol | ?

After receiving one of these commands, the instrument returns a binary blob
that requires decoding. The structure of these blobs is described in the next
section.


## Detailed description of received data blobs

Data blobs always start with a 2 byte magic number that indicates
the type of blob. The actual data follows immediately after that. 

Most numerical data is encoded as binary coded decimal (BCD), i.e bytes are
interpreted as two separate 4 bit nibbles which encode decimal digits (0-9),
separately. Values larger than 1 byte are stored in little-endian format.


### Timing data

Command: get-timing (0x11)

Magic number: 0xaadd

XXX data records of 16 bytes, each.

Record format:

Pos | Bytes | Content  | Type  | Comment
----|-------|----------|-------|----------------------
0   |    1  | 0x00     | –     | reserved
1   |    1  | year     | BCD   | date: year, 2 digits
2   |    1  | week     | BCD   | date: week
3   |    1  | month    | BCD   | date: month
4   |    1  | day      | BCD   | date: day
5   |    1  | hour     | BCD   | time: hours
6   |    1  | minute   | BCD   | time: minutes
7   |    1  | second   | BCD   | time: seconds
8   |    2  | value    | ?     | Measured value real?
10  |    2  | value    | ?     | Measured value data?
12  |    1  | stat0    | bin   | Status byte 0        
13  |    1  | stat1    | bin   | Status byte 1
14  |    1  | mem no   |       | ?
15  |    1  | read no  |       | ?


### Manually stored data

Command: get-stored-data (0x12)

Magic number: 0xbb88 (2 bytes)

99 data records of 13 bytes, each.

Total blob length = 99*13 + 2 = 1289bytes.

However, the instrument returns more bytes than that (1352 in my case).
The 63 extra bytes are all 0x00.

Record format:

Pos | Bytes |  Content  | Type  | Comment
----|-------|-----------|-------|----------------------
0   | 1     |  0x00     | –     | reserved
1   | 1     |  year     | BCD   | date: year, 2 digits
2   | 1     |  week     | BCD   | date: week
3   | 1     |  month    | BCD   | date: month
4   | 1     |  day      | BCD   | date: day
5   | 1     |  hour     | BCD   | time: hours
6   | 1     |  minute   | BCD   | time: minutes
7   | 1     |  second   | BCD   | time: seconds
8   | 2     |  value    | ?     | Measured value
10  | 1     |  stat0    | bin   | Status byte 0        
11  | 1     |  stat1    | bin   | Status byte 1
12  | 1     |  0x01     |       | reserved/undocumented/separator?


### Logger data

Command: get-logger-data (0x13)

Magic number: 0xaacc

XXX data records of 3 bytes, each.

Record format:

Pos |Bytes |  Content  | Type    | Comment
----|------|-----------|---------|----------------------
0   |1     |  group    | UInt8   | ?
1   |2     |  bufsize  | ULInt16 | ?



### Protocol transmission data

Command: get-stored-data (0x14)

Magic number: 0xaa56

Record format:

Pos | Bytes |  Content  | Type  | Comment
----|-------|-----------|-------|----------------------
0   | 1     |  group    | UInt8 | 
1   | 1     |  sampling | UInt8 | 
2   | 1     |  0x00     | UInt8 | reserved
3   | 1     |  year     | UInt8 | 
4   | 1     |  week     | UInt8 | docs said "Mon-day"???
5   | 1     |  month    | UInt8 | docs said "yue" which means "moon/month"
6   | 1     |  day      | UInt8 | 
7   | 1     |  hour     | UInt8 | 
8   | 1     |  minute   | UInt8 | 
9   | 1     |  second   | UInt8 | 
10  | 3     |  Data1    | data  | 1. data record
13  | 3     |  Data2    | data  | 2. data record
16  | 3     |  ...      | data  | ...


Data record format:

Pos | Bytes |  Content  | Type  | Comment
----|-------|-----------|-------|----------------------
0   | 2     |  Value    | BCD?  | Measures value
2   | 1     |  Status   | UInt8 | Stat0 byte


## Status bytes

Some data records contain two status bytes that indicate the settings
associated with a measurement as bit fields.

### Stat0 

XXX -- transcribed from docs. Untested!

Bits  | Meaning | Values
------|---------|----------------------------------------------------------
7     | APO     | 0: on, 1: off
6     | Hold    | 0: off, 1: on
5,4,3 | Mode    | 000:Normal, 010:Pmin, 011:Pmax, 100:Max, 101:Min, 110:Rel
2     | units   | 0:lux, 1:fc
0,1   | Range   | 00:range0, ... 11:range4


### Stat1 

XXX -- transcribed from docs. Untested!

Bits  | Meaning   | Values
------|-----------|--------------------------------------------
8,7,6 | reserved  |
5     | low power | 0:off, 1:on
4     | signed    | 0:false, 1:true 
3,2   |     ?     | 00:time, 01:day, 10:sampling-rate, 11:year
1,0   | ?         | 01:MEM, 10:LOAD



