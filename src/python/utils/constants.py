import os
import time
import logging

from enum import Enum
import serial


logger = logging.getLogger(__name__)

# PATHS

ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '../../..'))
# assert os.path.split(ROOT_DIR)[-1] == 'pixybattle'  # make sure the relative path works

# defining PixyCam sensory variables
PIXY_MIN_X = 0
PIXY_MAX_X = 319
PIXY_MIN_Y = 0
PIXY_MAX_Y = 199

PIXY_X_CENTER = ((PIXY_MAX_X - PIXY_MIN_X) / 2)
PIXY_Y_CENTER = ((PIXY_MAX_Y - PIXY_MIN_Y) / 2)
PIXY_RCS_MIN_POS = 0
PIXY_RCS_MAX_POS = 1000
PIXY_RCS_CENTER_POS = ((PIXY_RCS_MAX_POS - PIXY_RCS_MIN_POS) / 2)
BLOCK_BUFFER_SIZE = 10

# defining PixyCam motor variables
PIXY_RCS_PAN_CHANNEL = 0
PIXY_RCS_TILT_CHANNEL = 1

PAN_PROPORTIONAL_GAIN = 400
PAN_DERIVATIVE_GAIN = 300
TILT_PROPORTIONAL_GAIN = 500
TILT_DERIVATIVE_GAIN = 400

# MOTOR CONSTANTS

MAX_MOTOR_SPEED = 300  # 480
MIN_MOTOR_SPEED = -480


# defining weight matrix for each signature
SIG_ENEMY1 = 1
SIG_DEFAULT1 = 2
SIG_SELF1 = 3
SIG_BOUNDARY1 = 4
SIG_ENEMY2 = 5
SIGNATURE_LIST = [SIG_ENEMY1, SIG_DEFAULT1, SIG_SELF1, SIG_BOUNDARY1, SIG_ENEMY2]
TARGET_WEIGHT_MATRIX = [10., 5., 0., 0., 10.]


# LASER CONSTANTS
LASER_COOLDOWN = 1  # seconds
RECOVERY = 5  # time it takes for laser to reactivate after being hit, in seconds

# TWEETING

TWEET_DEFAULT_PROB = 1


class Situation(Enum):
    """Enumerate the possible situations for which there are canned tweets available."""
    STARTING_UP = 'starting_up.txt'
    LASER_FIRING = 'laser_firing.txt'
    RECEIVED_HIT = 'received_hit.txt'
    MOVING = 'moving.txt'
    SHUTTING_DOWN = 'shutting_down.txt'
    RANDOM = 'random.txt'


# todo: may not be necessary
class PixySerial(object):
    RETRY_INTERVAL = 10  # seconds
    SERIAL_DEVICE = '/dev/ttyACM0'
    BAUD_RATE = 9600
    _serial = None

    def __init__(self):
        raise ValueError(
            'PixySerial is an abstract class and should not be instantiated. Call PixySerial.get() instead.'
        )

    @classmethod
    def get(cls):
        if cls._serial is None:
            logger.debug('Getting serial device {}'.format(cls.SERIAL_DEVICE))

        while cls._serial is None:
            try:
                cls._serial = serial.Serial(cls.SERIAL_DEVICE, cls.BAUD_RATE)
                break
            except:
                logger.warning(
                    "Could not open serial device {}, retrying in {}s".format(cls.SERIAL_DEVICE, cls.RETRY_INTERVAL)
                )
                time.sleep(10)

        return cls._serial


# BEHAVIOURAL STATES

class Behaviour(Enum):
    """
    Definition of robot's behavioural states (here for consistency). Add states where required, but always refer to
    them through this static class for consistency.

    Examples
    --------
    Fictitious robot API for demonstrative purposes
    >>> example_bot.set_behaviour(Behaviour.SEARCH)
    >>> if example_bot.behaviour == Behaviour.SEARCH:
    >>>     example_bot.do_things()
    """

    SEARCH = 'search'
    """Looking for target while moving"""

    CHASE = 'chase'
    """Target acquired, go towards it"""

    FIRE = 'fire'
    """Stationary, shoot"""

    KILLED = 'killed'
    """Recently shot: stationary for short period"""
