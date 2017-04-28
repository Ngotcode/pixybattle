#!/usr/bin/env python

import time
import sys
import signal
import ctypes
import math
import serial
from datetime import datetime
from pololu_drv8835_rpi import motors
import logging

from .bot_logging import get_logger_name
from .constants import SERIAL_DEVICE, BAUD_RATE, MAX_MOTOR_SPEED, MIN_MOTOR_SPEED, DEADBAND_PPN
from .general import setup


logger = logging.getLogger(get_logger_name(logging.DEBUG))

while True:
    try:
        ser = serial.Serial(SERIAL_DEVICE, BAUD_RATE)
        break
    except:
        logger.warning("Could not open serial device %s", SERIAL_DEVICE)
        time.sleep(10)

setup()

run_flag = 1

# 20ms time interval for 50Hz
dt = 20
# check timeout dt*3
timeout = 0.5
current_time = datetime.now()
last_time = datetime.now()


# defining motor function variables
# 5% drive is deadband
deadband = DEADBAND_PPN * MAX_MOTOR_SPEED
# total_drive is the total power available
total_drive = MAX_MOTOR_SPEED
# throttle is how much of the total_drive to use [0~1]
throttle = 0.7
# differential drive level [0~1]
# this is the drive level allocated for steering [0~1] dynamically modulate
diff_drive = 0.3
# this is the gain for scaling diff_drive
diff_gain = 1
# this ratio determines the steering [-1~1]
bias = 1
# this ratio determines the drive direction and magnitude [-1~1]
advance = 1
# this gain currently modulates the forward drive enhancement
drive_gain = 1
# body turning p-gain
h_pgain = 0.5
# body turning d-gain
h_dgain = 0




killed = False


def loop():
    """
    Main loop, Gets blocks from pixy, analyzes target location,
    chooses action for robot and sends instruction to motors
    """
    global throttle, diff_drive, diff_gain, bias, advance, turn_error, current_time, last_time, object_dist, dist_error, pan_error_prev, dist_error_prev, pan_loop, killed

    if ser.in_waiting:
        print("reading line from serial..")
        code = ser.readline().rstrip()
        print("Got IR code {}".format(code))
        killed = True

    if killed:
        motors.setSpeeds(0, 0)
        time.sleep(5)

    current_time = datetime.now()
    drive()
    return run_flag


def constrain_drive(drive_ppn):
    """
    
    Parameters
    ----------
    drive_ppn : float
        [-1~1]

    Returns
    -------
    float
        Constrained drive proportion
    """
    if abs(drive_ppn) < DEADBAND_PPN:
        return 0

    if drive_ppn < -1:
        return -1

    if drive_ppn > 1:
        return 1

    return drive_ppn


def drive():
    # syn_drive is the drive level for going forward or backward (for both
    # wheels)
    syn_drive = advance * (1 - diff_drive) * throttle * total_drive
    left_diff = bias * diff_drive * throttle * total_drive
    right_diff = -bias * diff_drive * throttle * total_drive

    # construct the drive levels
    l_drive = (syn_drive + left_diff)
    r_drive = (syn_drive + right_diff)

    # Make sure that it is outside dead band and less than the max
    if l_drive > deadband:
        if l_drive > MAX_MOTOR_SPEED:
            l_drive = MAX_MOTOR_SPEED
    elif l_drive < -deadband:
        if l_drive < -MAX_MOTOR_SPEED:
            l_drive = -MAX_MOTOR_SPEED
    else:
        l_drive = 0

    if r_drive > deadband:
        if r_drive > MAX_MOTOR_SPEED:
            r_drive = MAX_MOTOR_SPEED
    elif r_drive < -deadband:
        if r_drive < -MAX_MOTOR_SPEED:
            r_drive = -MAX_MOTOR_SPEED
    else:
        r_drive = 0

    # Actually Set the motors
    motors.setSpeeds(int(l_drive), int(r_drive))


class Team4Bot(object):
    def __init__(self, **kwargs):
        fd_total_drive = kwargs.get('max_motor_speed', MAX_MOTOR_SPEED)
        bk_total_drive = kwargs.get('min_motor_speed', -MAX_MOTOR_SPEED)

    def drive(self, left_drive, right_drive):
        """
        
        Parameters
        ----------
        left_drive : float
            Proportion of possible drive, [-1~1]
        right_drive : float
            Proportion of possible drive, [-1~1]
        """

        motors.setSpeeds(constrain_drive(left_drive)*MAX_MOTOR_SPEED, constrain_drive(right_drive)*MAX_MOTOR_SPEED)

    def drive_ppn_to_(self, drive_ppn):

    def forward(self):