#!/usr/bin/env python
import time
import sys
import signal
import ctypes
import math
from datetime import datetime
import logging
from argparse import ArgumentParser
import serial
import numpy as np
from pololu_drv8835_rpi import motors
from pixy import pixy
import search
from utils.robot_state import RobotState
from utils.constants import *  #  SIG_BOUNDARY1, DEFAULT_LOG_LEVEL
from utils.bot_logging import set_log_level, Tweeter, ImageLogger
from utils.shooting import LaserController
from utils.scan_scene import scan_scene
from utils.vision import PixyBlock

serial_device = '/dev/ttyACM0'
baudRate = 9600

tweeter = Tweeter()
image_logger = ImageLogger(__name__)

while True:
    try:
        ser = serial.Serial(serial_device, baudRate)
        break
    except:
        print "Could not open serial device {}".format(serial_device)
        time.sleep(10)

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

# defining PixyCam motor variables
PIXY_RCS_PAN_CHANNEL = 0
PIXY_RCS_TILT_CHANNEL = 1

PAN_PROPORTIONAL_GAIN = 400
PAN_DERIVATIVE_GAIN = 300
TILT_PROPORTIONAL_GAIN = 500
TILT_DERIVATIVE_GAIN = 400

MAX_MOTOR_SPEED = 480  # 480
MIN_MOTOR_SPEED = -480

run_flag = 1

# 20ms time interval for 50Hz
dt = 20
# check timeout dt*3
timeout = 0.5
# (pixyViewV/pixyImgV + pixyViewH/pixyImgH) / 2
pix2ang_factor = 0.117
# reference object one
ref_size1 = 100
# reference object two is side post (~50mm tall)
ref_size2 = 50
# this is the distance estimation of an object
object_dist = 0
# this is some desired distance to keep (mm)
target_dist = 1
# reference distance; some fix distance to compare the object distance with
ref_dist = 400

blocks = None
do_pan = 1

def handle_SIGINT(sig, frame):
    """
    Handle CTRL-C quit by setting run flag to false
    This will break out of main loop and let you close
    pixy gracefully
    """
    global run_flag
    run_flag = False


class Blocks(ctypes.Structure):
    """
    Block structure for use with getting blocks from
    pixy.get_blocks()
    """
    _fields_ = [
        ("type", ctypes.c_uint),
        ("signature", ctypes.c_uint),
        ("x", ctypes.c_uint),
        ("y", ctypes.c_uint),
        ("width", ctypes.c_uint),
        ("height", ctypes.c_uint),
        ("angle", ctypes.c_uint)
    ]


class ServoLoop(object):
    """
    Loop to set pixy pan position
    """

    def __init__(self, pgain, dgain):
        self.m_pos = PIXY_RCS_CENTER_POS
        self.m_prev_error = 0x80000000
        self.m_pgain = pgain
        self.m_dgain = dgain

    def update(self, error):
        if self.m_prev_error != 0x80000000:
            vel = (error * self.m_pgain +
                   (error - self.m_prev_error) * self.m_dgain) >> 10
            self.m_pos += vel
            if self.m_pos > PIXY_RCS_MAX_POS:
                self.m_pos = PIXY_RCS_MAX_POS
            elif self.m_pos < PIXY_RCS_MIN_POS:
                self.m_pos = PIXY_RCS_MIN_POS
        self.m_prev_error = error

# define pan loop
pan_loop = ServoLoop(300, 500)


def setup():
    """
    One time setup. Inialize pixy and set sigint handler
    """
    tweeter = Tweeter()
    tweeter.tweet_canned(Situation.STARTING_UP, TWEET_DEFAULT_PROB)
    # global blocks
    pixy_init_status = pixy.pixy_init()
    if pixy_init_status != 0:
        print 'Error: pixy_init() [%d] ' % pixy_init_status
        pixy.pixy_error(pixy_init_status)
        return
    else:
        print "Pixy setup OK"
    blocks = pixy.BlockArray(BLOCK_BUFFER_SIZE)
    signal.signal(signal.SIGINT, handle_SIGINT)
    robot_state = RobotState(blocks, datetime.now(), MAX_MOTOR_SPEED)
    return robot_state

# killed = False

def compute_dist_error(block):
    object_dist = ref_size1 / (2 * math.tan(math.radians(block.height * pix2ang_factor)))
    dist_error = object_dist - target_dist
    return dist_error

def bias_computation(robot_state, dt, pan_loop):
    # should be still int32_t
    signed_turn_error = PIXY_RCS_CENTER_POS - pan_loop.m_pos
    turn_error = np.abs(signed_turn_error)
    if dt == 0:
        dt += 1e-5
    ud = robot_state.h_dgain * float(turn_error - robot_state.previous_turn_error)/dt
    robot_state.previous_turn_error = turn_error
    # >0 is turning left; currently only p-control is implemented
    robot_state.bias = np.sign(signed_turn_error) * float(turn_error + ud) / float(PIXY_RCS_CENTER_POS) * robot_state.h_pgain

def logit(x, k, x0):
    return (1 + np.exp(-k * (x - x0)))**(-1)

def drive_toward_block(robot_state, block):
    pan_error = PIXY_X_CENTER - block.x
    robot_state.throttle = 0.5
    # amount of steering depends on how much deviation is there
    robot_state.diff_drive = abs(float(pan_error) / 300+.4)
    dist_error = compute_dist_error(block)
    # this is in float format with sign indicating advancing or retreating
    robot_state.advance = logit(dist_error, .025, 400)
    # float(dist_error) / ref_dist
    # print float(dist_error) / ref_dist
    #print 'dist_error:%f, ref_dist:%f, object_dist:%f, target_dist:%f'%(dist_error, ref_dist, object_dist, target_dist)
    return pan_error

def loop(robot_state):
    """
    Main loop, Gets blocks from pixy, analyzes target location,
    chooses action for robot and sends instruction to motors
    """

    tweeter = Tweeter()
    if ser.in_waiting:
        print("Reading line from serial..")
        code = ser.readline().rstrip()
        print("Got IR code {}".format(code))
        robot_state.killed = True

    if robot_state.killed:
        print "I'm hit!"
        tweeter.tweet_canned(Situation.RECEIVED_HIT, TWEET_HIT_PROB)

    robot_state.current_time = datetime.now()

    # If no new blocks, don't do anything
    while not pixy.pixy_blocks_are_new() and run_flag:
        # print PixyBlock.from_pixy(), 'test'
        pass
    # while pixy.pixy_blocks_are_new()  and run_flag:
    #     pass

    count = 0
    if robot_state.state == "search":
        ## /!\ WE MIGHT WANT TO ROTATE FIRST /!\

        ## Look for Enemy target; if found go to chase state, else turn
        block = scan_scene("chase")
        if time.time() - robot_state.search_starting_time >= robot_state.min_turning_time:
            if block is not None:
                robot_state.state = "chase"
                print 'search to chase'
                tweeter.tweet_canned(Situation.CHASE, TWEET_CHASE_PROB)

            else:
            ## If enough turn for enough time go to roam state
                if time.time() - robot_state.search_starting_time > robot_state.max_turning_time:
                    robot_state.state = "roam"
                    print 'search to roam'
                    tweeter.tweet_canned(Situation.RANDOM, TWEET_ROAM_PROB)
                else:
                    motors.setSpeeds(int( robot_state.turn_direction * .2 * MAX_MOTOR_SPEED),
                                     int(-robot_state.turn_direction * .2 * MAX_MOTOR_SPEED))
        else:
            motors.setSpeeds(int( robot_state.turn_direction * .2 * MAX_MOTOR_SPEED),
                             int(-robot_state.turn_direction * .2 * MAX_MOTOR_SPEED))

    elif robot_state.state == "chase":
        ## Look for Enemy target; if none found go to roam state
        block = scan_scene("chase")
        if block is None:
            print block
            robot_state.state = "roam"
            print "chase to roam"
            tweeter.tweet_canned(Situation.RANDOM, TWEET_ROAM_PROB)
        else: # count > 0:
            pan_error = drive_toward_block(robot_state, block)
            pan_loop.update(pan_error)

            # Update pixy's pan position
            pixy.pixy_rcs_set_position(PIXY_RCS_PAN_CHANNEL, pan_loop.m_pos)

            # if Pixy sees nothing recognizable, don't move.
            time_difference = robot_state.current_time - robot_state.previous_time
            if time_difference.total_seconds() >= timeout:
                throttle = 0.0
                diff_drive = 1

            dt = (robot_state.current_time - robot_state.previous_time).total_seconds()
            bias_computation(robot_state, dt, pan_loop)
            robot_state.previous_time = robot_state.current_time
            l_drive, r_drive = drive(robot_state)
            if robot_state.advance < .5:
                robot_state.switch_to_search()
                motors.setSpeeds(int( robot_state.turn_direction * .2 * MAX_MOTOR_SPEED),
                                 int(-robot_state.turn_direction * .2 * MAX_MOTOR_SPEED))
                print 'chase to search'
                tweeter.tweet_canned(Situation.SEARCH, TWEET_SEARCH_PROB)

    elif robot_state.state == "roam":
        # First, see if there is a shootable target
        block = scan_scene("chase")
        if block is not None:
            robot_state.state = "chase"
            print 'roam to chase'
            tweeter.tweet_canned(Situation.CHASE, TWEET_CHASE_PROB)
            # return run_flag
        else:
            # else, we are still in roam mode
            block = scan_scene("roam")
            if block is not None:
                if block.signature != SIG_BOUNDARY1:
                    dist_error = compute_dist_error(block)
                    robot_state.throttle = 0.8
                    robot_state.diff_drive = 0 #abs(float(pan_error) / 300+.4)
                    robot_state.advance = logit(dist_error, .025, 400)
                    if robot_state.advance < .05:
                        robot_state.switch_to_search()
                        print 'roam to search'
                        tweeter.tweet_canned(Situation.SEARCH, TWEET_SEARCH_PROB)
                    else:
                        l_drive, r_drive = drive(robot_state)
                else:
                    robot_state.switch_to_search()
                    motors.setSpeeds(0, 0)
                    print 'roam to search from wall'
                    tweeter.tweet_canned(Situation.WALL, TWEET_WALL_PROB)
            else:
                robot_state.advance = .9
                l_drive, r_drive = drive(robot_state)
    return run_flag


def drive(robot_state):
    # syn_drive is the drive level for going forward or backward (for both
    # wheels)
    syn_drive = robot_state.advance * (1 - robot_state.diff_drive) * robot_state.throttle * robot_state.total_drive
    left_diff = robot_state.bias * robot_state.diff_drive * robot_state.throttle * robot_state.total_drive
    right_diff = -robot_state.bias * robot_state.diff_drive * robot_state.throttle * robot_state.total_drive

    # construct the drive levels
    l_drive = (syn_drive + left_diff)
    r_drive = (syn_drive + right_diff)

    # Make sure that it is outside dead band and less than the max
    if l_drive > robot_state.deadband:
        if l_drive > MAX_MOTOR_SPEED:
            l_drive = MAX_MOTOR_SPEED
    elif l_drive < -robot_state.deadband:
        if l_drive < -MAX_MOTOR_SPEED:
            l_drive = -MAX_MOTOR_SPEED
    else:
        l_drive = 0

    if r_drive > robot_state.deadband:
        if r_drive > MAX_MOTOR_SPEED:
            r_drive = MAX_MOTOR_SPEED
    elif r_drive < -robot_state.deadband:
        if r_drive < -MAX_MOTOR_SPEED:
            r_drive = -MAX_MOTOR_SPEED
    else:
        r_drive = 0

    # Actually Set the motors
    motors.setSpeeds(int(l_drive), int(r_drive))
    return int(l_drive), int(r_drive)

if __name__ == '__main__':
    set_log_level(DEFAULT_LOG_LEVEL)
    parser = ArgumentParser(description='Start the robot in laser death mode!')
    parser.add_argument(
        '--skip-prewarm', '-s', action='store_true', default=False,
        help="Go straight from the prewarm into the robot behaving, rather than waiting for user input."
    )
    parser.add_argument(
        '--verbosity', '-v', action='count', default=0,
        help='Increase verbosity of command line logging (1 for info, 2 for debug, 3 for everything)'
    )

    parsed_args = parser.parse_args()

    if parsed_args.verbosity >= 3:
        set_log_level(logging.NOTSET)
    elif parsed_args.verbosity == 2:
        set_log_level(logging.DEBUG)
    elif parsed_args.verbosity == 1:
        set_log_level(logging.INFO)

    try:
        # pixy.pixy_cam_set_brightness(20)
        robot_state = setup()
        with LaserController() as controller:
            if not parsed_args.skip_prewarm:
                input('Press enter to GO!')
            controller.fire_at_will()
            while True:
                ok = loop(robot_state)
                if not ok:
                    break
    finally:
        pixy.pixy_close()
        motors.setSpeeds(0, 0)
        print("Robot Shutdown Completed")
