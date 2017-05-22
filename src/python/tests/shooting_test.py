from multiprocessing import Process
from multiprocessing.queues import Empty
import time

import pytest
from mock import Mock, patch

from utils.shooting import DeadDrop, LaserCommander, LaserProcess


class DeadDropTestProcess(Process):
    def __init__(self, dead_drop, item):
        super(DeadDropTestProcess, self).__init__()
        self.dead_drop = dead_drop
        self.item = item

    def run(self):
        pass


class DeadDropTestPutProcess(DeadDropTestProcess):
    def run(self):
        self.dead_drop.put(self.item)


class DeadDropTestGetProcess(DeadDropTestProcess):
    def run(self):
        assert self.dead_drop.get() == self.item


# DEADDROP TESTS


@pytest.fixture
def dead_drop():
    return DeadDrop()


def test_deaddrop_multiple_put(dead_drop):
    dead_drop.put('item')
    assert dead_drop.qsize() == 1
    item2 = 'another_item'
    dead_drop.put(item2)
    assert dead_drop.qsize() == 1
    assert dead_drop.q.get() == item2


def test_deaddrop_get(dead_drop):
    item = 'item'
    dead_drop.put(item)
    assert dead_drop.get() == item


def test_deaddrop_get_default(dead_drop):
    assert dead_drop.empty()
    item = 'item'
    assert dead_drop.get(item) == item


def test_deaddrop_throw_empty(dead_drop):
    with pytest.raises(Empty):
        dead_drop.get()


def test_deaddrop_get_across_processes(dead_drop):
    item = 'item'
    ddtp = DeadDropTestGetProcess(dead_drop, item)
    ddtp.start()
    time.sleep(0.01)
    assert dead_drop.get() == item
    ddtp.join()


def test_deaddrop_put_across_processes(dead_drop):
    item = 'item'
    ddtp = DeadDropTestPutProcess(dead_drop, item)
    dead_drop.put(item)
    time.sleep(0.1)
    ddtp.start()
    ddtp.join()
