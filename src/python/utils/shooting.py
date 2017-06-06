"""
Process for automatically firing the laser as fast as possible.

Examples
--------

Import and instantiate our laser commander
>>> from utils.shooting import LaserController
>>> controller = LaserController()

Start the laser controller process
>>> controller.start()

Instruct the laser commander
>>> controller.fire_once()
>>> controller.fire_at_will()
>>> controller.hold_fire()

`fire_once` blocks execution until the laser reports that it has fired. A timeout can be passed in to prevent it from
waiting indefinitely.

By default, `fire_at_will` does not block. To make it block until the laser has reported that it has fired one shot,
pass `True` as the first argument - again, a timeout can be passed as a second argument.

To fire multiple times in a row, blocking between each shot, use
>>> controller.fire_multiple(n)  # fire n shots

Find out when the laser last fired (updated automatically)
>>> controller.last_fired

You must remember to stand down the commander!
>>> controller.stand_down()

You can (/should) use the Laser Commander in a `with` statement so that you don't have to remember anything, and errors
are handled better:
>>> with LaserController() as controller:
>>>     controller.fire_at_will()
The Commander will be stood down automatically upon leaving the `with` statement (including error cases)
"""

from multiprocessing import Process, Value, Array
import logging
import time
import datetime

from utils.constants import LASER_COOLDOWN, RECOVERY, PixySerial

# year, month, day, hour, second, microsecond
EPOCH_TUPLE = (datetime.MINYEAR, 1, 1, 0, 0, 0, 0)

POLL_INTERVAL = 0.001  # small delay to prevent polling threads consuming 100% CPU

INITIAL_VALUE = -2
READY_SIGNAL = -1

logger = logging.getLogger(__name__)


class LaserController(object):
    """Class for controlling the behaviour of the laser in a fire-and-forget fashion."""
    __instance = None

    def __init__(self):
        self.interface = LaserInterface()
        self.laser_process = LaserProcess(self.interface)
        self.logger = logging.getLogger(type(self).__name__)

    def start(self):
        """Start the underlying WeaponsSystem process; blocks until laser is ready"""
        self.logger.debug('Starting laser process')
        self.laser_process.start()
        while self.interface.stood_down:
            time.sleep(POLL_INTERVAL)

    @property
    def last_fired(self):
        """Float timestamp, in seconds since the Epoch, when the laser last fired."""
        return self.interface.last_fired

    @property
    def last_hit(self):
        """Float timestamp, in seconds since the Epoch, when the robot was last hit with a laser"""
        return self.interface.last_hit

    @property
    def is_disabled(self):
        """Whether the laser is currently disabled by being hit"""
        return self.interface.is_disabled

    def fire_multiple(self, shots=1, timeout_per_shot=None):
        """
        Fire the given number of times as fast as possible, blocking between each one until the laser has fired.

        Parameters
        ----------
        shots : int
            How many shots to fire
        timeout_per_shot : float
            Maximum time to wait for each shot. If None (default), it will wait indefinitely.
        """
        self.logger.info('Fire {} times!'.format(shots))
        results = []
        for _ in range(shots):
            results.append(self.fire_once(timeout_per_shot))

        return results

    def fire_once(self, timeout=None):
        """
        Fire the laser once and then return it to the 'hold fire' state, blocking execution until the laser has fired.

        Parameters
        ----------
        timeout : float
            Maximum time to wait for laser to fire. If None (default), it will wait indefinitely.

        Returns
        -------
        bool
            Whether the laser successfully fired in the time given
        """
        self.logger.info('Fire once!')
        previous_fire = self.interface.last_fired
        self.interface.firing = True
        result = self.interface.wait_for_change('last_fired', previous_fire, timeout)
        self.interface.firing = False
        return result

    def fire_at_will(self, block=False, timeout=None):
        """
        Fire the laser as often as possible, indefinitely.

        Parameters
        ----------
        block : bool
            Whether to wait until the laser has fired at least once before continuing execution
        timeout : float
            Timeout for first laser shot (ignored if `block` is False). If None (default), it will wait indefinitely.

        Returns
        -------
        bool or None
            If block is True, a boolean is returned for whether the laser successfully fired before the timeout.
        """
        self.logger.info('Fire at will!')
        result = None
        if block:
            result = self.fire_once(timeout)
        self.interface.firing = True
        return result

    def hold_fire(self):
        """Stop firing the laser"""
        self.interface.firing = False

    def stand_down(self):
        """Stop firing the laser and close the underlying process. Blocks until the process is closed."""
        self.interface.stood_down = True
        self.logger.debug('Stopping laser process')
        self.laser_process.join()
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


def datetime_to_array(array, timestamp=None):
    """
    Set the given array

    Parameters
    ----------
    timestamp : datetime.datetime
    array : multiprocessing.Array

    Returns
    -------
    None
    """
    array.acquire()
    array[0] = timestamp.year
    array[1] = timestamp.month
    array[2] = timestamp.day
    array[3] = timestamp.hour
    array[4] = timestamp.minute
    array[5] = timestamp.second
    array[6] = timestamp.microsecond
    array.release()


def array_to_datetime(array):
    """

    Parameters
    ----------
    array : multiprocessing.Array

    Returns
    -------
    datetime.datetime
    """
    array.acquire()
    dt = datetime.datetime(*array)
    array.release()
    return dt


class LaserInterface(object):
    """Object for passing commands into, and getting feedback from, weapons system"""

    def __init__(self, cooldown=LASER_COOLDOWN, recovery=RECOVERY):
        """

        Parameters
        ----------
        cooldown : float
            Time in seconds between laser shots
        recovery : float
            Time in seconds for laser to reactivate after being hit
        """
        self._firing = Value('h', 0)
        self._stood_down = Value('h', 1)  # start stood down; LaserProcess brings online
        self._last_fired = Array('L', EPOCH_TUPLE)
        self._last_hit = Array('L', EPOCH_TUPLE)
        self.cooldown = datetime.timedelta(seconds=cooldown)
        self.recovery = datetime.timedelta(seconds=recovery)

    @property
    def firing(self):
        return bool(self._firing.value)

    @firing.setter
    def firing(self, new_value):
        self._firing.value = bool(new_value)

    @property
    def stood_down(self):
        return bool(self._stood_down.value)

    @stood_down.setter
    def stood_down(self, new_value):
        self._stood_down.value = bool(new_value)

    @property
    def last_fired(self):
        return array_to_datetime(self._last_fired)

    @last_fired.setter
    def last_fired(self, new_value):
        datetime_to_array(self._last_fired, new_value)

    @property
    def last_hit(self):
        return array_to_datetime(self._last_hit)

    @last_hit.setter
    def last_hit(self, new_value):
        datetime_to_array(self._last_hit, new_value)

    @property
    def is_cooling(self):
        return datetime.datetime.utcnow() - self.last_fired < self.cooldown

    @property
    def is_disabled(self):
        return datetime.datetime.utcnow() - self.last_hit < self.recovery

    def wait_for_change(self, attribute, initial=None, timeout=None):
        started = datetime.datetime.now()
        finish = started + datetime.timedelta(seconds=timeout) if timeout else datetime.datetime(datetime.MAXYEAR, 1, 1)

        if initial is None:
            initial = getattr(self, attribute)

        value = getattr(self, attribute)
        while value == initial:
            if datetime.datetime.utcnow() > finish:
                return False
            time.sleep(POLL_INTERVAL)
            value = getattr(self, attribute)

        return True


class LaserProcess(Process):
    def __init__(self, laser_interface):
        super(LaserProcess, self).__init__()
        self.interface = laser_interface
        self.ser = None
        self.logger = None

    def run(self):
        self.logger = logging.getLogger(type(self).__name__)
        self.logger.debug('Laser Process started')
        self._setup_serial()

        while not self.interface.stood_down:
            if self.interface.firing and not self.interface.is_cooling and not self._check_hit():
                self._fire()

            time.sleep(POLL_INTERVAL)

        self.logger.debug('Laser Process stood down')

    def _setup_serial(self):
        if self.ser is None:
            self.ser = PixySerial.get()
        self.interface.stood_down = False

    def _check_hit(self):
        if self.interface.is_disabled:
            return True

        if self.ser.in_waiting and self.ser.readline().rstrip() == 'HIT':
            self.logger.warn("We've been hit!")
            self.interface.last_hit = datetime.datetime.utcnow()
            return True

        return False

    def _fire(self):
        self.logger.debug('Firing!')
        self.ser.write("FIRE\n")
        self.interface.last_fired = datetime.datetime.utcnow()
        self.logger.debug('Laser cooling for {}s'.format(self.interface.cooldown))
