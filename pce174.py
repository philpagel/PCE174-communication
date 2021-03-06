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

__version__ = 1.0
__author__ = "Philipp Pagel"
__copyright__ = "Copyright 2018, 2019, Philipp Pagel"
__license__ = "MIT License"


def main():
    "The main function"

    args = getargs()

    if args.command=="press":
        # press buttons
        if len(args.args)!=1:
            sys.exit("'press' expects a single argument, {} found".format(len(button)))
        press_button(args.port, args.args[0])
    elif args.command=="get":
        # get status information
        if len(args.args)!=1:
            sys.exit("'get' command takes exactly 1 argument ({} given)".format(len(args.args)))
        print(getvar(args.port, args.args[0]))
    elif args.command=="set":
        # set things
        if len(args.args)!=2:
            sys.exit("'set' command takes exactly 2 argument ({} given)".format(len(args.args)))
        setvar(args.port, var=args.args[0], value=args.args[1])
    elif args.command=="read":
        # read data from instrument
        if len(args.args)!=1:
            sys.exit("'read' command takes exactly 1 argument ({} given)".format(len(args.args)))
        dat = read_data(port=args.port, datatype=args.args[0], outformat=args.format, sep=args.sep, fromfile=args.file, header=True)
        if args.format in ('repr', 'csv', 'construct'):
            dat = str(dat) + "\n"
            dat = dat.encode("utf-8")
        sys.stdout.buffer.write(bytes(dat))
        #print(dat)
    elif args.command=="log":
        # tethered logging
        log_live_data(port=args.port, outformat=args.format, sampleno=args.sampleno, interval=args.samplingint, sep=args.sep)
    elif args.command=="setup":
        # enter/exit setup
        send_cmd(args.port, 0xfa)
    else:
        sys.exit("Unknown command `{}`\nTry -h for help".format(args.command))


def press_button(port, button, n=1):
    """Send button press to instrument

    Valid values of button: units, light, load, range, apo, rec, peak, left, rel,
        right, max, min, up, hold, down, off, REC, PEAK, REL, LOAD, LIGHT
    
    lower case button names indicate a short press
    upper case button names indicate a long press/hold
    """

    cmd = {
            'units':    0xfe,
            'light':    0xfd,
            'load':     0xfd,
            'range':    0x7f,
            'apo':      0x7f,
            'rec':      0xfb,
            'peak':     0xf7,
            'left':     0xf7,
            'rel':      0xdf,
            'right':    0xdf,
            'min':      0xbf,
            'max':      0xbf,
            'up':       0xbf,
            'hold':     0xef,
            'down':     0xef,
            'off':      0xf3,
            'REC':      0xdc,
            'PEAK':     0xda,
            'LEFT':     0xda,
            'LOAD':     0xdb,
            'LIGHT':    0xdb,
            'REL':      0xde,
            'RIGHT':    0xde
            } 

    if button not in cmd:
        sys.exit("Unknown button '{}'".format(button))
    
    for i in range(n):
        send_cmd(port, cmd[button])
        if n>1:
            time.sleep(.25)


def getvar(port, var):
    """return the requested type of mode/status data
    """

    dat = read_data(port=port, datatype='live', outformat='raw')
    dat = parse_live_data(dat)
    dat = process_live_data(dat)

    if var=="status":
        dat = """date:       {date}
weekday:    {weekday}
time:       {time}
unit:       {unit}
range:      {range}
mode:       {mode}
hold:       {hold}
apo:        {apo}
power:      {power}
view:       {view}
memstat:    {memstat}
read_no:    {read_no}""".format_map(dat)
    else:
        if var not in dat.keys():
            sys.exit("Unknown parameter '{}'".format(var))
        dat = dat[var] 
    return dat


def setvar(port, var, value):
    "set variable var to value"

    validvars = {
            'mode':     ('normal', 'rel', 'min', 'max', 'pmin', 'pmax'), 
            'hold':     ('cont', 'hold'),
            'range':    {
                'lux':  ('400k', '400', '4k', '40k'), 
                'fc':   ('40k', '40', '400', '4k')
                },
            'unit':     ('lux', 'fc'), 
            'apo':      ('on', 'off'), 
            'view':     ('time', 'day', 'year', 'sampling')
            }

    if var in validvars:
        stat = read_data(port=port, datatype='live')
        time.sleep(.25)
        
        if value==stat[var]:
            pass # No change of settings necessary
        elif var == "unit":
            press_button(port, "units")
        elif var == "range":
            if value not in validvars['range'][stat["unit"]]:
                sys.exit("`{}` is not a valid range for unit `{}`".format(value, stat["unit"]))
            press_button(port, "range", pressdist(stat["range"], value, validvars["range"][stat["unit"]]))
            time.sleep(.25)
        elif var == "mode":
            if stat["mode"] != "normal":
                press_button(port, "rel", 2)
            if value == "rel":
                press_button(port, "rel", 1)
            if value == "max":
                press_button(port, "max", 1)
            if value == "min":
                press_button(port, "min", 2)
            if value == "pmax":
                press_button(port, "peak", 1)
            if value == "pmin":
                press_button(port, "peak", 2)
        elif var == "hold":
            press_button(port, "hold")
        # XXX This does not seem to work
#        elif var == "apo":
#            if value == "on":
#                send_cmd(port, 0x7b)
#            elif value == "off":
#                send_cmd(port, 0x7c)
#            return  # apo is automatically turned off by getting live data?!? So we cannot test for success
        elif var == "view":
            print(stat["view"], value)
            print ("dist:", pressdist(stat["view"], value, validvars["view"]))
            press_button(port, "RIGHT", pressdist(stat["view"], value, validvars["view"]))
            
        # test success
        time.sleep(.25)
        newval = getvar(port, var)
        if newval != value:
            sys.exit("Error: Failed to set `{}` to `{}`".format(var, value))
    else:
        sys.exit("{} is not a valid argument to `set`".format(var))
   
def pressdist(v1, v2, l):
    "return button press distance between values v1 and v2 in list l"

    p0 = [i for i,x in enumerate(l) if x == v1][0] 
    p1 = [i for i,x in enumerate(l) if x == v2][0]
    n = p1-p0
    if n<0:
        n+=4
    return n



def log_live_data(port, outformat, sampleno, interval, sep=","):
    """Log live data (tethered logging)
    """

    if sampleno <0:
        sampleno = float('Inf')
    i = 0
    while True:
        dat = read_data(port=port, datatype="live", outformat=outformat, sep=sep, header=i==0)
        dat = str(dat) + "\n"
        dat = dat.encode("utf-8")
        sys.stdout.buffer.write(bytes(dat))
        sys.stdout.flush()
        i += 1
        if sampleno >0:
            if i >= sampleno:
                break
        time.sleep(interval)
    return



def read_data(port, datatype, outformat="repr", sep=",", fromfile="", header=False):
    """
    read data from the instrument and return the results in the specified outformat

    port:       serial port to use or filename
                typically something like /dev/ttyUSB0 or com1
                if fromfile==True this is the filenem to read from
    datatype:   {live|saved|logger}
                live: current value as displayed
                saved: manually saved data (registers 1-99)
                logger: logging session data
    outformat:  {csv|repr|construct|hex|raw}
    fromfile:   {True|False}
                if True, port is interpreted as a file name to read raw data from
    """
    
    cmd = {
            "live":     0x11,
            "saved":    0x12,
            "logger":   0x13
            }

    dat = None
    if datatype not in cmd.keys():
        sys.exit("Unknown data type '{}'".format(datatype))
    else:
        if len(fromfile)>0:
            infile = open(fromfile, "rb")
            dat = infile.read()
            infile.close()
        dat = send_cmd(port, cmd[datatype], read=True) 
        dat = decode_blob(dat, datatype, outformat, sep, header=header)
    return dat



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
    msg = hello + bytes([cmd])
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

    dat = None
    if cmd == "live":
        dat = parse_live_data(blob) # blob -> construct
        if outformat == "raw":
            dat = blob
        elif outformat == "hex":
            dat = binascii.hexlify(blob) # blob -> hex
        elif outformat == "construct":
            pass
        elif outformat == "repr":
            dat = process_live_data(dat) # blob -> repr
        elif outformat == "csv":
            dat = process_live_data(dat) # blob -> repr
            dat = live_data2csv(dat, sep, header=header) # repr -> csv
        else:
            raise Exception("Unknown format `{}`".format(outformat))
    elif cmd == "saved":
        dat = parse_saved_data(blob)
        if outformat == "raw":
            dat = blob
        elif outformat == "hex":
            dat = binascii.hexlify(blob)
        elif outformat == "construct":
            pass
        elif outformat == "repr":
            dat = process_saved_data(dat)
        elif outformat == "csv":
            dat = process_saved_data(dat)
            dat = saved_data2csv(dat, sep)
        else:
            raise Exception("Unknown format `{}`".format(outformat))
    elif cmd == "logger":
        dat = parse_logger_data(blob)
        if outformat == "raw":
            dat = blob
        elif outformat == "hex":
            dat = binascii.hexlify(blob)
        elif outformat == "construct":
            pass
        elif outformat == "repr":
            dat = process_logger_data(dat)
        elif outformat == "csv":
            dat = process_logger_data(dat)
            dat = logger_data2csv(dat, sep)
        else:
            raise Exception("Unknown format `{}`".format(outformat))
    else:
        raise Exception("Unknown command `{}`.".format(cmd))

    return dat


def decode_stat0(byte):
    """return a dict from stat0 byte data

    The return value is a dict with decoded information form the bit field and
    contains the following keys

    Key    | Description
    -------|---------------------------------
    unit   | unit of measurement [lux/fc]
    range  | measurement range [(40, 400, ... 400k)]
    apo    | Auto-power-off (on/off)
    mode   | (normal/Pmin/Pmax/max/min/rel
    hold   | hold/cont
    Frange | Factor for decimal point of value

    This is how Frange is intended to be use:

    value = Stat0_sign * (100 * valH + valL) * Frange
    """

    Stat0 = BitStruct(
        "apo" / Flag,
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
    ret["apo"] = ("on", "off")[ret["apo"]]
    ret["mode"] = mode[ret["mode"]]
    ret["hold"] = ("cont", "hold")[ret["hold"]]
    ret["Frange"] = Frange[ret["range"]]

    return ret


def decode_stat1(byte):
    """return a dict from Stat1 byte data

    The return value is a dict with decoded information form the bit field and
    contains the following keys

    Key         | Description
    ------------|---------------------------------
    power       | ok/low
    sign        | +1/-1
    displaymode | time/day/sampling-interval/year
    memstat     | store/recall/logging/None
    """

    Stat1 = BitStruct(
        BitsInteger(2),
        "power" / Flag,
        "sign" / Flag,
        "view" / BitsInteger(2),
        "memstat" / BitsInteger(2),
    )

    ret = Stat1.parse(bytes([byte]))

    view = {0b00: "time", 0b01: "day", 0b10: "sampling", 0b11: "year"}

    memstat = {0b00: None, 0b01: "store", 0b10: "recall", 0b11: 'logging'}

    ret["power"] = ("ok", "low")[ret["power"]]
    ret["sign"] = (1, -1)[ret["sign"]]
    ret["view"] = view[ret["view"]]
    ret["memstat"] = memstat[ret["memstat"]]

    return ret


def parse_live_data(blob):
    """return construct container from live data blob

    Accept a binary blob of live data and parse it.
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


def parse_saved_data(blob):
    """return a construct container from saved data blob

    Accept a binary blob of saved data and parse it.
    Returns a construct container object with parsed data.
    """

    record = Struct(
        "foo" / Int8ub,  # should be 0x00 but isn't always
        #'magic' / Const(b'\x00'),
        "year" / Int8ub,
        "weekday" / Int8ub,
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


def parse_logger_data(blob):
    """return construct container from logger_data blob

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


def process_live_data(rec):
    """Return live data dict from construct container

    Accepts a construct container object and returns a dict
    representing the measurement.

    Processing comprises the assembly of common time and date formats as well
    as turning bit fields into human readable values.

    Measurement records are dicts with the following keys:

    Key       | Description
    ----------|-----------------------------------------------
    date      | Date in ISO-8601 format (YYYY-MM-DD)
    weekday   | Int (1-7)
    time      | Time (HH:MM:SS)
    value     | Numerical value of reading
    rawvalue  | raw numerical value
    unit      | Unit of measurement (lux/fc)
    range     | Measurement range used (40, 400, ... 4000k)
    mode      | normal/Pmin/Pmax/min/max/rel
    hold      | Was hold active? (hold/cont)
    apo       | Auto-power-off (on/off)
    power     | Power status (ok/low)
    view      | Active view mode (time/day/sampling/year)
    memstat   | store/recall/logging/None
    mem_no    | Number of manually saved records in memory.
    read_no   | manual storage cursor position
    """

    # bcd decoding
    for key in ["year", "weekday", "month", "day", "hour", "minute", "second"]:
        rec[key] = bcd2int(rec[key])

    stat0 = decode_stat0(rec["stat0"])
    stat1 = decode_stat1(rec["stat1"])

    # reassemble the record in a more practical format
    rec = {
        "date": "20%2.2i-%2.2i-%2.2i" % (rec["year"], rec["month"], rec["day"]),
        "weekday": rec["weekday"],
        "time": "%2.2i:%2.2i:%2.2i" % (rec["hour"], rec["minute"], rec["second"]),
        "value": stat1["sign"] * (100 * rec["dat1H"] + rec["dat1L"]) * stat0["Frange"],
        "rawvalue": (100 * rec["dat0H"] + rec["dat0L"]) * stat0["Frange"],
        "unit": stat0["unit"],
        "range": stat0["range"],
        "mode": stat0["mode"],
        "hold": stat0["hold"],
        "apo": stat0["apo"],
        "power": stat1["power"],
        "view": stat1["view"],
        "memstat": stat1["memstat"],
        "mem_no": rec["mem_no"],
        "read_no": rec["read_no"],
    }

    return rec


def process_saved_data(dat):
    """Return saved data dict from construct container

    Accepts a construct container object and returns a list of dicts
    Each dict represents one saved measurement.

    Processing comprises the assembly of common time and date formats as well as
    turning bit fields into human readable values.

    Saved data records are dicts with the folloing keys:

    Key       | Description
    ----------|-----------------------------------------------
    pos       | Number of the storage position
    date      | Date in ISO-8601 format (YYYY-MM-DD)
    weekday   | Int (1-7)
    time      | Time (HH:MM:SS)
    value     | Numerical value
    unit      | Unit of measurement (lux/fc)
    range     | Measurement range used (40, 400, ... 400k)
    mode      | normal/Pmin/Pmax/min/max/rel
    hold      | Was hold active? (hold/cont)
    apo       | Auto-power-off (on/off)
    power     | Power status (ok/low)
    view      | Active view mode (time/day/sampling/year)
    memstat   | store/recall/logging/None
    """

    dat2 = []
    for rec in dat["data"]:
        if rec["pos"] == 0: # we have reached the first empty register position
            break
        # bcd decoding
        for key in ["year", "weekday", "month", "day", "hour", "minute", "second"]:
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
            "weekday": rec["weekday"],
            "time": dtime.time(),
            "value": stat1["sign"] * (100 * rec["datH"] + rec["datL"]) * stat0["Frange"],
            "unit": stat0["unit"],
            "range": stat0["range"],
            "mode": stat0["mode"],
            "hold": stat0["hold"],
            "apo": stat0["apo"],
            "power": stat1["power"],
            "view": stat1["view"],
            "memstat": stat1["memstat"],
        }

        dat2.append(rec)

    return dat2


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
    weekday   | Int (1-7)
    time      | HH:MM:SS
    value     | measurement
    unit      | Unit of measurement (lux/fc)
    range     | Measurement range used (40, 400, ... 400k)
    mode      | normal/Pmin/Pmax/min/max/rel
    hold      | Was hold active? (hold/cont)
    apo       | Auto-power-off (on/off)

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
                "weekday": group["weekday"],
                "time": dtime.time(),
                #'value'    : stat1['sign'] * (100*rec['datH'] + rec['datL']) * stat0['Frange'],
                "value": (100 * rec["datH"] + rec["datL"]) * stat0["Frange"],
                "unit": stat0["unit"],
                "range": stat0["range"],
                "mode": stat0["mode"],
                "hold": stat0["hold"],
                "apo": stat0["apo"],
            }

            logger.append(rec)
            dtime += datetime.timedelta(seconds=group["sampling"])

    return logger


def live_data2csv(dat, sep, header=True):
    """returns csv from live data dict"""

    # define columns and assemble header
    cols = (
        "date",
        "weekday",
        "time",
        "value",
        "rawvalue",
        "unit",
        "range",
        "mode",
        "hold",
        "apo",
        "power",
        "view",
        "memstat",
        "mem_no",
        "read_no",
    )

    csv = []
    if header:
        csv = [sep.join(cols)]
    csv.append(sep.join(([str(dat[col]) for col in cols])))

    return "\n".join(csv)


def saved_data2csv(dat, sep, header=True):
    "returns csv from live data dict"

    cols = (
        "pos",
        "date",
        "weekday",
        "time",
        "value",
        "unit",
        "range",
        "mode",
        "hold",
        "apo",
        "power",
        "view",
        "memstat",
    )
    csv = []
    if header:
        csv = [sep.join(cols)]
    for rec in dat:
        if rec["pos"] > 0:
            csv.append(sep.join(([str(rec[col]) for col in cols])))

    return "\n".join(csv)


def logger_data2csv(dat, sep, header=True):
    "returns csv from logger data list"

    cols = (
        "groupno",
        "id",
        "date",
        "weekday",
        "time",
        "value",
        "unit",
        "range",
        "mode",
        "hold",
        "apo",
    )
    csv = []
    if header:
        csv = [sep.join(cols)]
    for rec in dat:
        csv.append(sep.join(([str(rec[col]) for col in cols])))

    return "\n".join(csv)


def getargs():
    "Return commandline options and arguments"

    parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description="Talk to a PCE-174 lightmeter/logger",
            epilog="""Available commands:

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

See README.md for details
"""
    )

    parser.add_argument(
        "-p",
        dest="port",
        type=str,
        default="/dev/ttyUSB0",
        help="port to connect to (default:/dev/ttyUSB0)",
    )
    parser.add_argument(
        "-f",
        dest="format",
        type=str,
        default="csv",
        choices=["csv", "repr", "construct", "raw", "hex"],
        help="specify output format for read commands (default:csv)",
    )
    parser.add_argument(
        '-i',
        '--samplingint',
        dest="samplingint",
        type=int,
        default=1,
        help="set sampling interval for tethered logging [s] (default:1)."
        )
    parser.add_argument(
        '-n',
        '--sampleno',
        dest="sampleno",
        type=int,
        default=-1,
        help="set number of samples for tethered logging [s] (default: -1)."
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
            "-s", "--sep", dest="sep", type=str, default=",", help="separator for csv (default:',')"
    )
    parser.add_argument(
        "command", nargs="?", type=str, help="command to send to instrument"
    )
    parser.add_argument(
        "args", nargs="*", help="arguments to command"
    )

    return parser.parse_args()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

# EOF
