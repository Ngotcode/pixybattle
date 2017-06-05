import os
from multiprocessing import Process
import datetime
import time
import logging
import csv
import json

import pytest

from utils.shooting import LaserController, LaserInterface

logger = logging.getLogger('tests.shooting_test')

DEBUG = True

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'shooting_test')

SHORT_COOLDOWN = 0.2  # seconds
SHORT_RECOVERY = 0.3  # seconds

READ = 'READ'
WRITE = 'WRITE'
FIRE = r'FIRE\n'
HIT = 'HIT'


INIT_VALUE = datetime.datetime(100, 1, 1)
TEST_VALUE = datetime.datetime(200, 1, 1)


def empty_output_dir():
    logging.debug('Emptying output directory %s', OUTPUT_DIR)
    for filename in os.listdir(OUTPUT_DIR):
        filepath = os.path.join(OUTPUT_DIR, filename)
        os.remove(filepath)


def setup_module():
    logger.info('Setting up %s module', __name__)
    if os.path.isdir(OUTPUT_DIR):
        empty_output_dir()
    else:
        logger.debug('Creating output directory %s', OUTPUT_DIR)
        os.makedirs(OUTPUT_DIR)


def teardown_module():
    if not DEBUG:
        empty_output_dir()


class ValueChangerProcess(Process):
    def __init__(self, laser_interface):
        super(ValueChangerProcess, self).__init__()
        self.interface = laser_interface

    def run(self):
        self.interface.last_fired = TEST_VALUE


class ValueCheckerProcess(Process):
    def __init__(self, laser_interface):
        super(ValueCheckerProcess, self).__init__()
        self.interface = laser_interface
        self.initial_val = laser_interface.last_fired

    def run(self):
        time.sleep(0.1)
        assert self.initial_val == INIT_VALUE
        assert self.interface.last_fired == TEST_VALUE


# DEADDROP TESTS


@pytest.fixture
def laser_interface():
    return LaserInterface(SHORT_COOLDOWN, SHORT_RECOVERY)


def test_put_across_processes(laser_interface):
    laser_interface.last_fired = INIT_VALUE
    proc = ValueChangerProcess(laser_interface)
    proc.start()
    time.sleep(0.1)
    assert laser_interface.last_fired == TEST_VALUE
    proc.join()


def test_get_across_processes(laser_interface):
    laser_interface.last_fired = INIT_VALUE
    proc = ValueChangerProcess(laser_interface)
    proc.start()
    laser_interface.last_fired = TEST_VALUE
    proc.join()


def datetime_to_list(dt=None):
    if dt is None:
        dt = datetime.datetime.now()
    return [dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond]


def list_to_datetime(lst):
    return datetime.datetime(*lst)


class DummySerial(object):
    def __init__(self, output_filename=None, is_hit=False):
        self.output_path = self.set_filename(output_filename)
        self.is_hit = is_hit

    def write(self, arg):
        self.log(WRITE, arg)

    @property
    def in_waiting(self):
        return self.is_hit

    def read(self):
        return HIT if self.is_hit else ''

    def log(self, operation, msg=''):
        with open(self.output_path, 'a') as f:
            f.write(
                '{}\t{}\t{}\n'.format(datetime_to_list(), operation, msg.encode('string_escape') if msg else 'EMPTY_MESSAGE')
            )

    def set_filename(self, filename):
        if filename is None:
            return
        self.output_path = os.path.join(OUTPUT_DIR, filename)
        return self.output_path

    def read_log(self):
        with open(self.output_path) as f:
            reader = csv.DictReader(f, fieldnames=['time', 'op', 'msg'], delimiter='\t')
            out = []
            for line in reader:
                line['time'] = list_to_datetime(json.loads(line['time']))
                out.append(line)
            return out


@pytest.fixture
def controller_dummy(request):
    controller = LaserController()
    dummy_serial = DummySerial(request.function.__name__ + '.txt')
    controller.interface.cooldown = datetime.timedelta(seconds=SHORT_COOLDOWN)
    controller.interface.recovery = datetime.timedelta(seconds=SHORT_RECOVERY)
    controller.laser_process.ser = dummy_serial
    return controller, dummy_serial


def test_instantiate_controller(controller_dummy):
    controller, dummy_serial = controller_dummy
    controller.start()
    assert controller.laser_process.is_alive()
    controller.stand_down()
    assert not controller.laser_process.is_alive()


def test_commander_with(controller_dummy):
    controller, dummy_serial = controller_dummy
    with controller:
        assert controller.laser_process.is_alive()
    assert not controller.laser_process.is_alive()


def test_fire_once(controller_dummy):
    controller, dummy_serial = controller_dummy
    with controller:
        controller.fire_once()
    log = dummy_serial.read_log()
    assert len(log) == 1
    assert log[0]['op'] == WRITE
    assert log[0]['msg'] == FIRE


def test_fire_multiple(controller_dummy):
    controller, dummy_serial = controller_dummy
    with controller:
        controller.fire_multiple(3)
    log = dummy_serial.read_log()
    assert len(log) == 3
    assert all(line['op'] == WRITE for line in log)
    assert all(line['msg'] == FIRE for line in log)
    for this, that in zip(log, log[1:]):
        assert that['time'] - this['time'] >= datetime.timedelta(seconds=SHORT_COOLDOWN)


def test_fire_at_will(controller_dummy):
    controller, dummy_serial = controller_dummy
    with controller:
        controller.fire_at_will()
        time.sleep(SHORT_COOLDOWN*6)
    log = dummy_serial.read_log()
    assert len(log) > 3  # allow some time for loop execution etc.
    assert all(line['op'] == WRITE for line in log)
    assert all(line['msg'] == FIRE for line in log)
    for this, that in zip(log, log[1:]):
        assert that['time'] - this['time'] >= datetime.timedelta(seconds=SHORT_COOLDOWN)


def test_last_fired(controller_dummy):
    controller, dummy_serial = controller_dummy
    with controller:
        controller.fire_once()
        first_shot = controller.last_fired
        controller.fire_once()
        second_shot = controller.last_fired

    assert second_shot - first_shot > datetime.timedelta(seconds=SHORT_COOLDOWN)
