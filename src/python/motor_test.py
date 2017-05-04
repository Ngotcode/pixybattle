from __future__ import division
from utils.constants import MAX_MOTOR_SPEED
import logging
from utils.bot_logging import get_logger_name
import pytest
import time


THROTTLE_LEVEL = 0.5
MOTOR_WAIT = 1

CAMERA_WAIT = 1

PIXY_RCS_PAN_CHANNEL = 0  # todo: replace with constant
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


def test_import_motors():
    from pololu_drv8835_rpi import motors

def test_import_pixy():
    from pixy import pixy


logger = logging.getLogger(get_logger_name(logging.DEBUG))
try:
    from pololu_drv8835_rpi import motors
except:
    logger.error('Could not import `motors`, using dummy and bypassing waits')
    MOTOR_WAIT = 0
    motors = DummyMotors()

try:
    from pixy import pixy
except:
    logger.error('Could not import `pixy`, using dummy and bypassing waits')
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
    logger.debug('Angling camera to value %d (%.3f degrees azimuth)', arg_value, angle)

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
    logger.info('Testing movement: %s', msg.upper())
    left_drive, right_drive = left*drive_level, right*drive_level
    logger.debug('Setting speed: left %d, right %s', left_drive, right_drive)
    if isinstance(motors, Dummy):
        logger.warning('Using dummy motors')
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
    logger.debug('Testing camera pan: %s', msg.upper())
    if isinstance(motors, Dummy):
        logger.warning('Using dummy pixy interface')
    pan_camera(angle)
    time.sleep(CAMERA_WAIT)


if __name__ == '__main__':
    pytest.main(['-s', __file__])
