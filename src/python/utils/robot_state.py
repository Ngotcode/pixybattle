from random import random
from utils.constants import MIN_TIME_TURN_WALL, MIN_TIME_TURN, MAX_TIME_TURN_WALL, MAX_TIME_TURN
from time import time

class RobotState(object):
    """docstring for robot_state"""
    def switch_to_search(self, wall = False):
        self.state = "search"
        self.turn_direction = 1 if random() <.5 else -1
        if wall:
            self.max_turning_time = MIN_TIME_TURN_WALL + random() * (MAX_TIME_TURN_WALL - MIN_TIME_TURN_WALL)
            self.min_turning_time = MIN_TIME_TURN_WALL
        else:
            self.max_turning_time = MIN_TIME_TURN + random() * (MAX_TIME_TURN - MIN_TIME_TURN)
            self.min_turning_time = MIN_TIME_TURN
        self.advance = 0
        self.search_starting_time = time()
    
    def __init__(self, blocks, current_time, total_drive):
        self.blocks = blocks
        self.throttle = 0
        self.diff_drive = 0
        self.diff_gain = 0
        self.bias = 0
        self.advance = 0
        self.drive_gain = 1
        self.h_pgain = 0.7
        self.h_dgain = 0.2
        self.turn_error = 0
        self.current_time = current_time
        self.last_time = current_time
        self.object_dist = 100
        self.dist_error = 0
        self.pan_error_prev = 0
        self.dist_error_prev = 0
        self.pan_loop = 0
        self.killed = False
        self.last_fire = current_time
        self.total_drive = total_drive
        self.target_dist = 100
        self.ref_dist = 400
        self.previous_turn_error = 0
        self.previous_time = current_time
        self.deadband = 0.05 * total_drive
        self.state = "search"
        self.switch_to_search()
