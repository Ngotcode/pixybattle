import os
import shutil
import logging
from collections import namedtuple

import pytest

from utils.bot_logging import Tweeter
from utils.constants import Situation


logger = logging.getLogger('tests.tweeting_test')

DEBUG = True

SEED = 1
NORMAL_TWEET_PROB = 1
LOW_TWEET_PROB = 0.5

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'tweeting_test')

FakePixyBlock = namedtuple('FakeBlock', ['x', 'y', 'width', 'height', 'angle', 'signature'])


def empty_output_dir():
    logging.debug('Emptying output directory %s', OUTPUT_DIR)
    for root, dirs, files in os.walk(OUTPUT_DIR):
        for fname in files:
            os.remove(os.path.join(root, fname))
        for dname in dirs:
            shutil.rmtree(os.path.join(root, dname))


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


class DummyApi(object):
    def __init__(self, test_name):
        self.path = os.path.join(OUTPUT_DIR, test_name + '.txt')
        self.img_dir = os.path.join(OUTPUT_DIR, test_name)
        if not os.path.isdir(self.img_dir):
            logger.debug('Creating image output dir at {}'.format(self.img_dir))
            os.makedirs(self.img_dir)
        with open(self.path, 'w'):
            logger.debug('Creating output file at {}'.format(self.path))
        self.img_count = 1

    def update_status(self, msg):
        with open(self.path, 'a') as f:
            logger.debug('Twitter API updating status with "{}" to {}'.format(msg, self.path))
            f.write(msg + '\n')

    def update_with_media(self, path, status='', file=None):
        output_path = os.path.join(self.img_dir, '{}.png'.format(self.img_count))
        with open(self.path, 'a') as f:
            logger.debug(
                'Twitter API updating status with {} and image to {}'.format(status, output_path, self.path)
            )
            f.write(status + '|{}\n'.format(output_path))

        with open(output_path, 'wb') as f:
            logger.debug('Twitter API creating image at {}'.format(output_path))
            f.write(file.read())


def read_statuses(tweeter):
    with open(tweeter.api.path) as f:
        return f.read().strip().split('\n')


def check_image_paths(tweeter):
    for status in read_statuses(tweeter):
        if '.png' in status:
            path = status.split('|')[-1]
            assert os.path.isfile(path)


@pytest.fixture
def tweeter(request):
    api = DummyApi(request.function.__name__)
    tweeter = Tweeter(default_prob=NORMAL_TWEET_PROB, seed=SEED, api=api)
    logger.debug('Tweeter created with api path at {}'.format(tweeter.api.path))
    return tweeter


def test_tweets(tweeter):
    tweet_msg = 'this is a message'
    tweeter.tweet(tweet_msg)
    assert tweet_msg in read_statuses(tweeter)


def test_tweets_canned(tweeter):
    count = 0
    for situation in Situation:
        tweeter.tweet_canned(situation)
        count += 1

    assert len(read_statuses(tweeter)) == count


@pytest.fixture
def blocks():
    return [
        FakePixyBlock(200, 200, 500, 500, 0, 1),
        FakePixyBlock(500, 500, 400, 400, 0, 2)
    ]


def test_tweets_image(tweeter, blocks):
    tweeter.tweet_blocks(blocks)
    check_image_paths(tweeter)


def test_tweets_image_with_status(tweeter, blocks):
    tweet_msg = 'this is a message'
    tweeter.tweet_blocks(blocks, msg=tweet_msg)
    check_image_paths(tweeter)
    status = read_statuses(tweeter)[0]
    assert tweet_msg in status


def test_tweets_low_prob(tweeter):
    tweeter.default_prob = LOW_TWEET_PROB
    attempts = 10
    for idx in range(attempts):
        tweeter.tweet('Tweeted on attempt {}'.format(idx))

    statuses = read_statuses(tweeter)
    assert 0 < len(statuses) < attempts
