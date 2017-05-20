from multiprocessing import Queue
from multiprocessing.queues import Empty
import time

import pytest
from mock import Mock, patch

from utils.shooting import DeadDrop, LaserCommander, LaserProcess


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

