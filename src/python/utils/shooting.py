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
import time

from utils.constants import LASER_COOLDOWN, PixySerial


POLL_INTERVAL = 0.01  # small delay to prevent polling threads consuming 100% CPU
READY_SIGNAL = -1

logger = logging.getLogger(__name__)


def put_singular(queue, item):
    """
    Put item in the queue, removing any other items if the queue is not empty. Non-blocking because it always 
    empties the list before attempting an insert.
    
    Parameters
    ----------
    queue : multiprocessing.Queue
    item : object
    
    Raises
    ------
    multiprocessing.queues.Empty
    """
    # timeouts required because multiprocessing is dumb
    try:
        while True:
            queue.get(timeout=POLL_INTERVAL)
    except Empty:
        queue.put(item, timeout=POLL_INTERVAL)


def get_with_default(queue, default=None):
    """
    Get the item from the queue if it exists. If the queue is empty and a default is supplied, return that; 
    otherwise raise multiprocessing.queues.Empty.
    
    Parameters
    ----------
    queue : multiprocessing.Queue
    default
        Default value to return if queue is empty.

    Returns
    -------
    object
    
    Raises
    ------
    multiprocessing.queues.Empty
    """
    try:
        return queue.get(timeout=POLL_INTERVAL)
    except Empty as e:
        if default is None:
            raise e
        else:
            return default


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
        self._command_queue, self._timestamp_queue = Queue(1), Queue(1)
        self._laser = LaserProcess(self._command_queue, self._timestamp_queue, False, LASER_COOLDOWN)
        self.__stood_down = False
        self.__last_fired = -1
        self.logger = logging.getLogger(type(self).__name__)
        self.started = False

    def start(self):
        """Start the underlying AutoLaser process; blocks until laser is ready"""
        self.logger.debug('Starting laser process')
        self._laser.start()
        assert self._timestamp_queue.get() == READY_SIGNAL
        self.started = True

    def _send_command(self, command):
        self.logger.info('Sending laser command: "%s"', command)
        if self.stood_down:
            raise ValueError('Cannot send command to stood-down Laser Commander - create a new one.')
        if not self.started:
            raise ValueError('Cannot send command to Laser Commander which has not been started')
        put_singular(self._command_queue, command)

    @property
    def stood_down(self):
        """Boolean, whether the LaserCommander is stood down"""
        return self.__stood_down

    @property
    def last_fired(self):
        """Float timestamp, in seconds since the Epoch, when the laser last fired."""
        self.__last_fired = get_with_default(self._timestamp_queue, self.__last_fired)
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

    def __init__(self, command_queue, timestamp_queue, firing=False, cooldown=LASER_COOLDOWN):
        """
        
        Parameters
        ----------
        command_queue : multiprocessing.Queue
            DeadDrop from which the laser will receive commands
        timestamp_queue : multiprocessing.Queue
            DeadDrop to which the laser will record its last fire time
        firing : bool
            Whether the laser is currently in 'fire at will' mode
        cooldown : float
            Cooldown in seconds between laser shots
        """
        super(LaserProcess, self).__init__()
        self.command_queue = command_queue
        self.timestamp_queue = timestamp_queue
        self.firing = firing
        self.cooldown = cooldown
        self.ser = None
        self.logger = None

    def run(self):
        self.logger = logging.getLogger(type(self).__name__)

        self.setup_serial()

        while True:
            try:
                command = self.command_queue.get(timeout=POLL_INTERVAL)
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
        put_singular(self.timestamp_queue, time.time())
        self.logger.debug('Laser cooling for {}s'.format(self.cooldown))
        time.sleep(self.cooldown)

    def setup_serial(self):
        if self.ser is None:
            self.ser = PixySerial.get()
        self.timestamp_queue.put(READY_SIGNAL)
