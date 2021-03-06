
import sys
import signal
import pixy
import ctypes
import time
from datetime import datetime
import rrb3


PIXY_MIN_X = 0
PIXY_MAX_X = 319
PIXY_MIN_Y = 0
PIXY_MAX_Y = 199

PIXY_X_CENTER = ((PIXY_MAX_X - PIXY_MIN_X) / 2)
PIXY_Y_CENTER = ((PIXY_MAX_Y - PIXY_MIN_Y) / 2)
PIXY_RCS_MIN_POS = 0
PIXY_RCS_MAX_POS = 1000
PIXY_RCS_CENTER_POS = ((PIXY_RCS_MAX_POS - PIXY_RCS_MIN_POS) / 2)

PIXY_RCS_PAN_CHANNEL = 0
PIXY_RCS_TILT_CHANNEL = 1

PAN_PROPORTIONAL_GAIN = 400
PAN_DERIVATIVE_GAIN = 300
TILT_PROPORTIONAL_GAIN = 500
TILT_DERIVATIVE_GAIN = 400

BLOCK_BUFFER_SIZE = 10

DRIVE_CONVERSION_FACTOR = 0.01
MAX_MOTOR_SPEED = 1.0
MIN_MOTOR_SPEED = 0
MOTOR_FORWARD = 0
MOTOR_REVERSE = 1
run_flag = 1


# TODO implement timeout?
# 20ms time interval for 50Hz
dt = 20
# check timeout
timeout = dt * 3
current_time = datetime.now()
last_time = datetime.now()


# 5% drive is deadband
deadband = 0.05
# initialize the left wheel state
l_drive = 0
# initialize the right wheel state
r_drive = 0
# synchronous drive level
syn_drive = 0
# this is the total drive level [-100~100] abs(throttle)<30 doesn't do much
throttle = 0
# this gain currently modulates the forward drive enhancement
drive_gain = 3
# this ratio determines the differential drive [0~1]
bias = 0.5
# this is the drive level allocated for turning [0~1] dynamically modulate
diff_gain = 0
#  body turning gain
h_pgain = 0.5
# body turning gain
h_dgain = 0
# distance tracking target size: 16cm for orange cone width
target_size = 20
target_size2 = 10
rr = rrb3.RRB3(9, 6)

blocks = None


def handle_SIGINT(signal, frame):
    global run_flag
    run_flag = False


class Blocks (ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_uint),
        ("signature", ctypes.c_uint),
        ("x", ctypes.c_uint),
        ("y", ctypes.c_uint),
        ("width", ctypes.c_uint),
        ("height", ctypes.c_uint),
        ("angle", ctypes.c_uint)
    ]


class ServoLoop (object):

    def __init__(self, pgain, dgain):
        self.m_pos = PIXY_RCS_CENTER_POS
        self.m_prevError = 0x80000000
        self.m_pgain = pgain
        self.m_dgain = dgain

    def update(self, error):
        if (self.m_prevError != 0x80000000):
            vel = (error * self.m_pgain +
                   (error - self.m_prevError) * self.m_dgain) >> 10
            self.m_pos += vel
            if (self.m_pos > PIXY_RCS_MAX_POS):
                self.m_pos = PIXY_RCS_MAX_POS
            elif (self.m_pos < PIXY_RCS_MIN_POS):
                self.m_pos = PIXY_RCS_MIN_POS
        self.m_prevError = error

# define objects
pan_loop = ServoLoop(300, 500)
tilt_loop = ServoLoop(500, 700)


def setup():
    global blocks
    # Serial.begin(9600)
    pixy_init_status = pixy.pixy_init()
    if pixy_init_status != 0:
        print 'Error: pixy_init() [%d] ' % pixy_init_status
        pixy_error(pixy_init_status)
        return
    else:
        print "Pixy setup OK"
    rr.set_motors(0, 0, 0, 0)
    blocks = pixy.BlockArray(BLOCK_BUFFER_SIZE)
    signal.signal(signal.SIGINT, handle_SIGINT)
    rr.set_led1(1)
    time.sleep(0.1)
    rr.set_led1(0)
    rr.set_led2(1)
    time.sleep(0.1)
    rr.set_led2(0)


def loop():
    global blocks, throttle, diff_gain, bias, current_time, last_time
    # TODO python equivilant?
    current_time = datetime.now()
    while not pixy.pixy_blocks_are_new() and run_flag:
        pass
    count = pixy.pixy_get_blocks(BLOCK_BUFFER_SIZE, blocks)
    if count < 0:
        print 'Error: pixy_get_blocks() [%d] ' % count
        pixy.pixy_error(count)
        sys.exit(1)
    if count > 0:
        last_time = current_time
        # if the largest block is the object to pursue, then prioritize this
        # behavior
        if (blocks[0].signature == 1):
            pan_error = PIXY_X_CENTER - blocks[0].x
            tilt_error = blocks[0].y - PIXY_Y_CENTER
            # the target is far and we must advance
            if (blocks[0].width < target_size):
                # charge forward
                throttle = 100  # charge forward
                dist_error = target_size - blocks[0].width
                # this is in float format
                diff_gain = 1 - drive_gain * float(dist_error) / target_size

            # the target is too close and we must back off
            elif (blocks[0].width > target_size):
                # retreat
                throttle = -100
                dist_error = blocks[0].width - target_size
                # this is in float format
                diff_gain = 1 - float(dist_error) / target_size

        # this is line following algorithm
        elif (blocks[0].signature == 2):
            pan_error = PIXY_X_CENTER - blocks[0].x
            tilt_error = blocks[0].y - PIXY_Y_CENTER
            # charge forward
            throttle = 100
            diff_gain = 0.3
        # if none of the blocks make sense, just pause
        else:
            pan_error = 0
            tilt_error = 0
            throttle = 0
            diff_gain = 1

        pan_loop.update(pan_error)
        tilt_loop.update(tilt_error)

    set_position_result = pixy.pixy_rcs_set_position(
        PIXY_RCS_PAN_CHANNEL, pan_loop.m_pos)
    set_position_result = pixy.pixy_rcs_set_position(
        PIXY_RCS_TILT_CHANNEL, tilt_loop.m_pos)

# TODO implement this?
    # if Pixy sees nothing recognizable, don't move.
    time_difference = current_time - last_time
    if (time_difference.total_seconds() >= timeout):
        print time_difference.total_seconds(), timeout
        throttle = 0
        diff_gain = 1

    # this is turning to left
    if (pan_loop.m_pos > PIXY_RCS_CENTER_POS):
        # should be still int32_t
        turnError = pan_loop.m_pos - PIXY_RCS_CENTER_POS
        # <0.5 is turning left
        bias = - float(turnError) / float(PIXY_RCS_CENTER_POS) * h_pgain
    # this is turning to right
    elif (pan_loop.m_pos < PIXY_RCS_CENTER_POS):
        # should be still int32_t
        turnError = PIXY_RCS_CENTER_POS - pan_loop.m_pos
        # <0.5 is turning left
        bias = float(turnError) / float(PIXY_RCS_CENTER_POS) * h_pgain
    drive()
    return run_flag


def drive():
    global throttle, diff_gain, bias
    # syn_drive is the drive level for going forward or backward (for both
    # wheels)
    syn_drive = 0.5 * throttle * (1 - diff_gain)
    # Drive range is 0 - 1 so convert from 0 - 100 value
    l_drive = (syn_drive + bias * diff_gain * abs(throttle)) * \
        DRIVE_CONVERSION_FACTOR
    r_drive = (syn_drive - bias * diff_gain * abs(throttle)) * \
        DRIVE_CONVERSION_FACTOR
    l_direction = MOTOR_FORWARD
    r_direction = MOTOR_FORWARD
    # Make sure that it is outside dead band and less than the max
    if (l_drive > deadband):
        l_direction = MOTOR_FORWARD
        if (l_drive > MAX_MOTOR_SPEED):
            l_drive = MAX_MOTOR_SPEED
    elif (l_drive < -deadband):
        l_direction = MOTOR_REVERSE
        l_drive = -l_drive
        if (l_drive > MAX_MOTOR_SPEED):
            l_drive = MAX_MOTOR_SPEED
    else:
        l_drive = 0
    if (r_drive > deadband):
        r_direction = MOTOR_FORWARD
        if (r_drive > MAX_MOTOR_SPEED):
            r_drive = MAX_MOTOR_SPEED
    elif (r_drive < -deadband):
        r_direction = MOTOR_REVERSE
        r_drive = -r_drive
        if (r_drive > MAX_MOTOR_SPEED):
            r_drive = MAX_MOTOR_SPEED
    else:
        r_drive = 0

    # Actually Set the motors
    rr.set_motors(l_drive, l_direction, r_drive, r_direction)


if __name__ == '__main__':
    setup()
    while(True):
        ok = loop()
        if not ok:
            break
    pixy.pixy_close()
