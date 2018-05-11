# PCE-174 light meter protocol description

The light meter uses a binary protocol over the serial connection. Therefore,
talking to it manually through a terminal program is not fun.

The protocol documentation and implementation started from a chinglish piece of
documentation that I got my hands on. As it turns out, the documentation is
sketchy and partially incorrect, so quite a bit of reverse engineering went
into this, too.

I'd provide the original documentation here but don't feel like getting sued for
copyright violations. So if you want it ask nicely and PCE or Extech may send
it to you, too.

*Caution:* This is still work in process and I am updating this document and
the script as I learn. So don't complain if it damages you car, explodes your
house or harms a kitten.


## Sending commands

All commands are preceded by sending the two magic bytes:

    0x87 0x83

After that, send a single code byte to run the desired command.  For the most
part, the commands directly correspond to key presses on the instrument (see
manual for details):
                            
Code | Command   |  Key               | Description
-----|-----------|--------------------|------------------------------------
0xfe | units     |  UNITS key         | Toggle units (lux/fc)
0x7f | range     |  RANGE/APO         | Toggle measurement ranges
0xfd | light     |  LIGHT/LOAD key    | Toggle backlight
0xf7 | peak      |  PEAK/LEFT         | Toggle peak min/max mode
0xdf | rel       |  REL/RIGHT         | Toggle rel mode
0xef | hold      |  HOLD/DOWN         | Toggle hold mode
0xbf | minmax    |  MAX/MIN/UP        | Toggle min/max/continuous mode
0xfb | save      |  REC/SETUP         | Save reading to memory
0xde | lighthold |  LIGHT/LOAD (hold) | Toggle view mode for saved data
0xdc | logger    |  REC/SETUP (hold)  | Start/Stop data logging
0xf3 | off       |  POWER             | Power off
0xdb | relhold   |  REL/RIGHT (hold)  | Switch to next display mode 
0xda | peakhold  |  PEAK/LEFT (hold)  | Switch to previous display mode


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
interpreted as two separate 4 bit nibbles which encode decimal digits (0-9). 


### Manually stored data

Command: get-stored-data (0x12)

Magic number: 0xbb88 (2 bytes)

The instrument has 99 storage register so we expect 99 data records of 13
bytes, each.

Total blob length = 99x13 + 2 = 1289bytes.

However, the instrument normally returns quite a few extra bytes.  The extra
bytes are all 0x00.

Record format:

Pos | Bytes |  Content  | Type  | Comment
----|-------|-----------|-------|----------------------
0   | 1     |  0x00     | –     | reserved
1   | 1     |  year     | BCD   | date: year, 2 digits
2   | 1     |  weekday  | BCD   | date: weekday [1,7]
3   | 1     |  month    | BCD   | date: month
4   | 1     |  day      | BCD   | date: day
5   | 1     |  hour     | BCD   | time: hour
6   | 1     |  minute   | BCD   | time: minute
7   | 1     |  second   | BCD   | time: second
8   | 1     |  pos      | Uchar | storage position [1,99]
9   | 1     |  datH     | Uchar | value: higher 2 digits
10  | 1     |  datL     | Uchar | value: lower 2 digits
11  | 1     |  stat0    | bin   | Status byte 0        
12  | 1     |  stat1    | bin   | Status byte 1


The data value uses a variety of BCD on byte level. datH and datL are not BCD
encoded, themselves.

    value = Stat0_sign * (100 * datH + datL) * Flevel


with:

Range | Flevel
------|--------
400   | 0.1
4k    | 1.0
40k   | 10
400k  | 100

and Stat0_sign is the sign from the Stat0 byte.

The instrument does return all storage positions - even the ones that are
unused.  Those have a value of 0x00 for the pos field and are ignored by this
program.


### Timing data

Command: get-timing (0x11)

Magic number: 0xaadd

XXX data records of 16 bytes, each.

Record format:

Pos | Bytes | Content  | Type  | Comment
----|-------|----------|-------|----------------------
0   | 1     | 0x00     | –     | reserved
1   | 1     | year     | BCD   | date: year, 2 digits
2   | 1     | weekday  | BCD   | date: weekday [1, 7]
3   | 1     | month    | BCD   | date: month
4   | 1     | day      | BCD   | date: day
5   | 1     | hour     | BCD   | time: hours
6   | 1     | minute   | BCD   | time: minutes
7   | 1     | second   | BCD   | time: seconds
8   | 2     | value    | ?     | Measured value real?
10  | 2     | value    | ?     | Measured value data?
12  | 1     | stat0    | bin   | Status byte 0        
13  | 1     | stat1    | bin   | Status byte 1
14  | 1     | mem no   |       | ?
15  | 1     | read no  |       | ?



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
0   | 1     |  group    | BCD   | 
1   | 1     |  sampling | BCD   | sampling interval [s] 
2   | 1     |  0x00     | –     | reserved
3   | 1     |  year     | BCD   | date: year 
4   | 1     |  weekday  | BCD   | date: weekday [1,7]
5   | 1     |  month    | BCD   | date: month
6   | 1     |  day      | BCD   | date: day
7   | 1     |  hour     | BCD   | time: hour
8   | 1     |  minute   | BCD   | time: minute
9   | 1     |  second   | BCD   | time: second
10  | 3     |  Data1    | data  | 1. data record
13  | 3     |  Data2    | data  | 2. data record
16  | 3     |  ...      | data  | ...


Data record format:

Pos | Bytes |  Content  | Type  | Comment
----|-------|-----------|-------|----------------------
0   | 1     |  datH     | Uchar | value: higher 2 digits
1   | 1     |  datL     | Uchar | value: lower 2 digits
2   | 1     |  Stat0    | bin   | Stat0 byte

See above (Manually stored data) for interpretation of datH and datL.


## Status bytes

Some data records contain status bytes that indicate the settings
associated with a measurement as bit fields.


### Stat0 

Bits  | Meaning | Values
------|---------|----------------------------------------------------------
7     | APO     | 0: on, 1: off
6     | Hold    | 0: cont, 1: hold
5,4,3 | Mode    | 000:normal, 010:Pmin, 011:Pmax, 100:max, 101:min, 110:rel
2     | units   | 0:lux, 1:fc
0,1   | range   | 00:level3, 01:level2, 10:level3 ,11:level0


range level | lux  | fc
------------|------|------
level0      | 400k |  40k 
level1      |  400 |   40 
level2      |   4k |  400
level3      |  40k |   4k



### Stat1 

This status byte indicates the display mode the instrument was in.

Bits  | Meaning       | Values
------|---------------|--------------------------------------------
7,6   | reserved      |
5     | power         | 0:ok, 1:low
4     | sign          | 0:+, 1:-
3,2   | displaymode   | 00:time, 01:day, 10:sampling-interval, 11:year
1,0   | memload       | 01:MEM, 10:LOAD

The sign must be multiplied with value, as the value data is always unsigned.

