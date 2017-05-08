import os
from enum import Enum


# PATHS

ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '../../..'))
assert os.path.split(ROOT_DIR)[-1] == 'pixybattle'  # make sure the relative path works


# MOTOR CONSTANTS
MAX_MOTOR_SPEED = 480

# CAMERA CONSTANTS
PIXY_RCS_PAN_CHANNEL = 0

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

    IDLE = 'idle'
    """Stationary, non-scanning, will not change unless state is changed"""

    SEARCH = 'search'
    """Looking for target while moving"""

    APPROACH = 'approach'
    """Target acquired, go towards it while firing"""

    PAN = 'pan'
    """Stationary, panning camera"""

    KILLED = 'killed'
    """Recently shot: stationary for short period"""

    PANIC = 'panic'
    """Everything has gone wrong, spin around and shoot"""
