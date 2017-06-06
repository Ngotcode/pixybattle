#!/usr/bin/env python
import os
import json
import logging
from io import BytesIO
import random

import tweepy
from enum import Enum

from utils.constants import ROOT_DIR, TWEET_PROB
from utils.bot_logging.image_logging import ImageCreator

logger = logging.getLogger(__name__)

for logger_name in ['requests', 'requests_oauthlib', 'oauthlib']:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

CREDENTIALS_PATH = os.path.join(ROOT_DIR, 'team4_keys.json')
SAYINGS_ROOT = os.path.join(ROOT_DIR, 'sayings')


class Sayings(Enum):
    STARTING_UP = 'starting_up.txt'
    LASER_FIRING = 'laser_firing.txt'
    RECEIVED_HIT = 'received_hit.txt'
    MOVING = 'moving.txt'
    SHUTTING_DOWN = 'shutting_down.txt'
    RANDOM = 'random.txt'


def pick_saying(saying):
    with open(os.path.join(SAYINGS_ROOT, saying.value)) as f:
        lines = f.read().strip().split('\n')

    return random.choice(lines)


class Tweeter(object):
    api = None

    def __init__(self, api=None):
        """

        Parameters
        ----------
        api
            By default, tweepy API instance is created using credentials in a json file. For testing purposes,
            a dummy API can be passed in here.
        """
        self.image_creator = ImageCreator()

        if self.api is None:
            if api is None:
                with open(CREDENTIALS_PATH) as f:
                    cred = json.load(f)

                auth = tweepy.OAuthHandler(cred['consumer_key'], cred['consumer_secret'])
                auth.set_access_token(cred['access_token'], cred['access_secret'])

                api = tweepy.API(auth)
            type(self).api = api

    def tweet(self, msg):
        """Tweet the given message. The message is not validated for length etc."""
        self.api.update_status(msg)

    def tweet_saying(self, saying):
        msg = pick_saying(saying)
        self.tweet(msg)

    def tweet_blocks(self, blocks, msg='', title=None, **kwargs):
        """Tweet an image of a sequence of blocks"""
        buf = BytesIO(self.image_creator.save_bytes(blocks, title, **kwargs))
        buf.seek(0)
        self.api.update_with_media('image.png', status=msg, file=buf)


class ProbabilisticTweeter(object):
    def __init__(self, api=None, default_prob=TWEET_PROB, seed=None):
        self.tweeter = Tweeter(api)
        self.random = random.Random(seed)
        self.default_prob = default_prob

    def permit(self, p=None):
        return self.random.random() < (p if p is None else self.default_prob)

    def tweet(self, msg, p=None):
        if self.permit(p):
            self.tweeter.tweet(msg)

    def tweet_saying(self, saying, p=None):
        if self.permit(p):
            self.tweeter.tweet_saying(saying)

    def tweet_blocks(self, blocks, msg='', title=None, p=None, **kwargs):
        if self.permit(p):
            self.tweeter.tweet_blocks(blocks, msg=msg, title=title, **kwargs)


if __name__ == '__main__':
    import sys
    try:
        msg = sys.argv[1]
    except IndexError:
        msg = "Testing one two three... is this thing on?"

    tweeter = Tweeter()
    tweeter.tweet(msg)
