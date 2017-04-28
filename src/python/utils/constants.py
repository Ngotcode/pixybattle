import os
from enum import Enum


# PATHS

ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '../../..'))
assert os.path.split(ROOT_DIR)[-1] == 'pixybattle'  # make sure the relative path works


# STATES

class State(Enum):
    """
    Definition of robot's states (here for consistency). Add states where required. Integer values are meaningless, 
    they just need to be different.
    
    Examples
    --------
    Fictitious robot API for demonstrative purposes
    >>> example_bot.set_state(State.SEARCH)
    >>> if example_bot.state == State.SEARCH:
    >>> ....example_bot.do_things()
    """

    """Normal behaviour when looking for target"""
    SEARCH = 0

    """Target acquired, go towards it while firing"""
    APPROACH = 1

    """Everything has gone wrong, spin around and shoot"""
    PANIC = 2
