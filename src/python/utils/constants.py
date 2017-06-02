import os
from enum import Enum


# PATHS

ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '../../..'))
assert os.path.split(ROOT_DIR)[-1] == 'pixybattle'  # make sure the relative path works

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
SIGNATURE_LIST = [SIG_ENEMY1, SIG_DEFAULT1, SIG_SELF1, SIG_BOUNDARY1]
TARGET_WEIGHT_MATRIX = [10., 10., 0., 0.]


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
    >>> ....example_bot.do_things()
    """

    SEARCH = 'search'
    """Looking for target while moving"""

    CHASE = 'chase'
    """Target acquired, go towards it"""

    FIRE = 'fire'
    """Stationary, shoot"""

    KILLED = 'killed'
    """Recently shot: stationary for short period"""
