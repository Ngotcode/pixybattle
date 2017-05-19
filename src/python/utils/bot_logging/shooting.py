"""
Process for automatically firing the laser as fast as possible.

Examples
--------

Import and instantiate our laser commander
>>> from utils.shooting import LaserCommander
>>> lt_worf = LaserCommander()

Start the laser controller process
>>> lt_worf.start()

Instruct the laser commander
>>> lt_worf.fire_once()
>>> lt_worf.fire_at_will()
>>> lt_worf.hold_fire()

You must remember to stand down the commander!
>>> lt_worf.stand_down()

You can use the Laser Commander in a `with` statement so that you don't have to remember anything, and errors are 
handled better:

>>> with LaserCommander() as lt_worf:
>>>     lt_worf.fire_at_will()

The Commander will be stood down automatically upon leaving the `with` statement (including error cases)
"""

from multiprocessing import Process, Pipe

from enum import Enum
import serial

from utils.constants import LASER_TIMEOUT, SERIAL_DEVICE, BAUD_RATE
import time


POLL_TIMEOUT = 0.001  # arbitrarily small number


class Command(Enum):
    FIRE_ONCE = 'fire_once'
    FIRE_AT_WILL = 'fire_at_will'
    HOLD_FIRE = 'hold_fire'
    STAND_DOWN = 'stand_down'


class LaserCommander(object):
    __instance = None

    def __init__(self):
        self._conn, laser_conn = Pipe()
        self._laser = AutoLaser(laser_conn, False, LASER_TIMEOUT)
        self.__stood_down = False

    def start(self):
        self._laser.start()

    def _send_command(self, command):
        if self.stood_down:
            raise ValueError('Cannot send command to stood-down Laser Commander - create a new one.')
        self._conn.send(command)

    @property
    def stood_down(self):
        return self.__stood_down

    def fire_once(self):
        self._send_command(Command.FIRE_ONCE)

    def fire_at_will(self):
        self._send_command(Command.FIRE_AT_WILL)

    def hold_fire(self):
        self._send_command(Command.HOLD_FIRE)

    def stand_down(self):
        self._send_command(Command.STAND_DOWN)
        self.__stood_down = False
        self._laser.join()
        self.__instance = None

    @classmethod
    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = object.__new__(cls)

        return cls.__instance

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stand_down()


class AutoLaser(Process):
    def __init__(self, conn, firing=False, timeout=LASER_TIMEOUT):
        super(AutoLaser, self).__init__()
        self.conn = conn
        self.firing = firing
        self.timeout = timeout
        self.ser = serial.Serial(SERIAL_DEVICE, BAUD_RATE)

    def run(self):
        while True:
            if self.conn.poll(POLL_TIMEOUT):
                signal = self.conn.recv()
                if signal == Command.FIRE_ONCE:
                    self.firing = False
                    self._fire()
                elif signal == Command.FIRE_AT_WILL:
                    self.firing = True
                    self._fire()
                elif signal == Command.HOLD_FIRE:
                    self.firing = False
                elif signal == Command.STAND_DOWN:
                    return
                else:
                    ValueError('Unknown command {} received'.format(signal))
            elif self.firing:
                self._fire()

    def _fire(self):
        self.ser.write("FIRE\n")
        time.sleep(self.timeout)
