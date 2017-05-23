import os
from multiprocessing import Process, Queue
from multiprocessing.queues import Empty
import time
import logging
import csv

import pytest

from utils.shooting import get_with_default, put_singular, LaserCommander

logger = logging.getLogger('tests.shooting_test')

DEBUG = False

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'shooting_test')
SHORT_COOLDOWN = 0.1  # seconds

READ = 'READ'
WRITE = 'WRITE'
FIRE = r'FIRE\n'


class SingletonQueueTestProcess(Process):
    def __init__(self, queue, item):
        super(SingletonQueueTestProcess, self).__init__()
        self.queue = queue
        self.item = item

    def run(self):
        pass


class SingletonQueueTestPutProcess(SingletonQueueTestProcess):
    def run(self):
        self.queue.put(None)
        put_singular(self.queue, self.item)


class SingletonQueueTestGetProcess(SingletonQueueTestProcess):
    def run(self):
        assert self.queue.get() == self.item


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


# DEADDROP TESTS


@pytest.fixture
def singleton_queue():
    return Queue(1)


def test_put_singular_single(singleton_queue):
    assert singleton_queue.empty()
    put_singular(singleton_queue, 'item')
    assert singleton_queue.qsize() == 1


def test_put_singular_multiple(singleton_queue):
    assert singleton_queue.empty()
    singleton_queue.put('item')
    item2 = 'another_item'
    put_singular(singleton_queue, item2)
    assert singleton_queue.qsize() == 1
    assert singleton_queue.get() == item2


def test_get_default_exists(singleton_queue):
    assert singleton_queue.empty()
    singleton_queue.put('item')
    assert singleton_queue.qsize() == 1
    output = get_with_default(singleton_queue, 'not_item')
    assert output == 'item'


def test_get_default_not_exists(singleton_queue):
    assert singleton_queue.empty()
    item = 'item'
    output = get_with_default(singleton_queue, item)
    assert output == item


def test_get_default_throw_empty(singleton_queue):
    with pytest.raises(Empty):
        get_with_default(singleton_queue)


def test_get_across_processes(singleton_queue):
    item = 'item'
    ddtp = SingletonQueueTestPutProcess(singleton_queue, item)
    ddtp.start()
    time.sleep(0.5)
    assert singleton_queue.get() == item
    ddtp.join()


def test_put_across_processes(singleton_queue):
    item = 'item'
    ddtp = SingletonQueueTestGetProcess(singleton_queue, item)
    singleton_queue.put(item)
    ddtp.start()
    ddtp.join()


class DummySerial(object):
    def __init__(self, output_filename=None, canned_responses=None):
        self.canned_responses = dict() if canned_responses is None else canned_responses
        self.next_response = ''
        self.output_path = self.set_filename(output_filename)

    def write(self, arg):
        self.log(WRITE, arg)
        self.next_response = self.canned_responses.get(arg, '')

    def read(self):
        response = self.next_response
        self.next_response = ''
        self.log(READ, response)
        return response

    def log(self, operation, msg=''):
        with open(self.output_path, 'a') as f:
            f.write(
                '{}\t{}\t{}\n'.format(time.time(), operation, msg.encode('string_escape') if msg else 'EMPTY_MESSAGE')
            )

    def set_filename(self, filename):
        if filename is None:
            return
        self.output_path = os.path.join(OUTPUT_DIR, filename)
        return self.output_path

    def read_log(self):
        with open(self.output_path) as f:
            reader = csv.DictReader(f, fieldnames=['time', 'op', 'msg'], delimiter='\t')
            return [line for line in reader]


@pytest.fixture
def cmdr_dummy(request):
    commander = LaserCommander()
    dummy_serial = DummySerial(request.function.__name__ + '.txt')
    commander._laser.cooldown = SHORT_COOLDOWN
    commander._laser.ser = dummy_serial
    return commander, dummy_serial


def test_instantiate_commander(cmdr_dummy):
    cmdr, dummy_serial = cmdr_dummy
    cmdr.start()
    assert cmdr._laser.is_alive()
    cmdr.stand_down()
    assert not cmdr._laser.is_alive()


def test_commander_with(cmdr_dummy):
    cmdr, dummy_serial = cmdr_dummy
    with cmdr:
        assert cmdr._laser.is_alive()
    assert not cmdr._laser.is_alive()


def test_fire_once(cmdr_dummy):
    cmdr, dummy_serial = cmdr_dummy
    with cmdr:
        cmdr.fire_once()
    log = dummy_serial.read_log()
    assert len(log) == 1
    assert log[0]['op'] == WRITE
    assert log[0]['msg'] == FIRE


def test_fire_multiple(cmdr_dummy):
    cmdr, dummy_serial = cmdr_dummy
    with cmdr:
        cmdr.fire_multiple(3)
    log = dummy_serial.read_log()
    assert len(log) == 3
    assert all(line['op'] == WRITE for line in log)
    assert all(line['msg'] == FIRE for line in log)
    for this, that in zip(log, log[1:]):
        assert float(that['time']) - float(this['time']) > SHORT_COOLDOWN


def test_fire_at_will(cmdr_dummy):
    cmdr, dummy_serial = cmdr_dummy
    with cmdr:
        cmdr.fire_at_will()
        time.sleep(SHORT_COOLDOWN*6)
    log = dummy_serial.read_log()
    assert len(log) > 3  # allow some time for loop execution etc.
    assert all(line['op'] == WRITE for line in log)
    assert all(line['msg'] == FIRE for line in log)
    for this, that in zip(log, log[1:]):
        assert float(that['time']) - float(this['time']) > SHORT_COOLDOWN


def test_last_fired(cmdr_dummy):
    cmdr, dummy_serial = cmdr_dummy
    with cmdr:
        cmdr.fire_once()
        first_shot = cmdr.last_fired
        cmdr.fire_once()
        second_shot = cmdr.last_fired

    assert second_shot - first_shot > SHORT_COOLDOWN
