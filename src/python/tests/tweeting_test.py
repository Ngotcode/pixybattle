import os
import shutil
import logging
from collections import namedtuple

import pytest

from utils.bot_logging import Tweeter, DummyTweepyApi
from utils.constants import Situation


logger = logging.getLogger('tests.tweeting_test')

DEBUG = True

SEED = 1
NORMAL_TWEET_PROB = 1
LOW_TWEET_PROB = 0.5

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'tweeting_test')

FakePixyBlock = namedtuple('FakePixyBlock', ['x', 'y', 'width', 'height', 'angle', 'signature'])


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


def read_statuses(tweeter):
    with open(tweeter.api.path) as f:
        print('\033[1m' + f.read().strip().split('\n') + '\033[0m')
        return f.read().strip().split('\n')


def check_image_paths(tweeter):
    for status in read_statuses(tweeter):
        if '.png' in status:
            path = status.split('|')[-1]
            assert os.path.isfile(path)


@pytest.fixture
def tweeter(request):
    api = DummyTweepyApi(os.path.join(OUTPUT_DIR, request.function.__name__))
    tweeter_obj = Tweeter(default_prob=NORMAL_TWEET_PROB, seed=SEED, api=api)
    logger.debug('Tweeter created with api path at {}'.format(tweeter_obj.api.path))
    return tweeter_obj


def test_tweets(tweeter):
    tweet_msg = 'this is a message'
    with tweeter:
        tweeter.tweet(tweet_msg)
    assert read_statuses(tweeter)[0].endswith(tweet_msg)


def test_tweets_canned(tweeter):
    count = 0
    with tweeter:
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
    with tweeter:
        tweeter.tweet_blocks(blocks)
    check_image_paths(tweeter)


def test_tweets_image_with_status(tweeter, blocks):
    tweet_msg = 'this is a message'
    with tweeter:
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
