"""Search algorithms for pixybattle."""
import numpy as np
import time
# from pololu_drv8835_rpi import motors


def simple_search():
    """Simple search.

    This search will pick a random direction and move towards that direction
    for a random amount of time. It will not do any attempts to verify that
    the robot is properly moving towards the chosen directions (ie no PD loop
    corrections).
    """
    # loop until the search state is finished.
    search = True
    while search is True:
        # first query the camera
        blocks = _pan_debug()
        if blocks is not None:
            print "Targets found, acquire!!"
            # We found potential targets. Options here... call the target code
            # or just exit the loop and assume the targeting will be done
            # outside the search state.
            search = False
        else:
            print "No targets found... act lost"
            # No potential targets. Pick a random direction.
            # ... this is not the right way to do it. For now just spin for a
            # random number of iterations.
            rand_iter = np.random.randint(1,20)
            for i in range(rand_iter):
                # Always spin one direction? Ideally we'd pick an angle and
                # drive towards it.
                # motors.setSpeeds(-1, 1)
                print "\tmotors.setSpeeds(-1, 1)"
            # after spinning, go forward
            rand_iter = np.random.randint(1,20)
            for i in range(rand_iter):
                # Always spin one direction? Ideally we'd pick an angle and
                # drive towards it.
                # motors.setSpeeds(-1, 1)
                print "\tmotors.setSpeeds(1, 1)"

    
    # Is the only way to get to this point if blocks is not None?
    return blocks


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