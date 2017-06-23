#!/usr/bin/env python
"""
THESE TESTS ARE SKIPPED

Test module to prove that the motors are working (i.e. it has battery, the wires are plugged in the right way round
etc.).

Usage: from the command line, `pytest -s <this_file>`, or just run it as a script.

These tests can run in two modes.

The first mode is for use on the robot: `test_import_*` should pass and the robot should move as described in the log
(it needs some space to do so).

The second mode is for local testing (basically, proving that the tests themselves are internally consistent). The
motor commands are passed to dummy objects which just assert that the arguments look correct. The waits between motor
commands are skipped to save time. `test_import_*` should both fail in this mode.
"""

from __future__ import division
from utils.constants import MAX_MOTOR_SPEED, PIXY_RCS_PAN_CHANNEL
import logging
from utils.bot_logging import set_log_level
import pytest
import time


pytestmark = pytest.mark.skip('Motor tests are either useless or annoying')


THROTTLE_LEVEL = 0.5
MOTOR_WAIT = 1

CAMERA_WAIT = 1

CAMERA_MAX_ARG = 1000
CAMERA_SERVO_RANGE = 120  # degrees


class Dummy(object):
    pass


class DummyMotors(Dummy):
    def setSpeeds(self, drive1, drive2):
        for arg in (drive1, drive2):
            assert isinstance(arg, int)
            assert abs(arg) < MAX_MOTOR_SPEED


class DummyPixy(Dummy):
    def pixy_rcs_set_position(self, angle_arg, channel_arg):
        assert isinstance(angle_arg, int)
        assert 0 <= angle_arg <= 1000
        assert isinstance(channel_arg, int)


@pytest.mark.xfail
def test_import_motors():
    from pololu_drv8835_rpi import motors


@pytest.mark.xfail
def test_import_pixy():
    from pixy import pixy


logger = logging.getLogger(__name__)
set_log_level(logging.DEBUG)
try:
    from pololu_drv8835_rpi import motors
except:
    logger.exception('Could not import `motors`, using dummy and bypassing waits')
    MOTOR_WAIT = 0
    motors = DummyMotors()

try:
    from pixy import pixy
except:
    logger.exception('Could not import `pixy`, using dummy and bypassing waits')
    CAMERA_WAIT = 0
    pixy = DummyPixy()


drive_level = int(MAX_MOTOR_SPEED / 2)

logger.info('Throttle level is %d', THROTTLE_LEVEL)
logger.info('Drive level is %d', drive_level)


def pan_camera(extent):
    """
    Move camera to specified angle as a proportion of its maximum (clockwise from straight forward)

    Parameters
    ----------
    extent : float
        Between -1 and 1

    Returns
    -------
    int
        Between 0 and 1000
    """
    if not -1 <= extent <= 1:
        raise ValueError('Camera angle must be between -1 and 1')

    arg_value = int((extent + 1) * CAMERA_MAX_ARG/2)
    angle = extent * CAMERA_SERVO_RANGE/2
    logger.debug('Angling camera to value %d (%.1f degrees azimuth)\n%s', arg_value, angle, '-'*80)

    pixy.pixy_rcs_set_position(PIXY_RCS_PAN_CHANNEL, arg_value)
    return arg_value


@pytest.mark.parametrize('left,right,msg', [
    (0, 0, 'stationary'),
    (1, 0, 'left wheel forward'),
    (-1, 0, 'left wheel backward'),
    (0, 1, 'right wheel forward'),
    (0, -1, 'right wheel backward'),
    (1, -1, 'spin right'),
    (-1, 1, 'spin left'),
    (1, 1, 'drive forward'),
    (-1, -1, 'drive backward'),
    (0, 0, 'stationary')
])
def test_motors(left, right, msg):
    if isinstance(motors, Dummy):
        logger.warning('Using dummy motors')

    logger.info('Testing movement: %s\n', msg.upper())
    left_drive, right_drive = left*drive_level, right*drive_level
    logger.debug('Setting speed: left %d, right %s\n%s', left_drive, right_drive, '-'*80)

    motors.setSpeeds(left_drive, right_drive)
    time.sleep(MOTOR_WAIT)
    motors.setSpeeds(0, 0)  # assumes that stopping works


@pytest.mark.parametrize('angle,msg', [
    (0, 'centered'),
    (-1, 'extreme left'),
    (-0.5, 'moderate left'),
    (0, 'centered'),
    (0.5, 'moderate right'),
    (1, 'extreme right'),
    (0, 'centered')
])
def test_camera_servo(angle, msg):
    if isinstance(motors, Dummy):
        logger.warning('Using dummy pixy interface')
    logger.debug('Testing camera pan: %s\n', msg.upper())
    pan_camera(angle)
    time.sleep(CAMERA_WAIT)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
