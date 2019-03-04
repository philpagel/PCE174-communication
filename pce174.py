#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pce174

A tool to communicate with a PCE-174 lightmeter/logger
or compatible devices like the Extech HD450
"""

# from stdlib
import sys, argparse, binascii, warnings, datetime, time
from collections import OrderedDict
# others
import serial
from construct import * # requires construct ≥ 2.8 (tested with 2.9)
import pdb

__author__ = "Philipp Pagel"
__copyright__ = "Copyright 2018, 2019, Philipp Pagel"
__license__ = "MIT License"


def main():
    "The main function"

    args = getargs()

    # Add redundant keys to commandset for conveniance
    commandset["up"] = commandset["minmax"]
    commandset["down"] = commandset["hold"]
    commandset["left"] = commandset["peak"]
    commandset["right"] = commandset["rel"]

    if args.list:
        list_commands(commandset)
        return

    if args.command in commandset:
        if args.command=="log-live-data":
            log_live_data(args)
            return
        if len(args.file) > 0:
            if commandset[args.command]["ret"]:
                infile = open(args.file, "rb")
                blob = infile.read()
                infile.close()
            else:
                sys.exit(
                    "Cannot run command '%s' from file - no data expected."
                    % (args.command)
                )
        else:
            blob = send_command(args.interface, args.command)
        if commandset[args.command]["ret"]:  # read data
            if args.format == "raw":
                sys.stdout.buffer.write(blob)
            elif args.format == "hex":
                sys.stdout.buffer.write(binascii.hexlify(blob))
            elif args.format in ("csv", "repr", "construct"):
                print(decode_blob(blob, args.command, args.format, args.sep))
    else:
        sys.exit("Unknown command\nTry -h and/or -l for help")



def list_commands(commandset):
    """Print list of available commands
    as well as a short description
    """

    print("Available commands:\n")
    for key, value in commandset.items():
        print(" ", key)
        print(' '*5, value['desc'])
        print(' '*5, "Button:", value['key'])
        print()


def log_live_data(args):
    """Log live data (tethered logging)
    """

    if args.sampleno <0:
        args.sampleno = float('Inf')
    i = 0
    while True:
        blob = send_command(args.interface, args.command)
        if args.format == "raw":
            sys.stdout.buffer.write(blob)
        elif args.format == "hex":
            sys.stdout.buffer.write(binascii.hexlify(blob))
        elif args.format in ("csv", "repr", "construct"):
            print(decode_blob(blob, args.command, args.format, args.sep, header=i==0))
        i += 1
        if args.sampleno >0:
            if i >= args.sampleno:
                break
        time.sleep(args.samplingint)
    return


def send_command(port, command):
    """Send a known command to instrument

    port     : string indicating the serial interface to use. E.g. /dev/ttyUSB0
    command  : must be one of the valid command strings defined in commandset

    returns the binary blob that is received in response or empty byte array
    """

    return send_cmd(port, commandset[command]["cmd"], read=commandset[command]["ret"])


def send_cmd(port, cmd, read=False, timeout=0.1):
    """Send command byte to instrument

    port     : string indicating the serial port to use. E.g. /dev/ttyUSB0
    cmd      : a single byte to be sent
    read     : If True try to read data from the instrument after sending command
    timeout  : Rimeout for serial communication

    returns the binary blob that is received in response or empty byte array
    This function is provided separately for advanced use, e.g. when trying to
    reverse engineer/use undocumented functions of the instrument.
    """

    iface = serial.Serial(
        port=port, baudrate=9600, bytesize=8, parity="N", stopbits=1, timeout=timeout
    )

    hello = b"\x87\x83"  # command prefix
    msg = hello + cmd
    iface.write(msg)

    blob = b""
    if read:
        while True:
            byte = iface.read(1)
            if len(byte) > 0:
                blob += byte
            else:
                break
    iface.close()

    return blob


def bcd2int(dat):
    """Return the decimal value of a BCD encoded int

    The int can be of arbitrary length
    """

    ret = 0
    f = 1
    while dat != 0:
        val = dat & 0x0F
        if val > 9:
            warnings.warn("Pseudo-tetrade encountered in BCD conversion.")
        ret += f * val
        f *= 10
        dat = dat >> 4
    return ret


def decode_blob(blob, cmd, outformat, sep, header=True):
    """return decoded data

    Central dispatch for the different parsing, processing and csv translation steps
    """

    ret = None
    if cmd == "get-status":
        ret = parse_live_data(blob)
        ret = process_stat_data(ret)
    elif cmd in ("get-live-data", 'log-live-data'):
        ret = parse_live_data(blob)
        if outformat in ("csv", "repr"):
            ret = process_live_data(ret)
        if outformat == ("csv"):
            ret = live_data2csv(ret, sep, header=header)
    elif cmd == "get-saved-data":
        ret = parse_saved_data(blob)
        if outformat in ("csv", "repr"):
            ret = process_saved_data(ret)
        if outformat == ("csv"):
            ret = saved_data2csv(ret, sep)
    elif cmd == "get-logger-data":
        ret = parse_logger_data(blob)
        if outformat in ("csv", "repr"):
            ret = process_logger_data(ret)
        if outformat == ("csv"):
            ret = logger_data2csv(ret, sep)
    else:
        raise Exception("Unknown command.")


    return ret


def parse_live_data(blob):
    """parse live data to construct container

    Accept a binary blob of live data and parse it.
    Returns a construct container object with parsed data.
    """

    Live_data = Struct(
        "magic" / Const(b"\xaa\xdd"),
        Padding(1),
        "year" / Int8ub,
        "weekday" / Int8ub,
        "month" / Int8ub,
        "day" / Int8ub,
        "hour" / Int8ub,
        "minute" / Int8ub,
        "second" / Int8ub,
        "dat0H" / Int8ub,
        "dat0L" / Int8ub,
        "dat1H" / Int8ub,
        "dat1L" / Int8ub,
        "stat0" / Int8ub,
        "stat1" / Int8ub,
        "mem_no" / Int8ub,
        "read_no" / Int8ub,
    )

    return Live_data.parse(blob)


def process_stat_data(rec):
    """Return status information in human readable form"""

    dat = process_live_data(rec)
    ret = """Date:  {date}
Time:  {time}
Units: {unit}
Range: {range}
mode:  {mode}
APO:   {APO}
Power: {power}
Disp:  {dispmode}
Mem:   {memload}
Read:  {read_no}""".format_map(dat)

    return ret


def process_live_data(rec):
    """Return processed live data

    Accepts a construct container object and returns a dict
    representing the measurement.

    Processing comprises the assembly of common time and date formats as well
    as turning bit fields into human readable values.

    Measurment records are dicts with the following keys:

    Key       | Description
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
    """

    # bcd decoding
    for key in ["year", "weekday", "month", "day", "hour", "minute", "second"]:
        rec[key] = bcd2int(rec[key])

    stat0 = decode_stat0(rec["stat0"])
    stat1 = decode_stat1(rec["stat1"])

    # reassemble the record in a more practical format
    rec = {
        "date": "20%2.2i-%2.2i-%2.2i" % (rec["year"], rec["month"], rec["day"]),
        "time": "%2.2i:%2.2i:%2.2i" % (rec["hour"], rec["minute"], rec["second"]),
        "value": stat1["sign"] * (100 * rec["dat1H"] + rec["dat1L"]) * stat0["Frange"],
        "rawvalue": (100 * rec["dat0H"] + rec["dat0L"]) * stat0["Frange"],
        "unit": stat0["unit"],
        "range": stat0["range"],
        "mode": stat0["mode"],
        "hold": stat0["hold"],
        "APO": stat0["APO"],
        "power": stat1["power"],
        "dispmode": stat1["dispmode"],
        "memload": stat1["memload"],
        "mem_no": rec["mem_no"],
        "read_no": rec["read_no"],
    }

    return rec


def live_data2csv(dat, sep, header=True):
    """returns csv from live data dict"""

    # define columns and assemble header
    cols = (
        "date",
        "time",
        "value",
        "rawvalue",
        "unit",
        "range",
        "mode",
        "hold",
        "APO",
        "power",
        "dispmode",
        "memload",
        "mem_no",
        "read_no",
    )

    csv = []
    if header:
        csv = [sep.join(cols)]
    csv.append(sep.join(([str(dat[col]) for col in cols])))

    return "\n".join(csv)


def parse_saved_data(blob):
    """parse saved data to construct container

    Accept a binary blob of saved data and parse it.
    Returns a construct container object with parsed data.
    """

    record = Struct(
        "foo" / Int8ub,  # should be 0x00 but isn't always
        #'magic' / Const(b'\x00'),
        "year" / Int8ub,
        "week" / Int8ub,
        "month" / Int8ub,
        "day" / Int8ub,
        "hour" / Int8ub,
        "minute" / Int8ub,
        "second" / Int8ub,
        "pos" / Int8ub,
        "datH" / Int8ub,
        "datL" / Int8ub,
        "stat0" / Int8ub,
        "stat1" / Int8ub,
    )

    db = Struct("magic" / Const(b"\xbb\x88"), "data" / Array(99, record))

    return db.parse(blob)


def process_saved_data(dat):
    """Return processed saved data

    Accepts a construct container object and returns a list of dicts
    Each dict represents one saved measurement.

    Processing comprises the assembly of common time and date formats as well as
    turning bit fields into human readable values.

    Saved data records are dicts with the folloing keys:

    Key       | Description
    ----------|-----------------------------------------------
    pos       | Number of the storage position
    date      | Date in ISO-8601 format (YYYY-MM-DD)
    time      | Time (HH:MM:SS)
    value     | Numerical value
    unit      | Unit of measurement (lux/fc)
    range     | Measurement range used (40, 400, ... 400k)
    mode      | normal/Pmin/Pmax/min/max/rel
    hold      | Was hold active? (hold/cont)
    APO       | Auto-power-off (on/off)
    power     | Power status (ok/low)
    dispmode  | Active display mode (time/day/sampling/year)
    memload   | No idea what this is (0/1/2). Name may change in the future.
    """

    dat2 = []
    for rec in dat["data"]:
        if rec["pos"] == 0:
            break
        # bcd decoding
        for key in ["year", "week", "month", "day", "hour", "minute", "second"]:
            rec[key] = bcd2int(rec[key])

        stat0 = decode_stat0(rec["stat0"])
        stat1 = decode_stat1(rec["stat1"])

        dtime = datetime.datetime(
            2000 + rec["year"],
            rec["month"],
            rec["day"],
            rec["hour"],
            rec["minute"],
            rec["second"],
        )

        # reassemble the record in a more practical format
        rec = {
            "pos": rec["pos"],
            "date": dtime.date(),
            "time": dtime.time(),
            "value": stat1["sign"]
            * (100 * rec["datH"] + rec["datL"])
            * stat0["Frange"],
            "unit": stat0["unit"],
            "range": stat0["range"],
            "mode": stat0["mode"],
            "hold": stat0["hold"],
            "APO": stat0["APO"],
            "power": stat1["power"],
            "dispmode": stat1["dispmode"],
            "memload": stat1["memload"],
        }

        dat2.append(rec)

    return dat2


def saved_data2csv(dat, sep, header=True):
    "returns csv from live data dict"

    cols = (
        "pos",
        "date",
        "time",
        "value",
        "unit",
        "range",
        "mode",
        "hold",
        "APO",
        "power",
        "dispmode",
        "memload",
    )
    csv = []
    if header:
        csv = [sep.join(cols)]
    for rec in dat:
        if rec["pos"] > 0:
            csv.append(sep.join(([str(rec[col]) for col in cols])))

    return "\n".join(csv)


def parse_logger_data(blob):
    """Decode logger_data to csv

    Accept a binary blob of logger data and parse it.
    Returns a cosntruct container object with parsed data.
    """

    Datapoint = Struct(
        "datH" / Int8ub, "datL" / Int8ub, "stat0" / Int8ub, "next" / Peek(Int16ub)
    )

    Group = Struct(
        "magic" / Const(b"\xaa\x56"),
        "groupno" / Int8ub,
        "sampling" / Int8ub,
        "reserved" / Const(b"\x00\x00"),
        "year" / Int8ub,
        "weekday" / Int8ub,
        "month" / Int8ub,
        "day" / Int8ub,
        "hour" / Int8ub,
        "minute" / Int8ub,
        "second" / Int8ub,
        "data"
        / RepeatUntil(
            lambda x, lst, ctx: x.next == 0xAA56 or x.next == None, Datapoint
        ),
    )

    db = Struct(
        "magic" / Const(b"\xaa\xcc"),
        "nogroups" / Int8ub,
        "bufsize" / Int16ub,
        "groups" / Array(this.nogroups, Group),
    )

    dat = db.parse(blob)

    return dat


def process_logger_data(dat):
    """Return processed logger data

    Accepts a construct container object and returns a list of logging groups.

    Each group is a list of data points. Datapoints are dicts with the following keys:

    Key       | Description
    ----------|-------------------------------------------------
    groupno   | numerical id of the logging group
    id        | measurement number within the group [0,1, ...]
    sampling  | sampling interval [s]
    date      | YYYY-MM-DD
    time      | HH:MM:SS
    value     | measurement
    unit      | Unit of measurement (lux/fc)
    range     | Measurement range used (40, 400, ... 400k)
    mode      | normal/Pmin/Pmax/min/max/rel
    hold      | Was hold active? (hold/cont)
    APO       | Auto-power-off (on/off)

    """

    logger = []
    for group in dat["groups"]:
        # bcd decoding
        for key in ["year", "weekday", "month", "day", "hour", "minute", "second"]:
            group[key] = bcd2int(group[key])

        dtime = datetime.datetime(
            2000 + group["year"],
            group["month"],
            group["day"],
            group["hour"],
            group["minute"],
            group["second"],
        )

        for i, rec in enumerate(group["data"]):

            stat0 = decode_stat0(rec["stat0"])

            # reassemble the record in a more practical format
            rec = {
                "groupno": group["groupno"],
                "id": i,
                "sampling": group["sampling"],
                "date": dtime.date(),
                "time": dtime.time(),
                #'value'    : stat1['sign'] * (100*rec['datH'] + rec['datL']) * stat0['Frange'],
                "value": (100 * rec["datH"] + rec["datL"]) * stat0["Frange"],
                "unit": stat0["unit"],
                "range": stat0["range"],
                "mode": stat0["mode"],
                "hold": stat0["hold"],
                "APO": stat0["APO"],
            }

            logger.append(rec)
            dtime += datetime.timedelta(seconds=group["sampling"])

    return logger


def logger_data2csv(dat, sep, header=True):
    "returns csv from logger data list"

    cols = (
        "groupno",
        "id",
        "date",
        "time",
        "value",
        "unit",
        "range",
        "mode",
        "hold",
        "APO",
    )
    csv = []
    if header:
        csv = [sep.join(cols)]
    for rec in dat:
        csv.append(sep.join(([str(rec[col]) for col in cols])))

    return "\n".join(csv)


def decode_stat0(byte):
    """return a dict from stat0 byte data

    The return value is a dict with decoded information form the bit field and
    contains the following keys

    Key    | Description
    -------|---------------------------------
    unit   | unit of measurement [lux/fc]
    range  | measurement range [(40, 400, ... 400k)]
    APO    | Auto-power-off (on/off)
    mode   | (normal/Pmin/Pmax/max/min/rel
    hold   | hold/cont
    Frange | Factor for decimal point of value

    This is how Frange is intended to be use:

    value = Stat0_sign * (100 * valH + valL) * Frange
    """

    Stat0 = BitStruct(
        "APO" / Flag,
        "hold" / Flag,
        "mode" / BitsInteger(3),
        "unit" / Flag,
        "range" / BitsInteger(2),
    )
    ret = Stat0.parse(bytes([byte]))

    # I know this looks wrong but that's how they implemented the range order...
    Range = {"lux": ("400k", "400", "4k", "40k"), "fc": ("40k", "40", "400", "4k")}

    mode = {
        0b000: "normal",
        0b010: "Pmin",
        0b011: "Pmax",
        0b100: "max",
        0b101: "min",
        0b110: "rel",
    }

    # factor to set decimal point depending on range
    Frange = {"40": 0.01, "400": 0.1, "4k": 1.0, "40k": 10, "400k": 100}

    ret["unit"] = ("lux", "fc")[ret["unit"]]
    ret["range"] = Range[ret["unit"]][ret["range"]]
    ret["APO"] = ("on", "off")[ret["APO"]]
    ret["mode"] = mode[ret["mode"]]
    ret["hold"] = ("cont", "hold")[ret["hold"]]
    ret["Frange"] = Frange[ret["range"]]

    return ret


def decode_stat1(byte):
    """return a dict from Stat1 byte data

    The return value is a dict with decoded information form the bit field and
    contains the folliwing keys

    Key         | Description
    ------------|---------------------------------
    power       | ok/low
    sign        | +1/-1
    displaymode | time/day/sampling-interval/year
    memload     | MEM/LOAD
    """

    Stat1 = BitStruct(
        BitsInteger(2),
        "power" / Flag,
        "sign" / Flag,
        "dispmode" / BitsInteger(2),
        "memload" / BitsInteger(2),
    )

    ret = Stat1.parse(bytes([byte]))

    dispmode = {0b00: "time", 0b01: "day", 0b10: "sampling", 0b11: "year"}

    memload = {0b00: None, 0b01: "mem", 0b10: "load", 0b11: None}

    ret["power"] = ("ok", "low")[ret["power"]]
    ret["sign"] = (1, -1)[ret["sign"]]
    ret["dispmode"] = dispmode[ret["dispmode"]]
    ret["memload"] = memload[ret["memload"]]

    return ret



"""return command definition dict

Actually, an ordered dict of dicts.
Each inner dict represents a valid command and has the following keys:

cmd     command byte (sent to instrument)
ret     boolean indicating if any data will be returned by the instrument in response
key     equivalent key press on the instrument. None if no such key press exists
desc    brief command description
"""
commandset = OrderedDict(
        [
            (
                "units",
                {
                    "cmd": b"\xfe",  # command byte
                    "ret": False,  # will data be returned?
                    "key": "UNITS",  # Equivalent key press
                    "desc": "Toggle units between lux and fc",  # description
                },
            ),
            (
                "light",
                {
                    "cmd": b"\xfd",
                    "ret": False,
                    "key": "Light/LOAD",
                    "desc": "Toggle backlight",
                },
            ),
            (
                "range",
                {
                    "cmd": b"\x7f",
                    "ret": False,
                    "key": "RANGE/APO",
                    "desc": "Cycle through measurement ranges",
                },
            ),
            (
                "save",
                {
                    "cmd": b"\xfb",
                    "ret": False,
                    "key": "REC/Setup",
                    "desc": "Save reading to memory",
                },
            ),
            (
                "peak",
                {
                    "cmd": b"\xf7",
                    "ret": False,
                    "key": "PEAK/LEFT",
                    "desc": "Toggle peak value display or next value",
                },
            ),
            (
                "rel",
                {
                    "cmd": b"\xdf",
                    "ret": False,
                    "key": "REL/RIGHT",
                    "desc": "Toggle realtive reading or previous value",
                },
            ),
            (
                "minmax",
                {
                    "cmd": b"\xbf",
                    "ret": False,
                    "key": "MAX/MIN/UP",
                    "desc": "Toggle Min/Max/current value display or increase value",
                },
            ),
            (
                "hold",
                {
                    "cmd": b"\xef",
                    "ret": False,
                    "key": "HOLD/DOWN",
                    "desc": "Toggle hold or decrease value",
                },
            ),
            (
                "off",
                {
                    "cmd": b"\xf3",
                    "ret": False,
                    "key": "POWER",
                    "desc": "Turn off the instrument",
                },
            ),
            (
                "logging",
                {
                    "cmd": b"\xdc",
                    "ret": False,
                    "key": "REC-hold",
                    "desc": "Start/stop data logging",
                },
            ),
            (
                "prevview",
                {
                    "cmd": b"\xda",
                    "ret": False,
                    "key": "PEAK-hold",
                    "desc": "Switch to previous display view mode",
                },
            ),
            (
                "nextview",
                {
                    "cmd": b"\xdb",
                    "ret": False,
                    "key": "REL-hold",
                    "desc": "Switch to next display view mode",
                },
            ),
            (
                "viewsaved",
                {
                    "cmd": b"\xde",
                    "ret": False,
                    "key": "LIGHT/LOAD-hold",
                    "desc": "Toggle view mode for saved data",
                },
            ),
            (
                "setup",
                {
                    "cmd": b"\xfa",
                    "ret": False,   
                    "key": "REC+UNITS",
                    "desc": "Enter/exit setup",
                },
            ),
#            (
#                "clearval",
#                {
#                    "cmd": b"\xee",
#                    "ret": False,   
#                    "key": "REC+LOAD",
#                    "desc": "Clear the manual value storage (does not work!)",
#                },
#            ),
            (
                "APOon",
                {
                    "cmd": b"\x7b",
                    "ret": False,   
                    "key": "REC+RANGE",
                    "desc": "Turn on Auto Power-Off (APO)",
                },
            ),
            (
                "APOoff",
                {
                    "cmd": b"\x7c",
                    "ret": False,   
                    "key": "REC+RANGE",
                    "desc": "Turn off Auto Power-Off (APO)",
                },
            ),
            (
                "get-status",
                {
                    "cmd": b"\x11",
                    "ret": True,
                    "key": None,
                    "desc": "Read status"
                    },
            ),
            (
                "get-live-data",
                {
                    "cmd": b"\x11",
                    "ret": True,
                    "key": None,
                    "desc": "Read live data"
                    },
            ),
            (
                "log-live-data",
                {
                    "cmd": b"\x11",
                    "ret": True,
                    "key": None,
                    "desc": "Log live data. See -I and -n"
                    },
            ),
            (
                "get-saved-data",
                {
                    "cmd": b"\x12",
                    "ret": True,
                    "key": None,
                    "desc": "Read manually saved data (registers 1-99)",
                },
            ),
            (
                "get-logger-data",
                {
                    "cmd": b"\x13", 
                    "ret": True, 
                    "key": None, 
                    "desc": "Read logger data"
                    },
            ),
        ]
    )


def getargs():
    "Return commandline options and arguments"

    parser = argparse.ArgumentParser(description="Talk to a PCE-174 lightmeter/logger")

    parser.add_argument(
        "-l",
        "--list",
        dest="list",
        action="store_true",
        help="list all available commands",
    )
    parser.add_argument(
        "-i",
        dest="interface",
        type=str,
        default="/dev/ttyUSB0",
        help="interface to connect to (/dev/ttyUSB0)",
    )
    parser.add_argument(
        "-f",
        dest="format",
        type=str,
        default="csv",
        choices=["csv", "repr", "construct", "raw", "hex"],
        help="specify output format (csv)",
    )
    parser.add_argument(
            '-I',
            '--samplingint',
            dest="samplingint",
            type=int,
            default=1,
            help="set sampling interval for tethered logging [s] (1)."
            )
    parser.add_argument(
            '-n',
            '--sampleno',
            dest="sampleno",
            type=int,
            default=-1,
            help="set number of samples for tethered logging [s] (-1)."
            )
    parser.add_argument(
        "-F",
        "--file",
        dest="file",
        type=str,
        default="",
        help="parse previously saved raw data instead of reading from the instrument",
    )
    parser.add_argument(
        "-s", "--sep", dest="sep", type=str, default=",", help="separator for csv (',')"
    )
    parser.add_argument(
        "command", nargs="?", type=str, help="command to send to instrument"
    )

    return parser.parse_args()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

# EOF
