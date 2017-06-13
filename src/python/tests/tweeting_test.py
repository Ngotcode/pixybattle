import os
import logging

import pytest

from utils.bot_logging import Tweeter
from utils.
from utils.constants import Situation


logger = logging.getLogger('tests.tweeting_test')

DEBUG = True

SEED = 1
NORMAL_TWEET_PROB = 1
LOW_TWEET_PROB = 0.5

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'tweeting_test')


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


class DummyApi(object):
    def __init__(self, test_name):
        self.path = os.path.join(OUTPUT_DIR, test_name + '.txt')
        self.img_dir = os.path.join(OUTPUT_DIR, test_name)
        if not os.path.isdir(self.img_dir):
            os.makedirs(self.img_dir)
        self.img_count = 1

    def update_status(self, msg):
        with open(self.path, 'a') as f:
            f.write(msg)

    def update_with_meda(self, path, status='', file=None):
        output_path = os.path.join(self.img_dir, '{}.png'.format(self.img_count))

        with open(self.path, 'a') as f:
            f.write(status + '|{}'.format(output_path))

        with open(output_path, 'wb') as f:
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
    api = DummyApi(os.path.join(OUTPUT_DIR, request.function.__name__))
    return Tweeter(default_prob=NORMAL_TWEET_PROB, seed=SEED, api=api)


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



def test_tweets_image()



