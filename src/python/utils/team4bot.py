#!/usr/bin/env python

import time
import math
import serial
import pololu_drv8835_rpi
import logging

from .bot_logging import get_logger_name
from .constants import SERIAL_DEVICE, BAUD_RATE, MAX_MOTOR_SPEED, DEADBAND_PPN
from .general import setup


logger = logging.getLogger(get_logger_name(logging.DEBUG))

# throttle is how much of the total_drive to use [0~1]
THROTTLE_DEFAULT = 0.7
# differential drive level [0~1]
# this is the drive level allocated for steering [0~1] dynamically modulate
DIFF_DRIVE_DEFAULT = 0.3
# this is the gain for scaling diff_drive
DIFF_GAIN_DEFAULT = 1
# this ratio determines the steering [-1~1]
BIAS_DEFAULT = 1
# this ratio determines the drive direction and magnitude [-1~1]
ADVANCE_DEFAULT = 1
# this gain currently modulates the forward drive enhancement
DRIVE_GAIN_DEFAULT = 1
# body turning p-gain
H_PGAIN_DEFAULT = 0.5
# body turning d-gain
H_DGAIN_DEFAULT = 0

KILLED_TIME = 5  # seconds


class RobotController(object):
    _instance = None

    def __init__(self, **kwargs):
        """
        
        Parameters
        ----------
        kwargs
            Can include:
              - deadband_ppn (deadband as a proportion of maximum motor speed)
              - total_drive_ppn (default 1)
              - throttle
              - diff_drive
              - diff_gain
              - drive_gain
              - advance
              - bias
        """
        self.deadband = kwargs.get('deadband_ppn', DEADBAND_PPN) * MAX_MOTOR_SPEED
        self.total_drive = kwargs.get('total_drive_ppn', 1) * MAX_MOTOR_SPEED
        self.throttle = kwargs.get('throttle', THROTTLE_DEFAULT)
        self.diff_drive = kwargs.get('diff_drive', DIFF_DRIVE_DEFAULT)
        self.diff_gain = kwargs.get('diff_drive', DIFF_GAIN_DEFAULT)
        self.drive_gain = kwargs.get('drive_gain', DRIVE_GAIN_DEFAULT)
        self.h_pgain = kwargs.get('h_pgain', H_PGAIN_DEFAULT)
        self.h_pgain = kwargs.get('h_dgain', H_DGAIN_DEFAULT)
        self.bias = kwargs.get('bias', BIAS_DEFAULT)
        self.advance = kwargs.get('advance', ADVANCE_DEFAULT)
        self._motors = pololu_drv8835_rpi.motors
        self._motor_speeds = (0, 0)

        self.__behaviour = 'stopped'  # todo: replace with enum

        self.behaviour_methods = {
            'stopped': self._stop,
            'search': self._search,
            'proceed': self.set_motor_speeds,
            'killed': self._killed
        }

        self._previous_behaviour = self.__behaviour

        self.serial = self._setup_serial()

    @property
    def _syn_drive(self):
        """Drive level to be applied to both wheels"""
        return self.advance * (1 - self.diff_drive) * self.throttle * self.total_drive

    @property
    def _left_diff(self):
        """Drive level to add to left wheel"""
        return self.bias * self.diff_drive * self.throttle * self.total_drive

    @property
    def _right_diff(self):
        """Drive level to add to right wheel"""
        return -self._left_diff

    @property
    def behaviour(self):
        """Behavioural state of the robot"""
        return self.__behaviour

    @behaviour.setter
    def behaviour(self, value):
        logger.debug('Setting behaviour to %s', value)
        if self.behaviour is not 'killed':
            self._previous_behaviour = self.behaviour
        self.__behaviour = value

    def constrain_drive(self, drive):
        """
        Return drive level to be applied to motors
        
        Parameters
        ----------
        drive : number
            Drive level which may fall outside of bounds

        Returns
        -------
        int
            Drive level which is either 0, or between the deadband and max levels (either +ve or -ve)
        """
        if abs(drive) < self.deadband:
            logger.debug('Drive level %s is below deadband, setting to 0', str(drive))
            return 0

        if abs(drive) > MAX_MOTOR_SPEED:
            new_drive = int(math.copysign(MAX_MOTOR_SPEED, drive))
            logger.debug('Drive level %s is above max motor speed, setting to %s', str(drive), str(new_drive))
        else:
            new_drive = int(drive)

        return new_drive

    def set_motor_speeds(self, left_right_speeds=None):
        """
        
        Parameters
        ----------
        left_right_speeds : None or array-like (size 2)
            Sequence of speeds in Left-Right order. Defaults to determining speeds using member variables
        """
        if left_right_speeds is None:
            left_right_speeds = (self._syn_drive + diff for diff in (self._left_diff, self._right_diff))
        else:
            logger.debug('Motor speed set manually')
            assert len(left_right_speeds) == 2

        self._motor_speeds = [self.constrain_drive(speed) for speed in left_right_speeds]

        logger.debug('Setting speed to %s', repr(self._motor_speeds))

        self._motors.setSpeeds(*self._motor_speeds)

    def set_motor_speeds_proportional(self, left_right_speeds_ppn):
        """
        
        Parameters
        ----------
        left_right_speeds_ppn : array-like
            Sequence of speeds in left-right order as a proportion of the maximum (i.e. -1 to 1)
        """
        self.set_motor_speeds([MAX_MOTOR_SPEED * speed_ppn for speed_ppn in left_right_speeds_ppn])

    def _check_if_killed(self):
        """Set behaviour to killed if we have been shot"""
        if self.serial.in_waiting:
            logger.debug("reading line from serial..")
            code = self.serial.readline().rstrip()
            logger.debug("Got IR code %s", str(code))  # todo: actually check whether this is the right code
            logger.critical("YOU SUNK MY BATTLESHIP")
            self.behaviour = 'killed'
            return True

    def _killed(self):
        """Execute behaviour associated with killed state"""
        time.sleep(KILLED_TIME)
        logger.info('Waking up')
        self.serial.reset_output_buffer()  # so that shots received while dead aren't queued in the buffer
        self.behaviour = self._previous_behaviour

    def halt(self):
        """
        Stop without tidying up any intermediate variables. Can be used to quickly abort, or to stop in a behaviour where it
        is possible to resume.
        """
        logger.info('Halting')
        self.set_motor_speeds((0, 0))
        return 1

    def _stop(self):
        """
        Gracefully stop.
        """
        logger.info('Initiating stop behaviour')
        self.throttle = 0
        self.set_motor_speeds()
        return 1

    def _search(self):
        logger.info('Initiating search behaviour')
        # do things
        return 1

    def _proceed(self):
        """
        Respond only to changes in member variables.
        """
        logger.info('Initiating proceed behaviour')
        self.set_motor_speeds()
        return 1

    def start(self):
        """Main entry point to the robot's function"""
        self._proceed()
        self._loop()

    def _loop(self):
        """Main loop"""
        while True:
            self._check_if_killed()
            ret_code = self.behaviour_methods[self.behaviour]()
            if not ret_code:
                break

    @classmethod
    def __new__(cls, **kwargs):
        """
        As every script shares the same motors, it's better to prevent users creating more than one RobotController 
        instance.
        """
        if cls._instance:
            logging.warning('RobotController already exists, new parameters and defaults will be ignored')
            # todo: destroy previous instance and return a new one instead?
        else:
            cls._instance = RobotController(**kwargs)
        return cls._instance

    def destroy(self):
        self.halt()
        self.__class__._instance = None
        logger.info('RobotController destroyed')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.destroy()

    def _setup_serial(self):
        while True:
            try:
                return serial.Serial(SERIAL_DEVICE, BAUD_RATE)
            except:
                logger.warning("Could not open serial device %s, waiting for 10 seconds", SERIAL_DEVICE)
                time.sleep(10)


if __name__ == '__main__':
    setup()
    with RobotController() as pixybot_the_almighty_destroyer:
        pixybot_the_almighty_destroyer.start()
