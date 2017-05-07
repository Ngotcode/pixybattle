from collections import namedtuple
import os
import logging

import pytest

from utils import bot_logging

DEBUG = False

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'image_test')

FakeBlock = namedtuple('FakeBlock', ['x', 'y', 'width', 'height', 'angle', 'signature'])

logger = logging.getLogger('tests.image_test')


@pytest.fixture
def fake_blocks():
    return (
        FakeBlock(200, 200, 500, 500, 0, 1),
        FakeBlock(500, 500, 400, 400, 0, 2)
    )


@pytest.fixture
def image_creator():
    return bot_logging.ImageCreator()


def empty_output_dir():
    logging.debug('Emptying output directory %s', OUTPUT_DIR)
    for filename in os.listdir(OUTPUT_DIR):
        filepath = os.path.join(OUTPUT_DIR, filename)
        os.remove(filepath)


def setup_module():
    logging.info('Setting up %s module', __name__)
    if os.path.isdir(OUTPUT_DIR):
        empty_output_dir()
    else:
        logging.debug('Creating output directory %s', OUTPUT_DIR)
        os.makedirs(OUTPUT_DIR)


def teardown_module():
    if not DEBUG:
        empty_output_dir()


def test_image_creator(image_creator, fake_blocks):
    output_path = os.path.join(OUTPUT_DIR, 'two_overlapping_blocks.png')

    image_creator.save_file(fake_blocks, output_path, 'this is a title')
    assert len(image_creator._patches) == 0
    assert os.path.isfile(output_path)


def test_image_creator_multiple(image_creator, fake_blocks):
    for idx, fake_block in enumerate(fake_blocks):
        output_path = os.path.join(OUTPUT_DIR, 'single_block_{}.png'.format(idx))

        image_creator.save_file([fake_block], output_path, 'this is a title')
        assert len(image_creator._patches) == 0
        assert os.path.isfile(output_path)
