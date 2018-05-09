# PCE-174 light meter communication

This script implements the serial communication protocol used by the PCE-174
logging light meter.

The PCE-174 appears to be identical to the Extech HD450 light meter 
but as I don't own the latter I have no way to test this.

Currently, the script can send all control commands and request data from the
instrument. However, parsing and decoding of the data received is still work in
progress and considered non-functional.

## Connecting to a computer

The light meter has a mini USB port. Upon connection to the computer the
instrument identifies as a CP2102 USB to UART bridge (device ID 10c4:ea60). 

On my Debian Linux system, it is recognized out of the box; under Windows you
may need to install the respective driver (from the interweb or the Windows
software CD that comes with the instrument). Mac anyone?

Serial communication parameters:

parameter | value
----------|---------
baudrate  | 9600
bytesize  | 8
parity    | None
stopbits  | 1
timeout   | None
xonxoff   | False
rtscts    | False


## Usage

To communicate with the light meter connect through USB and run the command lie this:

    pce174 [-h] [-i INTERFACE] [-b BAUD] [-f {csv,raw,repr}] command

    positional arguments:
      command            command to send to instrument

    optional arguments:
      -h, --help         show this help message and exit
      -i INTERFACE       interface to connect to
      -b BAUD            baudrate
      -f {csv,raw,repr}  return data in the specified format

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
                            
Code | Command      |  Key               | Description
-----|--------------|--------------------|------------------------------------
0xfe | units        |  UNITS key         | Toggle units (fc/lux)
0xfd | load         |  LIGHT/LOAD key    | Toggle backlight
0xfb | save         |  REC/SETUP         | Save reading
0Xf7 | peak         |  PEAK/LEFT         | Toggle peak mode
0xdf | rel          |  REL/RIGHT         | Toggle rel mode
0xef | hold         |  HOLD/DOWN         | Toggle hold mode
0xbf | max          |  MAX/MIN/UP        | Toggle min/max/continuous mode
0Xdc | datalogger   |  REC/SETUP (hold)  | ?
0xdb | REL hold rel |  REL/RIGHT (hold)  | ?
0xde |              |  LIGHT/LOAD (hold) | ?
0xda |              |  PEAK/LEFT (hold)  | ?
0x7f | range        |  RANGE/APO         | Toggle measurement ranges
0xf3 | off          |  POWER             | Power off


Commands that request data from the instrument cannot be triggered by button
presses:


Code | Command           | Description
-----|-------------------|-------------------------------------------------
0x11 | get-timing        | ?
0x12 | get-stored-data   | Read manually stored data registers
0x13 | get-logger-data   | Read logger data
0x14 | get-data-protocol | ?


## Detailed description of received data

XXX - to be written


