# from __future__ import division
from pixy import pixy
import sys
from utils.constants import *
import time
import utils.vision import PixyBlock, Scene

ratio_thres = 500
wait_time = 0
step_size = 1


def print_block_info(blocks, count):
    if count > 0:
        for index in range(0, count):
            print '[BLOCK_TYPE=%d SIG=%d X=%3d Y=%3d WIDTH=%3d HEIGHT=%3d ANGLE=%3d]' % (blocks[index].type, blocks[index].signature, blocks[index].x, blocks[index].y, blocks[index].width, blocks[index].height, blocks[index].angle)


def search_max_blocks(signature, blocks, count):
    for n_count in range(count):
        if blocks[n_count].signature == signature and valid_block(blocks[n_count]):
            return blocks[n_count]
    return None


# check if the block is valid in search area
# later decision
def valid_block(block):
    return block.height <= (ratio_thres * block.width)


def area(block):
    return block.width * block.height



def scan_scene(blocks, do_pan):
    """
    loop when in searching state. Detect objects in the scene, return one of the following states:
    1 = Object detected: return a list of blocks
    0 = Object not detected: nothing detected even if camera panned for the full range
    TODO: global variable "blocks" and constants not included in this function
    """
    # detect objects in the scene
    block_with_signature = [None, None]
    tar_pan_view = -1
    area_list = [0, 0]
    target_signature = 1

    self_signature = 2  # save for future

    if do_pan:
        for pan_view in range(0, 1000, step_size):
            # print(pan_view)
            pixy.pixy_rcs_set_position(PIXY_RCS_PAN_CHANNEL, pan_view)
            time.sleep(wait_time)
            blocks = PixyBlock.from_pixy()
            count = len(blocks)
            if count > 0:
                # print_block_info(blocks, count)
                block = search_max_blocks(target_signature, blocks, count)
                # conflict point
                if block is None:
                    continue
                if area_list[target_signature - 1] < area(block):
                    block_with_signature[target_signature - 1] = block
                    area_list[target_signature - 1] = area(block)
                    tar_pan_view = pan_view
        # print(tar_pan_view)
        if tar_pan_view < 0:
            tar_pan_view = PIXY_RCS_CENTER_POS
        pixy.pixy_rcs_set_position(PIXY_RCS_PAN_CHANNEL, tar_pan_view)
    else:
            count = pixy.pixy_get_blocks(BLOCK_BUFFER_SIZE, blocks)
            if count < 0:
                print 'Error: pixy_get_blocks() [%d] ' % count
                pixy.pixy_error(count)
                sys.exit(1)
            else:
                if count > 0:
                    # print_block_info(blocks, count)
                    block_with_signature[0] = search_max_blocks(target_signature, blocks, count)

    return block_with_signature[0]
