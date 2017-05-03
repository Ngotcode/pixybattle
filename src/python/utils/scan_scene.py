
from pixy import pixy
import sys
import numpy as np
from utils.constants import *
import time


def scan_scene(blocks):
    """
    loop when in searching state. Detect objects in the scene, return one of the following states:
    1 = Object detected: return a list of blocks
    0 = Object not detected: nothing detected even if camera panned for the full range
    TODO: global variable "blocks" and constants not included in this function
    """
    # detect objects in the scene
    # pixy.pixy_rcs_set_position(PIXY_RCS_PAN_CHANNEL, 0)
    count = pixy.pixy_get_blocks(BLOCK_BUFFER_SIZE, blocks)
    if count>=0:
        for n_count in range(0, count+1):
            print(blocks[n_count].signature)
    time.sleep(3)
    return(blocks[0])
    
    # pixy.pixy_rcs_set_position(PIXY_RCS_PAN_CHANNEL, 250)
    # count_read = pixy.pixy_get_blocks(BLOCK_BUFFER_SIZE, blocks)
    # count = count_read
    # print count
    # time.sleep(3)
    
    # pixy.pixy_rcs_set_position(PIXY_RCS_PAN_CHANNEL, 500)
    # count_read = pixy.pixy_get_blocks(BLOCK_BUFFER_SIZE, blocks)
    # count = count_read
    # print count
    # time.sleep(3)
    
    # pixy.pixy_rcs_set_position(PIXY_RCS_PAN_CHANNEL, 750)
    # count_read = pixy.pixy_get_blocks(BLOCK_BUFFER_SIZE, blocks)
    # count = count_read
    # print count
    # time.sleep(3)
    
    # pixy.pixy_rcs_set_position(PIXY_RCS_PAN_CHANNEL, 1000)
    # count_read = pixy.pixy_get_blocks(BLOCK_BUFFER_SIZE, blocks)
    # count = count_read
    # print count
    # time.sleep(3)
    
    # # need some filtering of blocks here
    # count = count_read
    # print count

    # return
    # # If negative blocks, something went wrong
    # if count < 0:
    #     print 'Error: pixy_get_blocks() [%d] ' % count
    #     pixy.pixy_error(count)
    #     sys.exit(1)
    # # If no object detected, pan camera until something is found
    # elif count == 0:
    #     # pan from near end to far end
    #     steps = 4
    #     m_pos = pixy.pixy_rcs_get_position(PIXY_RCS_PAN_CHANNEL)
    #     pos_range = np.linspace(PIXY_RCS_MIN_POS, PIXY_RCS_MAX_POS, num=steps)
    #     pos_range = np.fliplr(pos_range) if m_pos > PIXY_RCS_CENTER_POS else pos_range
    #     for pos in pos_range:
    #         pos = int(pos)
    #         pixy.pixy_rcs_set_position(PIXY_RCS_PAN_CHANNEL, pos)
    #         count = pixy.pixy_get_blocks(BLOCK_BUFFER_SIZE, blocks)
    #         if count > 0:
    #             return 1
    #     # if nothing found, set camera to center and return 0
    #     pixy.pixy_rcs_set_position(PIXY_RCS_PAN_CHANNEL, PIXY_RCS_CENTER_POS)
    #     return blocks
    # # if more than one block
    # # Check which the largest block's signature and either do target chasing or
    # # line following
    # elif count > 0:
    #     return blocks
