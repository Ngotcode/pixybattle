
import time
import sys
import signal
import ctypes
import math
import serial
from datetime import datetime
from pololu_drv8835_rpi import motors

serial_device = '/dev/ttyACM0'
baud_rate = 9600

while True:
    try:
        ser = serial.Serial(serial_device, baud_rate)
        break
    except:
        print "Could not open serial device {}".format(serial_device)
        time.sleep(10)

MAX_MOTOR_SPEED = 1000  # 480
MIN_MOTOR_SPEED = -480

run_flag = 1

# 20ms time interval for 50Hz
dt = 20
# check timeout dt*3
timeout = 0.5
current_time = datetime.now()
last_time = datetime.now()


# defining motor function variables
# 5% drive is deadband
deadband = 0.05 * MAX_MOTOR_SPEED
# total_drive is the total power available
total_drive = MAX_MOTOR_SPEED
# throttle is how much of the total_drive to use [0~1]
throttle = 0.7
# differential drive level [0~1]
# this is the drive level allocated for steering [0~1] dynamically modulate
diff_drive = 0.3
# this is the gain for scaling diff_drive
diff_gain = 1
# this ratio determines the steering [-1~1]
bias = 1
# this ratio determines the drive direction and magnitude [-1~1]
advance = 1
# this gain currently modulates the forward drive enhancement
drive_gain = 1
# body turning p-gain
h_pgain = 0.5
# body turning d-gain
h_dgain = 0


def handle_SIGINT(sig, frame):
    """
    Handle CTRL-C quit by setting run flag to false
    This will break out of main loop and let you close
    pixy gracefully
    """
    global run_flag
    run_flag = False


def setup():
    signal.signal(signal.SIGINT, handle_SIGINT)

killed = False


def loop():
    """
    Main loop, Gets blocks from pixy, analyzes target location,
    chooses action for robot and sends instruction to motors
    """
    global throttle, diff_drive, diff_gain, bias, advance, turn_error, current_time, last_time, object_dist, dist_error, pan_error_prev, dist_error_prev, pan_loop, killed

    if ser.in_waiting:
        print("reading line from serial..")
        code = ser.readline().rstrip()
        print("Got IR code {}".format(code))
        killed = True

    if killed:
        motors.setSpeeds(0, 0)
        time.sleep(5)

    current_time = datetime.now()
    #drive()
    motors.setSpeeds(int(-MAX_MOTOR_SPEED/2), int(MAX_MOTOR_SPEED/2))
    return run_flag


def drive():
    # syn_drive is the drive level for going forward or backward (for both
    # wheels)
    syn_drive = advance * (1 - diff_drive) * throttle * total_drive
    left_diff = bias * diff_drive * throttle * total_drive
    right_diff = -bias * diff_drive * throttle * total_drive

    # construct the drive levels
    l_drive = (syn_drive + left_diff)
    r_drive = (syn_drive + right_diff)

    # Make sure that it is outside dead band and less than the max
    if l_drive > deadband:
        if l_drive > MAX_MOTOR_SPEED:
            l_drive = MAX_MOTOR_SPEED
    elif l_drive < -deadband:
        if l_drive < -MAX_MOTOR_SPEED:
            l_drive = -MAX_MOTOR_SPEED
    else:
        l_drive = 0

    if r_drive > deadband:
        if r_drive > MAX_MOTOR_SPEED:
            r_drive = MAX_MOTOR_SPEED
    elif r_drive < -deadband:
        if r_drive < -MAX_MOTOR_SPEED:
            r_drive = -MAX_MOTOR_SPEED
    else:
        r_drive = 0

    # Actually Set the motors
    motors.setSpeeds(int(l_drive), int(r_drive))


if __name__ == '__main__':
    try:
        setup()
        while True:
            ok = loop()
            if not ok:
                break
    finally:
        motors.setSpeeds(0, 0)
        print("Robot Shutdown Completed")
