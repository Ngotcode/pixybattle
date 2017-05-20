"""
Process for automatically firing the laser as fast as possible.

Examples
--------

Import and instantiate our laser commander
>>> from utils.shooting import LaserCommander
>>> lt_worf = LaserCommander()

Start the laser controller process
>>> lt_worf.start()

Instruct the laser commander
>>> lt_worf.fire_once()
>>> lt_worf.fire_at_will()
>>> lt_worf.hold_fire()

By default, `fire_once` blocks execution until the laser reports that it has fired, but this can be disabled by passing 
`False`.

By default, `fire_at_will` does not block. To make it block until the laser has reported that it has fired one shot, 
pass `True`.

To fire multiple times in a row, blocking between each shot, use
>>> lt_worf.fire_multiple(n)  # fire n shots

Find out when the laser last fired (updated automatically)
>>> lt_worf.last_fired

You must remember to stand down the commander!
>>> lt_worf.stand_down()

You can (/should) use the Laser Commander in a `with` statement so that you don't have to remember anything, and errors 
are handled better:
>>> with LaserCommander() as lt_worf:
>>>     lt_worf.fire_at_will()
The Commander will be stood down automatically upon leaving the `with` statement (including error cases)
"""

from multiprocessing import Process, Queue
from multiprocessing.queues import Empty
import logging

from enum import Enum
import serial
import time

from utils.constants import LASER_COOLDOWN, SERIAL_DEVICE, BAUD_RATE


POLL_INTERVAL = 0.001  # small delay to prevent polling threads consuming 100% CPU

logger = logging.getLogger(__name__)

class DeadDrop(object):
    """
    A Queue which holds only a single object and overwrites it as more are put in. Useful for communicating state 
    between processes in a memoryless fashion.
    """
    MAX_SIZE = 1

    def __init__(self):
        self.q = Queue(type(self).MAX_SIZE)

    def put(self, item):
        """
        Put item in the queue, removing any other items if the queue is not empty. Non-blocking because it always 
        empties the list before attempting an insert.
        
        Parameters
        ----------
        item : object
        
        Raises
        ------
        multiprocessing.queues.Full
        """
        # timeouts required because multiprocessing is dumb
        try:
            self.q.get(timeout=POLL_INTERVAL)
        except Empty:
            pass

        self.q.put(item, timeout=POLL_INTERVAL)

    def get(self, default=None):
        """
        Get the item from the DeadDrop if it exists. If the DeadDrop is empty and a default is supplied, return that; 
        otherwise raise multiprocessing.queues.Empty.
        
        Parameters
        ----------
        default
            Default value to return if DeadDrop is empty.

        Returns
        -------
        object
        
        Raises
        ------
        multiprocessing.queues.Empty
        """
        try:
            return self.q.get(timeout=POLL_INTERVAL)
        except Empty as e:
            if default is None:
                raise e
            else:
                return default

    def empty(self):
        return self.q.empty()

    def qsize(self):
        return self.q.qsize()


class Command(Enum):
    """Enumerate the commands which the laser can execute"""
    FIRE_ONCE = 'fire once'
    FIRE_AT_WILL = 'fire at will'
    HOLD_FIRE = 'hold fire'
    STAND_DOWN = 'stand down'


class LaserCommander(object):
    """Class for controlling the behaviour of the laser in a fire-and-forget fashion."""
    __instance = None

    def __init__(self):
        self._laser_input, self._laser_output = DeadDrop(), DeadDrop()
        self._laser = LaserProcess(self._laser_input, self._laser_output, False, LASER_COOLDOWN)
        self.__stood_down = False
        self.__last_fired = None
        self.logger = logging.getLogger(type(self).__name__)
        self.started = False

    def start(self):
        """Start the underlying AutoLaser process"""
        self.logger.debug('Starting laser process')
        self._laser.start()
        self.started = True

    def _send_command(self, command):
        self.logger.info('Sending laser command: "%s"'.format(command))
        if self.stood_down:
            raise ValueError('Cannot send command to stood-down Laser Commander - create a new one.')
        if not self.started:
            raise ValueError('Cannot send command to Laser Commander which has not been started')
        self._laser_input.put(command)

    @property
    def stood_down(self):
        """Boolean, whether the LaserCommander is stood down"""
        return self.__stood_down

    @property
    def last_fired(self):
        """Float timestamp, in seconds since the Epoch, when the laser last fired."""
        self.__last_fired = self._laser_output.get(default=self.__last_fired)
        return self.__last_fired

    def fire_multiple(self, shots=1):
        """
        Fire the given number of times as fast as possible, blocking between each one
        
        Parameters
        ----------
        shots : int
            How many shots to fire
        """
        for _ in range(shots):
            self.fire_once(True)

    def fire_once(self, block=True):
        """
        Fire the laser once and then return it to the 'hold fire' state. Does not wait for the laser to cool down.
        
        Parameters
        ----------
        block : boolean
            Whether to wait for the laser to fire before continuing execution
        """
        previous_fire = self.last_fired
        self._send_command(Command.FIRE_ONCE)
        if block:
            while self.last_fired == previous_fire:
                time.sleep(POLL_INTERVAL)

    def fire_at_will(self, block=False):
        """Fire the laser as fast as possible, indefinitely"""
        if block:
            self.fire_once(True)
        self._send_command(Command.FIRE_AT_WILL)

    def hold_fire(self):
        """Stop firing the laser"""
        self._send_command(Command.HOLD_FIRE)

    def stand_down(self):
        """Stop firing the laser and close the underlying process. Blocks until the process is closed."""
        self._send_command(Command.STAND_DOWN)
        self.__stood_down = True
        self._laser.join()
        self.__instance = None

    @classmethod
    def __new__(cls, *args, **kwargs):
        """Ensure that only one LaserCommander has control over the hardware at any time."""
        if cls.__instance is None:
            cls.__instance = object.__new__(cls)

        return cls.__instance

    def __enter__(self):
        """Start the process on entering a with clause"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stand down the laser on leaving a with clause"""
        self.stand_down()


class LaserProcess(Process):
    """Separate python process which can operate the laser independently of the main thread"""

    def __init__(self, input_drop, output_drop, firing=False, timeout=LASER_COOLDOWN):
        """
        
        Parameters
        ----------
        input_drop : DeadDrop
            DeadDrop from which the laser will receive commands
        output_drop : DeadDrop
            DeadDrop to which the laser will record its last fire time
        firing : bool
            Whether the laser is currently in 'fire at will' mode
        timeout : float
            Cooldown in seconds between laser shots
        """
        super(LaserProcess, self).__init__()
        self.input_drop = input_drop
        self.output_drop = output_drop
        self.firing = firing
        self.timeout = timeout
        self.ser = serial.Serial(SERIAL_DEVICE, BAUD_RATE)  # todo: handle failure to acquire serial
        self.logger = None

    def run(self):
        self.logger = logging.getLogger(type(self).__name__)
        while True:
            try:
                command = self.input_drop.get()
                self.logger.debug('Received command: %s', command)
                if command == Command.FIRE_ONCE:
                    self.firing = False
                    self._fire()
                elif command == Command.FIRE_AT_WILL:
                    self.firing = True
                    self._fire()
                elif command == Command.HOLD_FIRE:
                    self.firing = False
                elif command == Command.STAND_DOWN:
                    return
                else:
                    ValueError('Unknown command {} received'.format(command))
            except Empty:
                if self.firing:
                    self._fire()
                else:
                    time.sleep(POLL_INTERVAL)

    def _fire(self):
        """Fire the laser, record the timestamp, and block this process for the cooldown period"""
        self.logger.debug('Firing!')
        self.ser.write("FIRE\n")
        # todo: get response signal from ser?
        self.output_drop.put(time.time())
        time.sleep(self.timeout)
