"""
Process for automatically firing the laser as fast as possible.

Examples
--------

Import and instantiate our laser commander
>>> from utils.shooting import WeaponsOfficer
>>> lt_worf = WeaponsOfficer()

Start the laser controller process
>>> lt_worf.start()

Instruct the laser commander
>>> lt_worf.fire_once()
>>> lt_worf.fire_at_will()
>>> lt_worf.hold_fire()

`fire_once` blocks execution until the laser reports that it has fired. A timeout can be passed in to prevent it from
waiting indefinitely.

By default, `fire_at_will` does not block. To make it block until the laser has reported that it has fired one shot,
pass `True` as the first argument - again, a timeout can be passed as a second argument.

To fire multiple times in a row, blocking between each shot, use
>>> lt_worf.fire_multiple(n)  # fire n shots

Find out when the laser last fired (updated automatically)
>>> lt_worf.last_fired

You must remember to stand down the commander!
>>> lt_worf.stand_down()

You can (/should) use the Laser Commander in a `with` statement so that you don't have to remember anything, and errors
are handled better:
>>> with WeaponsOfficer() as lt_worf:
>>>     lt_worf.fire_at_will()
The Commander will be stood down automatically upon leaving the `with` statement (including error cases)
"""

from multiprocessing import Process, Value
import logging
import time

from utils.constants import LASER_COOLDOWN, RECOVERY, PixySerial


POLL_INTERVAL = 0.001  # small delay to prevent polling threads consuming 100% CPU

INITIAL_VALUE = -2
READY_SIGNAL = -1

logger = logging.getLogger(__name__)


class WeaponsOfficer(object):
    """Class for controlling the behaviour of the laser in a fire-and-forget fashion."""
    __instance = None

    def __init__(self):
        self.console = WeaponsConsole()
        self.weapons_system = WeaponsSystem(self.console)
        self.logger = logging.getLogger(type(self).__name__)

    def start(self):
        """Start the underlying WeaponsSystem process; blocks until laser is ready"""
        self.logger.debug('Starting laser process')
        self.weapons_system.start()
        while self.console.last_fired < READY_SIGNAL:
            time.sleep(POLL_INTERVAL)

    @property
    def last_fired(self):
        """Float timestamp, in seconds since the Epoch, when the laser last fired."""
        return self.console.last_fired

    @property
    def last_hit(self):
        return self.console.last_hit

    @property
    def is_disabled(self):
        return self.console.is_disabled

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
        previous_fire = self.console.last_fired
        self.console.firing = True
        result = self.console.wait_for_change('last_fired', previous_fire, timeout)
        self.console.firing = False
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
        result = None
        if block:
            result = self.fire_once(timeout)
        self.console.firing = True
        return result

    def hold_fire(self):
        """Stop firing the laser"""
        self.console.firing = False

    def stand_down(self):
        """Stop firing the laser and close the underlying process. Blocks until the process is closed."""
        self.console.stood_down = True
        self.weapons_system.join()
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


class WeaponsConsole(object):
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
        self._stood_down = Value('h', 0)
        self._last_fired = Value('d', INITIAL_VALUE)
        self._last_hit = Value('d', READY_SIGNAL)
        self.cooldown = cooldown
        self.recovery = recovery

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
        return self._last_fired.value

    @last_fired.setter
    def last_fired(self, new_value):
        self._last_fired.value = new_value

    @property
    def last_hit(self):
        return self._last_hit.value

    @last_hit.setter
    def last_hit(self, new_value):
        self._last_hit.value = new_value

    @property
    def is_cooling(self):
        return time.time() < self.last_fired + self.cooldown

    @property
    def is_disabled(self):
        return time.time() < self.last_hit + self.recovery

    def wait_for_change(self, attribute, initial=None, timeout=None):
        started = time.time()
        finish = started + timeout if timeout else float('inf')

        if initial is None:
            initial = getattr(self, attribute)

        value = getattr(self, attribute)
        while value == initial:
            if time.time() > finish:
                return False
            time.sleep(POLL_INTERVAL)
            value = getattr(self, attribute)

        return True


class WeaponsSystem(Process):
    def __init__(self, weapons_console):
        super(WeaponsSystem, self).__init__()
        self.console = weapons_console
        self.ser = None
        self.logger = None

    def run(self):
        self.logger = logging.getLogger(type(self).__name__)
        self._setup_serial()

        while not self.console.stood_down:
            if self.console.firing and not self.console.is_cooling and not self._check_hit():
                self._fire()

            time.sleep(POLL_INTERVAL)

    def _setup_serial(self):
        if self.ser is None:
            self.ser = PixySerial.get()
        self.console.last_fired = READY_SIGNAL

    def _check_hit(self):
        if self.console.is_disabled:
            return True

        if self.ser.in_waiting and self.ser.readline().rstrip() == 'HIT':
            self.logger.warn("We've been hit!")
            self.console.last_hit = time.time()
            return True

        return False

    def _fire(self):
        self.logger.debug('Firing!')
        self.ser.write("FIRE\n")
        self.logger.debug('Laser cooling for {}s'.format(self.console.cooldown))
