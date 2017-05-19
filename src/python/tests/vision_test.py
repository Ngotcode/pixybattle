#!/usr/bin/env python

from __future__ import division
import logging
from random import Random
from copy import copy

import pytest
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt

from utils import vision
from utils.bot_logging import set_log_level

logger = logging.getLogger(__name__)
set_log_level(logging.DEBUG)

SMALL_NUMBER = 0.01

TARGET_SIGMA = 0.01
TARGET_CONFIDENCE = 0.95
REPLICATES = 1000


# CONVENIENCE CLASSES


class BlockFactory(object):
    def __init__(self, signature=1, width=1.0, height=1.0):
        self.signature = signature
        self.width = width
        self.height = height

    def block(self, x=0.0, y=0.0, width=None, height=None):
        if width is None:
            width = self.width
        if height is None:
            height = self.height
        return vision.GenericBlock(self.signature, x, y, width, height)


# GENERICBLOCK TESTS


@pytest.mark.parametrize('bottom_left1,bottom_left2,expected', [
    ((0, 0), (0, 0), 1),
    ((0, 0), (0.5, 0), 0.5),
    ((0, 0), (0.5, 0.5), 0.25),
    ((0, 0), (2, 2), 0),
    ((0, 0), (1, 0), 0)
])
def test_intersection_area(bottom_left1, bottom_left2, expected):
    factory = BlockFactory()
    block1, block2 = factory.block(*bottom_left1), factory.block(*bottom_left2)

    assert block1.intersection_area(block2) == expected


@pytest.mark.parametrize('bottom_left1,bottom_left2,expected', [
    ((0, 0), (0, 0), 1),
    ((0, 0), (0.5, 0), 0.5),
    ((0, 0), (0.5, 0.5), 0.25),
    ((0, 0), (2, 2), 0),
    ((0, 0), (1, 0), 0)
])
def test_intersection_ppn(bottom_left1, bottom_left2, expected):
    factory = BlockFactory()
    block1, block2 = factory.block(*bottom_left1), factory.block(*bottom_left2)

    assert block1.intersection_ppn(block2) == expected


@pytest.mark.parametrize('bottom_left1,bottom_left2,expected', [
    ((0, 0), (0.5, 0.5), True),
    ((0, 0), (2, 2), False),
    ((0, 0), (1, 0), False)
])
def test_intersects(bottom_left1, bottom_left2, expected):
    factory = BlockFactory()
    block1, block2 = factory.block(*bottom_left1), factory.block(*bottom_left2)

    assert block1.intersects(block2) == expected


@pytest.mark.parametrize('bottom_left1,bottom_left2,expected', [
    ((0, 0), (SMALL_NUMBER, 0), True),
    ((0, 0), (1, 1), False)
])
def test_nearly_equals(bottom_left1, bottom_left2, expected):
    # todo: just test up to threshold sigma
    factory = BlockFactory()
    block1, block2 = factory.block(*bottom_left1), factory.block(*bottom_left2)

    assert block1.nearly_equals(block2) == expected


def test_merge_2_class():
    factory = BlockFactory()
    block1, block2 = factory.block(0, 0), factory.block(1, 1, 2, 2)

    block3 = vision.GenericBlock.merge_blocks(block1, block2)

    assert block3.x == 0.5
    assert block3.y == 0.5
    assert block3.width == 1.5
    assert block3.height == 1.5


def test_equality():
    factory = BlockFactory()
    assert factory.block() == factory.block()


def test_near_equality_signature():
    factory = BlockFactory()
    block1 = factory.block()
    block2 = factory.block()
    block2.signature = 2

    assert not block1.nearly_equals(block2)


def test_near_equality_power():
    block = vision.GenericBlock(1, 0, 0, 1, 1)
    result = vision.near_equality_accuracy_for_sigma(block, TARGET_SIGMA, REPLICATES)

    assert result > TARGET_CONFIDENCE


def test_nearly_equal_pairs_combinations():
    factory = BlockFactory()
    block1, block2, block3 = factory.block(), factory.block(1, 1), factory.block()

    pairs = vision.nearly_equal_pairs((block1, block2, block3))

    assert len(pairs) == 1
    pair = pairs.pop()
    assert block1 in pair
    assert block3 in pair


def test_nearly_equal_pairs():
    factory = BlockFactory()
    block1, block2 = factory.block(), factory.block(SMALL_NUMBER, SMALL_NUMBER)
    block3, block4 = factory.block(), factory.block(1, 1)

    pairs = vision.nearly_equal_pairs((block1, block2), (block3, block4))

    assert len(pairs) == 2
    assert (block1, block3) in pairs
    assert (block2, block3) in pairs


def test_signature_not_equal():
    block1 = vision.GenericBlock(0, 0, 0, 1, 1)
    block2 = vision.GenericBlock(1, 0, 0, 1, 1)

    assert block1.nearly_equals(block2) is False


def test_merge_blocks_combinations():
    factory = BlockFactory()
    block1, block2, block3 = factory.block(), factory.block(1, 1), factory.block(SMALL_NUMBER, SMALL_NUMBER)

    new_blocks = vision.merge_similar_blocks((block1, block2, block3))

    assert len(new_blocks) == 2
    assert block2 in new_blocks
    assert vision.GenericBlock.merge_blocks(block1, block3) in new_blocks


def test_merge_blocks():
    factory = BlockFactory()
    block1, block2 = factory.block(), factory.block(SMALL_NUMBER*2, SMALL_NUMBER*2)
    block3, block4 = factory.block(SMALL_NUMBER, SMALL_NUMBER), factory.block(1, 1)

    new_blocks = vision.merge_similar_blocks((block1, block2), (block3, block4))

    assert len(new_blocks) == 2
    assert block4 in new_blocks
    assert vision.GenericBlock.merge_blocks(block1, block2, block3) in new_blocks
# SCENE TESTS

def test_merge_scene():
    factory = BlockFactory()
    block1, block2 = factory.block(), factory.block(1, 1)
    block3, block4 = factory.block(SMALL_NUMBER, SMALL_NUMBER), factory.block(2, 2)
    scene1 = vision.Scene((block1, block2))
    scene2 = vision.Scene((block3, block4))

    scene3 = scene1.merge(scene2)

    assert isinstance(scene3, vision.Scene)
    assert block2 in scene3.blocks
    assert block4 in scene3.blocks
    assert vision.GenericBlock.merge_blocks(block1, block3) in scene3.blocks


def test_diff_scene_extra():
    factory = BlockFactory()
    block1, block2, block3 = factory.block(), factory.block(SMALL_NUMBER, SMALL_NUMBER), factory.block(1, 1)
    scene1 = vision.Scene([block1])
    scene2 = vision.Scene([block2, block3])

    added, subtracted = scene1.diff(scene2)

    assert len(subtracted) == 0
    assert len(added) == 1
    assert block3 in added


def test_diff_scene_signature():
    factory = BlockFactory()
    block1 = factory.block()
    block2 = factory.block()
    block2.signature = 2

    added, subtracted = vision.Scene([block1]).diff(vision.Scene([block2]))

    assert len(added) == 1
    assert block2 in added
    assert len(subtracted) == 1
    assert block1 in subtracted
