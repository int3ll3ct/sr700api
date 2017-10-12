"""
busprt_max31855k.py

A class to control a MAX31855K thermocouple chip connected via SPI to
a Sparkfun Bus Pirate v3.6.
"""
"""
MIT License

Copyright (c) 2017 int3ll3ct.ly@gmail.com

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import logging
import ctypes
import serial
from pyBusPirateLite.SPI import SPI as busprtspi
from pyBusPirateLite.SPI import PIN_POWER, PIN_CS, CFG_PUSH_PULL, CFG_IDLE

class Max31855_bitfield( ctypes.BigEndianStructure ):
    _pack_ = 1
    _fields_ = [("thermocouple_temp", ctypes.c_int, 14),
                ("reserved1", ctypes.c_uint, 1),
                ("fault", ctypes.c_uint, 1),
                ("int_junc_temp", ctypes.c_int, 12),
                ("reserved2", ctypes.c_uint, 1),
                ("scv_fault", ctypes.c_uint, 1),
                ("scg_fault", ctypes.c_uint, 1),
                ("oc_fault", ctypes.c_uint, 1)]


class Max31855_data(ctypes.Union):
    _pack_ = 1
    _fields_ = [("bit_values", Max31855_bitfield),
                ("bytes", ctypes.c_uint8 * 4)]


class Max31855kDevice(object):
    """ A class to control a MAX31855K thermocouple chip connected via SPI to
        a Sparkfun Bus Pirate v3.6. """
    def __init__(self):
        """ Creates a BusprtMax31855k object, optionally specifying the
            dev port to which the Bus Pirate is attached."""
        # init vars
        self.spi = None
        self.max31855_pkt = Max31855_bitfield()
        self.max31855_union = Max31855_data()

    def disconnect(self):
        """ disconnects from a previously connected Bus Pirate,
            if such connection exists, else, no action is performed. """
        if self.spi is not None:
            # power down the hardware on exit
            self.spi.config = 0
            self.spi.pins = 0
            # disconnect from hardware
            self.spi.disconnect()
            self.spi = None

    def find_connect(self):
        """ Looks for an FTDI chip with Vendor IS 0x0403 and Product ID
            0x6002, then verifies that the device is a bus pirate,
            before returning success/fail. """
        if self.spi is not None:
            # um, what do we do here?
            return True
        # pyBusPirateLite can auto-find the bus pirate...
        self.spi = busprtspi(connect=False)
        port = self.spi.get_port()
        # when no hardware present, port is None
        if port is None:
            self.spi = None
            return False
        self.spi = busprtspi(portname=("/dev/%s" % (port)))
        if self.spi is None:
            logging.warning(
                "BusprtMax31855k.find_connect - hardware not found.")
            return False
        # we've successfully connected
        # now let's configure the details
        """ pins byte:
                cfg: int
                    Pin configuration 0000wxyz
                    w=power, x=pull-ups, y=AUX, z=CS
                Notes
                -----
                Enable (1) and disable (0) Bus Pirate peripherals and pins.
                Bit w enables the power supplies,
                bit x toggles the on-board pull-up resistors,
                y sets the state of the auxiliary pin, and
                z sets the chip select pin.
                Features not present in a specific hardware version are ignored.
                Bus Pirate responds 0x01 on success.
        """
        self.spi.pins = PIN_POWER | PIN_CS
        """ config byte: 0000wxyz
                This command configures the SPI settings.
                Options and start-up defaults are the same as the user terminal
                SPI mode.
                w= pin output HiZ(0)/3.3v(1),
                x=CKP clock idle phase (low=0),
                y=CKE clock edge (active to idle=1),
                z=SMP sample time (middle=0).
                The Bus Pirate responds 0x01 on success.
                Default raw SPI startup condition is 0010.
                HiZ mode configuration applies to the SPI pins and the CS pin,
                but not the AUX pin.
                See the PIC24FJ64GA002 datasheet and the SPI section[PDF] of the
                PIC24 family manual for more about the SPI configuration settings.
           0x01 CFG_SAMPLE: sample time (0 = middle)
           0x02 CFG_CLK_EDGE: clock edge (1 = active to idle)
           0x04 CFG_IDLE: clock idle phase (0 = low)
           0x08 CFG_PUSH_PULL: pin output (0 = HiZ, 1 = push-pull)
        """
        self.spi.config = CFG_PUSH_PULL | CFG_IDLE
        """ speed: acceptable strings are
             '30kHz' : 0b000,
             '125kHz': 0b001,
             '250kHz': 0b010,
             '1MHz'  : 0b011,
             '2MHz'  : 0b100,
             '2.6MHz': 0b101,
             '4MHz'  : 0b110,
             '8MHz'  : 0b111
        """
        self.spi.speed = '30kHz'

        # the first read after an init gives some wonky results,
        # so let's just perform a throwaway read right away.
        self.read()

        return True

    def read(self):
        """ Read the temps and bitflags from the device.
            All temperatures in degrees Celsius.

            Returns:
                thermoocuple_temp (degC, float)
                fault - hardsware fault detected, see detailed fault
                int_junc_temp (degC, float)
                scv_fault
                scg_fault
                oc_fault

            If hardware not present, will set fault to 1,
            and all detailed fault bits to 0.
            """
        # bail if we're not connected!
        if self.spi is None:
            logging.warning("BusprtMax31855k.read - hardware not present!")
            return( 0.0,1,0.0,0,0,0)

        try:
            self.spi.cs = True
            bytes_read = self.spi.transfer([0,0,0,0])
            self.spi.cs = False
        except serial.serialutil.SerialException:
            logging.error(
                "BusprtMax31855k - connection lost, I/O failed on read.")
            self.spi = None
            return( 0.0,1,0.0,0,0,0)
        # print(bytes_read)
        # analyze bytes
        self.max31855_union.bytes = (
            (ctypes.c_ubyte * len(bytes_read))(*bytes_read))
        # print("max31855_union: ",
        #     ["0x%02x" % x for x in self.max31855_union.bytes])
        # print("thermocouple_temp: ",
        #     self.max31855_union.bit_values.thermocouple_temp/4.0)
        # print("fault: ", self.max31855_union.bit_values.fault)
        # print("int_junc_temp: ",
        #     self.max31855_union.bit_values.int_junc_temp/16.0)
        # print("scv_fault: ", self.max31855_union.bit_values.scv_fault)
        # print("scg_fault: ", self.max31855_union.bit_values.scg_fault)
        # print("oc_fault: ", self.max31855_union.bit_values.oc_fault)
        return (
            self.max31855_union.bit_values.thermocouple_temp/4.0,
            self.max31855_union.bit_values.fault,
            self.max31855_union.bit_values.int_junc_temp/16.0,
            self.max31855_union.bit_values.scv_fault,
            self.max31855_union.bit_values.scg_fault,
            self.max31855_union.bit_values.oc_fault
            )

    def is_connected(self):
        """ Reports whether we are actively connected to hardware.
            Returns:
                True if connected, otherwise False """
        if self.spi is not None:
            return True
        return False
