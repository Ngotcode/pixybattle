
from pixy import pixy
import sys


def scan_scene():
    """
    loop when in searching state. Detect objects in the scene, return one of the following states:
    1 = Object detected: return a list of blocks
    0 = Object not detected: nothing detected even if camera panned for the full range
    TODO: global variable "blocks" and constants not included in this function
    """
    # detect objects in the scene
    count_read = pixy.pixy_get_blocks(BLOCK_BUFFER_SIZE, blocks)
    # need some filtering of blocks here
    count = count_read

    # If negative blocks, something went wrong
    if count < 0:
        print 'Error: pixy_get_blocks() [%d] ' % count
        pixy.pixy_error(count)
        sys.exit(1)
    # If no object detected, pan camera until something is found
    elif count == 0:
        # look to the near end
        m_pos = pixy.pixy_rcs_get_position(PIXY_RCS_PAN_CHANNEL)
        near_end = PIXY_RCS_MIN_POS if m_pos < PIXY_RCS_CENTER_POS else PIXY_RCS_MAX_POS
        pixy.pixy_rcs_set_position(PIXY_RCS_PAN_CHANNEL, near_end)
        count = pixy.pixy_get_blocks(BLOCK_BUFFER_SIZE, blocks)
        if count > 0:
            return 1
        else:
            # look to the far end
            far_end = PIXY_RCS_MAX_POS if m_pos < PIXY_RCS_CENTER_POS else PIXY_RCS_MIN_POS
            pixy.pixy_rcs_set_position(PIXY_RCS_PAN_CHANNEL, far_end)
            count = pixy.pixy_get_blocks(BLOCK_BUFFER_SIZE, blocks)
            if count > 0:
                return 1
            else:
                pixy.pixy_rcs_set_position(PIXY_RCS_PAN_CHANNEL, PIXY_RCS_CENTER_POS)
                return 0
    # if more than one block
    # Check which the largest block's signature and either do target chasing or
    # line following
    elif count > 0:
        return 1


