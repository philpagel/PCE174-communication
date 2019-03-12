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
the script as I learn. So don't complain if it wrecks your car, explodes your
house or harms a kitten.


## Sending commands

Upon connection to the computer the instrument identifies as a CP2102 USB to
UART bridge (device ID `10c4:ea60`). 

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


All commands are preceded by sending the two magic bytes:

    0x87 0x83

After that, send a single code byte to run the desired command.  For the most
part, the commands directly correspond to key presses on the instrument (see
manual for details):
                            
Code | Key               | Description
-----|-------------------|------------------------------------
0xfe | UNITS key         | Toggle units (lux/fc)
0xfd | LIGHT/LOAD key    | Toggle backlight
0x7f | RANGE/APO         | Toggle measurement ranges
0xfb | REC/SETUP         | Save reading to memory
0xbf | MAX/MIN/UP        | Toggle min/max/continuous mode
0xf7 | PEAK/LEFT         | Toggle peak min/max mode
0xde | REL/RIGHT         | Toggle rel mode
0xef | HOLD/DOWN         | Toggle hold mode
0xdb | LIGHT/LOAD (hold) | Toggle view mode for saved data
0xdc | REC/SETUP (hold)  | Start/Stop data logging
0xda | PEAK/LEFT (hold)  | Switch to previous display mode
0xde | REL/RIGHT (hold)  | Switch to next display mode 
0xf3 | POWER             | Power off


Commands not described in manufacturer's protocol documentation but found to do
something by trial and error:

Code | Key       | Description
-----|-----------|------------------------------------
0xfa | REC+UNITS | Enter/exit setup
0xf9 | REC+RANGE | APO on
0x7b | REC+RANGE | APO on
0x7c | REC+RANGE | APO off
0xee |           | memCL shows but memory is not cleared


Commands that request data from the instrument cannot be triggered by button
presses:

Code | Description
-----|-------------------------------------------------
0x11 | Read the current measurement
0x12 | Read manually stored data registers (1-99)
0x13 | Read logger data
0x14 | Does not exist although mentioned in original docs

After receiving one of these commands, the instrument returns a binary blob
that requires decoding. The structure of these blobs is described in the next
section. The command `0x14` appears in the original documentation but seems to
do nothing. The data described for this command is actually part of the data
structure returned by `0x13` so is most likely an error in the original docs.


## Detailed description of received data blobs

Data blobs always start with a 2 byte magic number that indicates
the type of blob. The actual data follows immediately after that. 

Most numerical data is encoded as binary coded decimal (BCD), i.e bytes are
interpreted as two separate 4 bit nibbles which encode decimal digits (0-9). 

### Live data

Command: 0x11

1 data record of 18 bytes.

Record format:

Byte | Size | Content  | Type  | Comment
-----|------|----------|-------|-----------------------------------------
0    | 2    | 0xaadd   | –     | magic number
2    | 1    | 0x00     | –     | reserved
3    | 1    | year     | BCD   | date: year, 2 digits
4    | 1    | weekday  | BCD   | date: weekday [1, 7]
5    | 1    | month    | BCD   | date: month
6    | 1    | day      | BCD   | date: day
7    | 1    | hour     | BCD   | time: hours
8    | 1    | minute   | BCD   | time: minutes
9    | 1    | second   | BCD   | time: seconds
10   | 1    | valH     | Uchar | value: higher 2 digits
11   | 1    | valL     | Uchar | value: lower 2 digits
12   | 1    | rawvalH  | Uchar | raw value: higher 2 digits
13   | 1    | rawvalL  | Uchar | raw value: lower 2 digits
14   | 1    | stat0    | bin   | Status byte 0        
15   | 1    | stat1    | bin   | Status byte 1
16   | 1    | mem_no   | bin   | number of saved data records
17   | 1    | read_no  | bin   | manual storage cursor position

In normal mode, `value` and `rawvalue` are identical. In *rel* mode however,
`rawvalue` contains the absolute reading (that would be measured without *rel*
mode) and `value` is the relative reading as displayed on the screen.

`read_no` indicates where the cursor for viewing saved data is positioned. I.e.
the memory register which you will see when switching to saved data viewing
mode by pressing and holding `load`.

### Manually stored data

Command: 0x12

The instrument has 99 storage registers so we expect 99 data records of 13
bytes, each.

Total blob length = 99x13 + 2 = 1289bytes.

However, the instrument normally returns quite a few extra bytes.  The extra
bytes are all 0x00.


Byte | Size | Content  | Type  | Comment
-----|------|----------|-------|-----------------------
0    | 2    | 0xbb88   | –     | magic number
14   | 13   |          |       | data record 1
27   | 13   |          |       | data record 2
30   | 13   |          |       | data record 3
...
     | 13   |          |       | data record n (n<100)
     | x    | 0x00     |       | trailing zero bytes


Data record format:

Byte | Size |  Content  | Type  | Comment
-----|------|-----------|-------|----------------------
0    | 1    |  0x00     | –     | reserved
1    | 1    |  year     | BCD   | date: year, 2 digits
2    | 1    |  weekday  | BCD   | date: weekday [1,7]
3    | 1    |  month    | BCD   | date: month
4    | 1    |  day      | BCD   | date: day
5    | 1    |  hour     | BCD   | time: hour
6    | 1    |  minute   | BCD   | time: minute
7    | 1    |  second   | BCD   | time: second
8    | 1    |  pos      | Uchar | storage position [1,99]
9    | 1    |  valH     | Uchar | value: higher 2 digits
10   | 1    |  valL     | Uchar | value: lower 2 digits
11   | 1    |  stat0    | bin   | Status byte 0        
12   | 1    |  stat1    | bin   | Status byte 1


The data value uses a variety of BCD on byte level. valH and valL are not BCD
encoded, themselves.

    value = Stat0_sign * (100 * valH + valL) * Frange


with:

Range | Frange
------|--------
40    | 0.01
400   | 0.1
4k    | 1.0
40k   | 10
400k  | 100

and Stat0_sign is the sign from the Stat0 byte.

The instrument does return all storage positions – even the ones that are
unused.  Those have a value of 0x00 for the `pos` field and are ignored by this
program.


### Logger data

Command: 0x13

#### Header

5 bytes

Byte | Size | Content  | Type    | Comment
-----|------|----------|---------|-------------------------------
0    | 2    | 0xaacc   | –       | magic number
2    | 1    | nogroups | Uchar   | No. of logging groups
3    | 2    | bufsize  | UInt16  | Size of logging buffer [bytes]

Followed by `nogroups` logging records.


#### Logging group record

Header of 13 bytes:

Byte | Size |  Content  | Type  | Comment
-----|------|-----------|-------|------------------------
0    | 2    |  0xaa56   | –     | magic number
2    | 1    |  groupno  | BCD   | number of this group
3    | 1    |  sampling | BCD   | sampling interval [s] 
4    | 1    |  0x00     | –     | reserved
5    | 1    |  0x00     | –     | reserved
6    | 1    |  year     | BCD   | year 
7    | 1    |  weekday  | BCD   | weekday [1,7]
8    | 1    |  month    | BCD   | month
9    | 1    |  day      | BCD   | day
10   | 1    |  hour     | BCD   | hour
11   | 1    |  minute   | BCD   | minute
12   | 1    |  second   | BCD   | second

Followed by an unknown number of data-point records.  So we need to read until
we hit the next magic number for a logging group or EOF.

This is actually safe, as the magic number is larger than the largest possible 
measurement and thus cannot be encountered by chance.


#### logging data point record

Byte | Size  |  Content  | Type  | Comment
---- |-------|-----------|-------|------------------------
0    | 1     |  valH     | Uchar | value: higher 2 digits
1    | 1     |  valL     | Uchar | value: lower 2 digits
2    | 1     |  Stat0    | bin   | Stat0 byte

See above (manually stored data) for interpretation of valH and valL.
As no Stat1 byte is present, there is no `sign` value. It is unclear how
negative readings (in rel mode) should be handled.


## Status bytes

Some data records contain status bytes that indicate the settings
associated with a measurement as bit fields.


### Stat0 

Bits  | Meaning | Values
------|---------|-----------------------------------------------------------
7     | APO     | 0: on, 1: off
6     | Hold    | 0: cont, 1: hold
5,4,3 | Mode    | 000:normal, 010:Pmin, 011:Pmax, 100:max, 101:min, 110:rel
2     | units   | 0:lux, 1:fc
0,1   | range   | 00:level0, 01:level1, 10:level2 ,11:level3


range level | lux  | fc
------------|------|------
level0      | 400k |  40k 
level1      |  400 |   40 
level2      |   4k |  400
level3      |  40k |   4k



### Stat1 

This status byte indicates the display mode the instrument was in.

Bits  | Meaning   | Values
------|-----------|------------------------------------------------
7,6   | reserved  |
5     | power     | 0:ok, 1:low
4     | sign      | 0:+, 1:-
3,2   | view      | 00:time, 01:day, 10:sampling-interval, 11:year
1,0   | memstat   | 01:store, 10:recall, 11: logging, 00: None

The sign must be multiplied with value, as the value data is always unsigned.

`memstat` indicates if the instrument is in `store` or `recall` mode for saved
data.  This is the modes you can enter long-pressing the `load` button or
pressing `rec`, respectively.


