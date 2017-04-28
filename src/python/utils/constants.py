import os

# Paths

ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '../../..'))
assert os.path.split(ROOT_DIR)[-1] == 'pixybattle'  # make sure the relative path works

# Interfaces

SERIAL_DEVICE = '/dev/ttyACM0'
BAUD_RATE = 9600

# Robot

MAX_MOTOR_SPEED = 480

DEADBAND_PPN = 0.05