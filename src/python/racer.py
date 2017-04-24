import sys
import traceback
import signal
import ctypes
import math
import time
from datetime import datetime
import argparse

from pixy import pixy
from pololu_drv8835_rpi import motors

# Libraries for playing sound on the web service
import requests
import threading
from Queue import Queue

#VOICE_SERVICE_URL = "http://localhost:8080"
VOICE_SERVICE_URL = "http://10.9.6.2:8080"

BRIGHTNESS = 185

#### signature ids ####
OBSTACLE = 1
CENTER_LINE = 2
LEFT_LINE = 3
RIGHT_LINE = 4
L_POST = 5
R_POST = 6

##### defining PixyCam sensory variables
PIXY_MIN_X = 0
PIXY_MAX_X = 319
PIXY_MIN_Y = 0
PIXY_MAX_Y = 199

PIXY_X_CENTER = ((PIXY_MAX_X-PIXY_MIN_X) / 2)
PIXY_Y_CENTER = ((PIXY_MAX_Y-PIXY_MIN_Y) / 2)
PIXY_RCS_MIN_POS = 0
PIXY_RCS_MAX_POS = 1000
PIXY_RCS_CENTER_POS = ((PIXY_RCS_MAX_POS-PIXY_RCS_MIN_POS) / 2)
BLOCK_BUFFER_SIZE = 10

##### defining PixyCam motor variables
PIXY_RCS_PAN_CHANNEL = 0
PIXY_RCS_TILT_CHANNEL = 1

PAN_PROPORTIONAL_GAIN = 400
PAN_DERIVATIVE_GAIN = 300
TILT_PROPORTIONAL_GAIN = 500
TILT_DERIVATIVE_GAIN = 400

MAX_MOTOR_SPEED = 480
MIN_MOTOR_SPEED = -480

AVG_N = 3

run_flag = 1
first_pass = True
start_time = time.time()

# options that can be set by command-line arguments
no_brightness_check = True 
chatty = False
allow_move = True
finale = False

init_throttle = 1.0 #0.9
diff_drive_straight = 0.4 #0.6
diff_drive_posts = 0.5 #0.6

# 20ms time interval for 50Hz
dt = 20
# check timeout dt*3
timeout = 0.5
current_time = datetime.now()
last_time = datetime.now()


#### defining motor function variables
# 5% drive is deadband
deadband = 0.05 * MAX_MOTOR_SPEED
# total_drive is the total power available
total_drive = MAX_MOTOR_SPEED
# throttle is how much of the total_drive to use [0~1]
throttle = 0
# this is the drive level allocated for steering [0~1] dynamically modulate
diff_drive = 0
# this is the gain for scaling diff_drive
diff_gain = 1
# this ratio determines the steering [-1~1]
bias = 0
# this ratio determines the drive direction and magnitude [-1~1]
advance = 0
# this gain currently modulates the forward drive enhancement
drive_gain = 1
# body turning p-gain
h_pgain = 0.7
# body turning d-gain
h_dgain = 0.2

# turn error
turn_error = 0
# PID controller
pid_bias = 0
last_turn = 0

#### defining state estimation variables
# pixyViewV = 47
# pixyViewH = 75
# pixyImgV = 400
# pixyImgH = 640
# pixel to visual angle conversion factor (only rough approximation) (pixyViewV/pixyImgV + pixyViewH/pixyImgH) / 2
pix2ang_factor = 0.117
# reference object one is the pink earplug (~12mm wide)
refSize1 = 12
# reference object two is side post (~50mm tall)
refSize2 = 50
# this is the distance estimation of an object
object_dist = 0
# this is some desired distance to keep (mm)
target_dist = 100
# reference distance; some fix distance to compare the object distance with
refDist = 400

sayingQueue = Queue()


def say_now(saying):
    if not chatty:
        return
    try:
        if saying.startswith("SLEEP"):
            requests.get('{}/say?sleep={}'.format(VOICE_SERVICE_URL, saying.split()[1]))
        else:
            requests.get('{}/say?text={}'.format(VOICE_SERVICE_URL, saying))
    except Exception, err:
        print "Couldn't send saying to voice server", err


def say(saying):
    print "Saying '{}'".format(saying)
    if not chatty:
        return
    sayingQueue.put(saying)


def voice_thread_loop():
    def web_say(saying):
        try:
            if saying.startswith("SLEEP"):
                requests.get('%s/say?sleep=%s' % (VOICE_SERVICE_URL, saying.split()[1]))
            else:
                requests.get('%s/say?text=%s' % (VOICE_SERVICE_URL, saying))
        except Exception, err:
            print "Couldn't send saying to voice server",err
    last_saying = None
    last_time = datetime.now()
    while True:
        saying = sayingQueue.get()
        current_time = datetime.now()
        time_difference = current_time - last_time
        if saying:
            if not(saying==last_saying) or time_difference.total_seconds() >= 3:
                web_say(saying)
                last_saying = saying
                last_time = current_time


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
        self.m_prev_rror = 0x80000000L
        self.m_pgain = pgain
        self.m_dgain = dgain

    def update(self, error):
        if self.m_prev_rror != 0x80000000:
            vel = (error * self.m_pgain + (error - self.m_prev_rror) * self.m_dgain) >> 10
            self.m_pos += vel
            if self.m_pos > PIXY_RCS_MAX_POS:
                self.m_pos = PIXY_RCS_MAX_POS
            elif self.m_pos < PIXY_RCS_MIN_POS:
                self.m_pos = PIXY_RCS_MIN_POS
        self.m_prev_rror = error

# define pan loop
pan_loop = ServoLoop(300, 500)

class PID:
    """
    Discrete PID control
    """
    def __init__(self, P=2.0, I=0.0, D=1.0, derivator=0, integrator=0, integrator_max=500, integrator_min=-500):
        self.Kp=P
        self.Ki=I
        self.Kd=D
        self.derivator=derivator
        self.integrator=integrator
        self.integrator_max=integrator_max
        self.integrator_min=integrator_min
        self.set_point=0.0
        self.error=0.0

    def update(self,current_value):
        """
        Calculate PID output value for given reference input and feedback
        """
        self.error = self.set_point - current_value
        P_value = self.Kp * self.error
        D_value = self.Kd * (self.error - self.derivator)
        self.derivator = self.error
        self.integrator = self.integrator + self.error
        if self.integrator > self.integrator_max:
                self.integrator = self.integrator_max
        elif self.integrator < self.integrator_min:
                self.integrator = self.integrator_min
        I_value = self.integrator * self.Ki
        PID = P_value + I_value + D_value
        # print "SP:%2.2f PV:%2.2f Error:%2.2f -> P:%2.2f I:%2.2f D:%2.2f" % (self.set_point, current_value, self.error, P_value, I_value, D_value)
        return PID

    def set_point(self, set_point):
        """
        Initilize the setpoint of PID
        """
        self.set_point = set_point
        self.integrator=0
        self.derivator=0

pid = PID(h_pgain, 0, 0)


# logic for horizon per signature, etc.
def ignore(block):
    above_horizon = block.y < 60
    lines = (block.signature == LEFT_LINE) or (block.signature == CENTER_LINE) or (block.signature == RIGHT_LINE)
    if lines and above_horizon:
        return True
    return False


def adjust_brightness(bright_delta):
    pass


class Scene(object):
    """
    Detects different objects in a Scene.
    """
    def __init__(self):
        self.m_blocks = pixy.BlockArray(BLOCK_BUFFER_SIZE)
        self.m_block_count = []
        self.m_pan_error = 0
        self.m_brightness = BRIGHTNESS
        self.m_count = 0

    def is_sufficient(self):
        if not self.m_blockmap:
            return False
        # Should also check if we can see center or posts as backup.
        if self.see_center():
            return True
        return False

    def get_blocks(self):
        self.m_count = pixy.pixy_get_blocks(BLOCK_BUFFER_SIZE, self.m_blocks)

        # If negative blocks, something went wrong
        if self.m_count < 0:
            print 'Error: pixy_get_blocks() [%d] ' % self.m_count
            pixy.pixy_error(self.m_count)
            sys.exit(1)
        if self.m_count == 0:
            print "Detected no blocks"
            return None

        # package per signature
        i = 0
        blockmap = {}
        for block in self.m_blocks:
            if ignore(block):
                continue
            if block.signature not in blockmap:
                blockmap[block.signature] = []
            blockmap[block.signature].append(block)
            if i >= self.m_count:
                break
            i += 1
        return blockmap

    def blocks_seen(self):
        return self.m_count > 0

    def posts_seen(self):
        if self.m_blockmap == None:
            return False
        lpost = L_POST in self.m_blockmap
        rpost = R_POST in self.m_blockmap
        return lpost or rpost

    def see_center(self):
        if self.m_blockmap == None:
            return False
        return CENTER_LINE in self.m_blockmap

    def set_pan_error(self):
        if self.m_count == 0 or not (CENTER_LINE in self.m_blockmap):
            self.m_pan_error = 0
            return
        center = self.m_blockmap[CENTER_LINE]
        if len(center) > 1:
            self.m_pan_error = PIXY_X_CENTER - self.m_blockmap[CENTER_LINE][1].x
        else:
            self.m_pan_error = PIXY_X_CENTER - self.m_blockmap[CENTER_LINE][0].x


    @property
    def pan_error(self):
        return self.m_pan_error

    def get_frame(self):
        """Populates panError, blockCount, and blocks for a frame"""

        self.m_blockmap = None

        if no_brightness_check:
            self.m_blockmap = self.get_blocks()
            self.set_pan_error()
        else:
            self.m_brightness = pixy.pixy_cam_get_brightness()
            bmax = self.m_brightness + 20
            if bmax > 255:
                bmax = 255
            bmin = self.m_brightness - 20
            if bmin < 60:
                bmin = min(self.m_brightness-1, 60)
            gotit = False
            for i in range(self.m_brightness, bmax):
                self.m_blockmap = self.get_blocks()
                if self.is_sufficient():
                    gotit = True
                    break
                pixy.pixy_cam_set_brightness(i+1)
            if not gotit:
                for i in range(self.m_brightness-1, bmin, -1):
                    self.m_blockmap = self.get_blocks()
                    if self.is_sufficient():
                        gotit = True
                        break
                    pixy.pixy_cam_set_brightness(i)

            self.set_pan_error()
            if gotit:
                self.m_brightness = pixy.pixy_cam_get_brightness()
                print "Got good signtures at brightness %d" % self.m_brightness
            else:
                print "Could not find good signatures after brightness changes!"
                pixy.pixy_cam_set_brightness(self.m_brightness)
                return

        # calculate center blocks on each side
        right = 0
        left = 0
        if not self.m_blockmap:
            return
        if CENTER_LINE in self.m_blockmap:
            for block in self.m_blockmap[CENTER_LINE]:
                #print "Counting center block at %d" % block.x
                if block.x > PIXY_X_CENTER:    #should look for center of car, not center of pixycam view.  
                    right += 1
                else:
                    left += 1

        #print "Center blocks: left=%d, right=%d" % (left, right)

        # keep track of past AVG_N red blocks
        if len(self.m_block_count) > AVG_N:
            self.m_block_count.pop()
        self.m_block_count.insert(0, (left, right))



# init object processing
scene = Scene()

def setup():
    """
    One time setup. Inialize pixy and set sigint handler
    """
    pixy_init_status = pixy.pixy_init()
    if pixy_init_status != 0:
        print 'Error: pixy_init() [%d] ' % pixy_init_status
        pixy.pixy_error(pixy_init_status)
        return
    else:
        print "Pixy setup OK"
    signal.signal(signal.SIGINT, handle_SIGINT)
    pixy.pixy_cam_set_brightness(BRIGHTNESS)
    pixy.pixy_rcs_set_position(PIXY_RCS_PAN_CHANNEL, PIXY_RCS_CENTER_POS)
    
    if chatty:
        say_now("I may not be the fastest but I have style")
        #say("SLEEP 2")
        time.sleep(2)

def loop():
    """
    Main loop, Gets blocks from pixy, analyzes target location,
    chooses action for robot and sends instruction to motors
    """
    global start_time, throttle, diff_drive, diff_gain, bias, advance, turn_error, current_time, last_time, object_dist, dist_error, pan_error_prev, dist_error_prev, first_pass, pid_bias, last_turn

    current_time = datetime.now()
    # If no new blocks, don't do anything
    while not pixy.pixy_blocks_are_new() and run_flag:
        pass

    if first_pass:
        say("Here goes")
        start_time = time.time()
        first_pass = False

    scene.get_frame()
    if scene.blocks_seen():
        last_time = current_time
        
    if finale:
        refuse_to_play()
        return False

    p = scene.pan_error
    if p < 0:
        p = -p
    incr = p / 300.0
    #print "panError: %f, incr: %f" % (scene.panError, incr)
    #if incr > 0.65:
    #    incr = 0.65
    throttle = init_throttle  # - incr / 1.5
    diff_drive = diff_drive_straight + incr

    # amount of steering depends on how much deviation is there
    #diff_drive = diff_gain * abs(float(turn_error)) / PIXY_X_CENTER
    # use full available throttle for charging forward
    advance = 1

    pan_loop.update(scene.pan_error)

    # Update pixy's pan position
    pixy.pixy_rcs_set_position(PIXY_RCS_PAN_CHANNEL, pan_loop.m_pos)

    # if Pixy sees nothing recognizable, don't move.
    # time_difference = current_time - last_time
    if not scene.see_center(): #time_difference.total_seconds() >= timeout:
        print "Stopping since see nothing"
        throttle = 0.0
        diff_drive = 1

    turn = 0

    # this is turning to left
    if pan_loop.m_pos > PIXY_RCS_CENTER_POS:
        # should be still int32_t
        turn_error = pan_loop.m_pos - PIXY_RCS_CENTER_POS
        # <0 is turning left; currently only p-control is implemented
        turn = float(turn_error) / float(PIXY_RCS_CENTER_POS)

    # this is turning to right
    elif pan_loop.m_pos < PIXY_RCS_CENTER_POS:
        # should be still int32_t
        turn_error = PIXY_RCS_CENTER_POS - pan_loop.m_pos
        # >0 is turning left; currently only p-control is implemented
        turn = -float(turn_error) / float(PIXY_RCS_CENTER_POS)

    pid.set_point(0)
    pid_bias = pid.update(turn)
    #print "PID controller: SP=%2.2f PV=%2.2f -> OP=%2.2f" % (0, turn, pid_bias)
    last_turn = turn
    bias = pid_bias # use PID controller on turn bias
    # TODO: parameterize drive()

    if bias < -0.3:
        say("Going left")
    if bias > 0.3:
        say("Going right")

    drive()
    return run_flag

def drive():

    if not allow_move:
        return
    
    if advance < 0:
        say("Backup up.  Beep.  Beep.  Beep.")
        print "Drive: Backing up.  Beeeep...Beeeep...Beeeep"

    #print "Drive: advance=%2.2f, throttle=%2.2f, diff_drive=%2.2f, bias=%2.2f" % (advance, throttle, diff_drive, bias)

    # syn_drive is the drive level for going forward or backward (for both wheels)
    syn_drive = advance * (1 - diff_drive) * throttle * total_drive
    left_diff = bias * diff_drive * throttle * total_drive
    right_diff = -bias * diff_drive * throttle * total_drive
    #print "Drive: syn_drive=%2.2f, left_diff=%2.2f, right_diff=%2.2f" % (syn_drive, left_diff, right_diff)

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

### Dance moves

def forward(t):
    global bias, advance, throttle, diff_drive
    bias =0
    advance =1
    throttle =.25
    diff_drive=0
    drive()
    time.sleep(t) 

def backward(t):
    global bias, advance, throttle, diff_drive
    bias =0
    advance= -1
    throttle=.3
    diff_drive=0
    drive()
    time.sleep(t)

def r_spin(t):
    global bias, advance, throttle, diff_drive
    bias =1
    advance=1
    throttle=.3
    diff_drive=1
    drive()
    time.sleep(t)

def l_spin(t):
    global bias, advance, throttle, diff_drive
    bias = -1
    advance=1
    throttle=.3
    diff_drive=1
    drive()
    time.sleep(t)

def right(t):
    global bias, advance, throttle, diff_drive
    bias =0.5
    advance=1
    throttle=.4
    diff_drive=.5
    drive()
    time.sleep(t)

def left(t):
    global bias, advance, throttle, diff_drive
    bias = -0.5
    advance=1
    throttle=.3
    diff_drive=.5
    drive()
    time.sleep(t)

###  Experimental behaviors

def refuse_to_play():
        motors.setSpeeds(0, 0)
        l_spin(1)
        
        say_now("I'm going to dance")
        #say("SLEEP 1")
        time.sleep(2)
 
        right(1.5)
        left(1.5)
        forward(2)
        backward(2)
        r_spin(4)
        l_spin(3)
        r_spin(3)
        right(1.5)
        left(1.5)
        backward(2)
        forward(2)
        r_spin(5)
        l_spin(5)
        #while True:
        #    ok = loop()
        #    if not ok:
        #        break
        #pixy.pixy_close()
        motors.setSpeeds(0, 0)

    

def backup():
    pan_error = PIXY_X_CENTER - blocks[0].x
    object_dist = refSize1 / (2 * math.tan(math.radians(blocks[0].width * pix2ang_factor)))
    throttle = 0.5
    # amount of steering depends on how much deviation is there
    diff_drive = diff_gain * abs(float(pan_error)) / PIXY_X_CENTER
    dist_error = object_dist - target_dist
    # this is in float format with sign indicating advancing or retreating
    advance = drive_gain * float(dist_error) / refDist


def hailmary(block_count):
    global throttle, diff_drive, diff_gain, bias, advance, turn_error, current_time, last_time, object_dist, dist_error, pan_error_prev, dist_error_prev
    if len(block_count) == 0:
        print "can't do hailmary with no blocks"
        return

    print "Attempting to hail Mary with %d block history"%len(block_count)
    left_total = 0.0
    right_total = 0.0
    for (left, right) in block_count:
        left_total += left
        right_total += right
    avg_left = left_total / len(block_count)
    avg_right = right_total / len(block_count)
    print "Past %d frames had avg red blocks on (left=%d, right=%d)" % (AVG_N,avg_left,avg_right)
    # Turn towards the preponderance of red blocks
    last_time = currentTime
    if avg_left>avg_right:
        print "Executing blind left turn"
        bias = -1
    elif avg_right>avg_left:
        print "Executing blind right turn"
        bias = 1
    else:
        bias = 0
    if bias != 0:
        # Slow forward turn
        advance = 1
        throttle = 0.5
        diff_drive = 1
        # Reset pixy's head
        pixy.pixy_rcs_set_position(PIXY_RCS_PAN_CHANNEL, PIXY_RCS_CENTER_POS)
        normal_drive = False
    #If hailmary didn't work, hold on to your rosary beads, we're going hunting!
    else:
        # Need some kind of hunting behavior here
        #This situation usally arises when we're on a curve in one direction and want to sharply turn in the other direction
        #pan the camera until we find a red block, then go straight toward it.  
        print "Execute search and destroy"
        i=0
        no_red_blocks=True
        advance=-1 #if we can't find it, retreat
        while (no_red_blocks==True and i <= PIXY_RCS_MAX_POS):
        #while redblock not found
            #pan for red block
            print "Panning for red block. i:%d" %(i)
            pixy.pixy_rcs_set_position(PIXY_RCS_PAN_CHANNEL, i)
            count = pixy.pixy_get_blocks(BLOCK_BUFFER_SIZE, blocks)
            largest_block = blocks[0]
            #code stolen from earlier in file, maybe turn it into a function?
            if largest_block.signature == 2:
                no_red_blocks=False
                pan_error = PIXY_X_CENTER-blocks[0].x
                p = pan_error / 40.0
                if p < 0:
                    p = -p
                if p > 0.8:
                    p = 0.8
                throttle = 0.9 - p
                diff_drive = 0.6
                print "p: %f, pan_error: %d, turn_error: %d" % (p, pan_error, turn_error)
                advance = 1
            i= i +10


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='The Heather RaspberryPi Robot Racer')
    
    parser.add_argument('--chatty', dest='chatty', action='store_true')
    parser.set_defaults(chatty=False)    
    
    parser.add_argument('--bright', dest='bright', action='store_true')
    parser.set_defaults(bright=False)    

    parser.add_argument('--no-move', dest='move', action='store_false')
    parser.set_defaults(move=True)    

    parser.add_argument('--finale', dest='finale', action='store_true')
    parser.set_defaults(finale=False)    

    parser.add_argument("--lookahead", type=int, choices=[0, 1, 2],
                        help="set the center lookahead")
    parser.set_defaults(lookahead=0)    

    args = parser.parse_args()
    print "Chatty mode: ", args.chatty
    print "Alter brightness: ", args.bright
    print "Lookahead: ", args.lookahead
    
    if args.bright:
        no_brightness_check = False

    if not args.move:
        allow_move = False

    if args.finale:
        finale = True
        
    if args.chatty:
        chatty = True
        # Start thread to listen to say() commands and forward them to the text2speech web service
        t = threading.Thread(target=voice_thread_loop)
        t.daemon = True
        t.start()
        
    # Robot set up 
    setup()
    # Main loop
    try:
        while True:
            ok = loop()
            if not ok:
                break
    finally:
        say("Good bye")
        pixy.pixy_close()
        motors.setSpeeds(0, 0)
        print "Robot Shutdown Completed"

