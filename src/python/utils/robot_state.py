class RobotState(object):
    """docstring for robot_state"""
    def __init__(self, blocks, current_time, total_drive):
        self.blocks = blocks
        self.throttle = 0
        self.diff_drive = 0
        self.diff_gain = 0
        self.bias = 0
        self.advance = 0
        self.drive_gain = 1
        self.h_pgain = 0.5
        self.h_dgain = 0
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