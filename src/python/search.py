"""Search algorithms for pixybattle."""
import numpy as np
import time
from utils.scan_scene import scan_scene


def simple_search(robot_state, motors, do_pan):
    """Simple search.

    This search will pick a random direction and move towards that direction
    for a random amount of time. It will not do any attempts to verify that
    the robot is properly moving towards the chosen directions (ie no PD loop
    corrections).
    """
    block = scan_scene(robot_state.blocks, do_pan)
    if block is not None:
        print "Target found!"
        return block
    # First, rotate the robot
    rand_sec = np.random.random([1])[0] * 1
    print "Rotating for %f seconds." % rand_sec
    motors.setSpeeds(int(-100), int(100))
    time.sleep(rand_sec)
    motors.setSpeeds(0, 0)
    # time.sleep(10)

    block = scan_scene(robot_state.blocks, do_pan)
    if block is not None:
        print "Target found!"
        search = False
    else:
        print "Target not found!"
        rand_sec = np.random.random([1])[0] * 1
        print "Forward for %f seconds." % rand_sec
        motors.setSpeeds(int(200), int(200))
        time.sleep(rand_sec)
        motors.setSpeeds(0, 0)

    # Is the only way to get to this point if block is not None?
    return block


def _pan_debug():
    """Debug camera pan/search function.

    Debug code that simulates the camera pan search code. Randomly returns a
    "block list"
    """
    # The probability 
    block_prob = 0.5
    if np.random.rand(1)[0] > block_prob:
        # return a fake block list.
        return ["some", "stuff", "here"]
    else:
        # return nothing
        return None


def _test_search():
    """Test the search function."""
    for i in range(10):
        print "Search State iter: %i" % i
        simple_search()


if __name__ == "__main__":
    # If run standalone, do some testing.
    _test_search()
