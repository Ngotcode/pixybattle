import os


ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '../../..'))
assert os.path.split(ROOT_DIR)[-1] == 'pixybattle'  # make sure the relative path works


# MOTOR CONSTANTS
MAX_MOTOR_SPEED = 480

# CAMERA CONSTANTS
PIXY_RCS_PAN_CHANNEL = 0