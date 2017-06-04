# from __future__ import division
from pixy import pixy
import sys
from utils.constants import *
import time
from utils.vision import PixyBlock, Scene

ratio_thres = 500
wait_time = 0
step_size = 1


def print_block_info(blocks):
    for block in blocks:
        print(str(block))


def search_max_blocks(signature, blocks):
    for n_count in range(len(blocks)):
        if blocks[n_count].signature == signature and valid_block(blocks[n_count]):
            return blocks[n_count]
    return None


# check if the block is valid in search area
# later decision
def valid_block(block):
    return block.height <= (ratio_thres * block.width)


def area(block):
    if block is None:
        return 0
    return block.width * block.height


def area_with_weight(block, weight):
    return area(block) * weight


def find_max_block_in_scene(blocks, signatures, weights):
    best_block = None
    max_area = 0
    for sig, weight in zip(signatures, weights):
        current_block = search_max_blocks(sig, blocks)
        weighted_area = area_with_weight(current_block, weight)
        if weighted_area > max_area:
            best_block = current_block
            max_area = weighted_area
    return best_block, max_area


def scan_scene(do_pan):
    """
    loop when in searching state. Detect objects in the scene, return one of the following states:
    1 = Object detected: return a list of blocks
    0 = Object not detected: nothing detected even if camera panned for the full range
    TODO: global variable "blocks" and constants not included in this function
    """
    # detect objects in the scene
    # block_with_signature = [None, None]
    tar_pan_view = -1
    tar_area = 0
    tar_block = None


    if do_pan == 'search':
        for pan_view in range(0, 1000, step_size):
            # print(pan_view)
            pixy.pixy_rcs_set_position(PIXY_RCS_PAN_CHANNEL, pan_view)
            time.sleep(wait_time)
            blocks = PixyBlock.from_pixy()
            # print_block_info(blocks)
            block, max_area_pan = find_max_block_in_scene(blocks, SIGNATURE_LIST, TARGET_WEIGHT_MATRIX)
            if tar_area < max_area_pan:
                tar_area = max_area_pan
                tar_block = block
                tar_pan_view = pan_view

        # print(tar_pan_view)
        if tar_pan_view < 0:
            tar_pan_view = PIXY_RCS_CENTER_POS
        pixy.pixy_rcs_set_position(PIXY_RCS_PAN_CHANNEL, tar_pan_view)
    elif do_pan == "chase":
        blocks = PixyBlock.from_pixy()
        tar_block, _ = find_max_block_in_scene(blocks, SIGNATURE_LIST, TARGET_WEIGHT_MATRIX)
    elif do_pan == "roam":
        blocks = PixyBlock.from_pixy()
        if len(blocks) > 0:
            tar_block = blocks[0]
        else:
            tar_block = None
            

    # print_block_info([tar_block])
    return tar_block
