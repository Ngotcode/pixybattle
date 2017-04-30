import math

# pixel to visual angle conversion factor (only rough approximation)
# (pixyViewV/pixyImgV + pixyViewH/pixyImgH) / 2
pix2ang_factor = 0.117
# reference object one is the pink earplug (~12mm wide)
ref_size1 = 12

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


def calculate_distance(block):
    """
    calculate distance to teh object
    :param block: detected block
    :return: object_dist
    """
    object_dist = ref_size1 / (2 * math.tan(math.radians(block.width * pix2ang_factor)))
    return object_dist


def calculate_pan_error(block):
    """
    calculate pan error of the block
    :param block: detected block
    :return: pan_error
    """
    pan_error = PIXY_X_CENTER - block.x
    return pan_error
