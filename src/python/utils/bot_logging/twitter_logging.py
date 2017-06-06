#!/usr/bin/env python
import os
import json
import logging
from io import BytesIO
import random

import tweepy

from utils.constants import ROOT_DIR, TWEET_PROB
from utils.bot_logging.image_logging import ImageCreator

logger = logging.getLogger(__name__)

for logger_name in ['requests', 'requests_oauthlib', 'oauthlib']:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

CREDENTIALS_PATH = os.path.join(ROOT_DIR, 'team4_keys.json')


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

    def tweet_blocks(self, blocks, msg='', title=None, **kwargs):
        """Tweet an image of a sequence of blocks"""
        buf = BytesIO(self.image_creator.save_bytes(blocks, title, **kwargs))
        buf.seek(0)
        self.api.update_with_media('image.png', status=msg, file=buf)


class ProbabilisticTweeter(Tweeter):
    def __init__(self, api=None, default_prob=TWEET_PROB, seed=None):
        super(ProbabilisticTweeter, self).__init__(api)
        self.random = random.Random(seed)
        self.default_prob = default_prob

    def tweet(self, msg, p=None):
        if self.random.random() < (p if p is None else self.default_prob):
            super(ProbabilisticTweeter, self).tweet(msg)

    def tweet_blocks(self, blocks, msg='', title=None, p=None, **kwargs):
        if self.random.random() < (p if p is None else self.default_prob):
            super(ProbabilisticTweeter, self).tweet_blocks(blocks, msg='', title=None, **kwargs)


if __name__ == '__main__':
    import sys
    try:
        msg = sys.argv[1]
    except IndexError:
        msg = "Testing one two three... is this thing on?"

    tweeter = Tweeter()
    tweeter.tweet(msg)
