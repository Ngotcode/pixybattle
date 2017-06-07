#!/usr/bin/env python
"""
This module allows the robot to tweet.

Before it can be used, the `team4_keys.json` file must be saved in the pixybattle root directory (this MUST NOT be
checked into git).

>>> from utils.bot_logging import Tweeter
>>> tweeter = Tweeter()

The `Tweeter` takes optional keyword arguments of `default_prob` (default set in constants.py,
sets the default probability of any given tweet actually being sent), and `seed` (default None, to control the random
number generator).

You can send basic text tweets:
>>> tweeter.tweet('This is a message')
Or create an image from a list of blocks and tweet that:
>>> tweeter.tweet_blocks(blocks, msg='Message to tweet with the image', title='Image title', **matplotlib_args)
(only `blocks` is required)

You can also randomly select a tweet from a pre-defined list appropriate to a given situation. The situations are
enumerated in the `Situation` class.
>>> from utils.bot_logging import Situation
>>> print([situation.name for situation in Situation])  # see what sayings are available

To tweet a saying, simply
>>> tweeter.tweet_canned(Situation.LASER_FIRING)

All of the tweet methods take the optional argument `p`, which defines the probability of sending that particular
tweet, to override the instance default set in the constructor.
"""
import os
import json
import logging
from io import BytesIO
import random

import tweepy
from enum import Enum

from utils.constants import ROOT_DIR, TWEET_DEFAULT_PROB
from utils.bot_logging.image_logging import ImageCreator

logger = logging.getLogger(__name__)

for logger_name in ['requests', 'requests_oauthlib', 'oauthlib']:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

CREDENTIALS_PATH = os.path.join(ROOT_DIR, 'team4_keys.json')
SAYINGS_ROOT = os.path.join(ROOT_DIR, 'sayings')


class Situation(Enum):
    STARTING_UP = 'starting_up.txt'
    LASER_FIRING = 'laser_firing.txt'
    RECEIVED_HIT = 'received_hit.txt'
    MOVING = 'moving.txt'
    SHUTTING_DOWN = 'shutting_down.txt'
    RANDOM = 'random.txt'


class Tweeter(object):
    api = None

    def __init__(self, default_prob=TWEET_DEFAULT_PROB, seed=None, api=None):
        """

        Parameters
        ----------
        default_prob : float
            Between 0 and 1, the default probability that any given tweet will be sent
        seed : int
            Seed for the random number generator
        api
            For testing purposes. Default will create a new tweepy.API instance
        """
        self.image_creator = ImageCreator()
        self.default_prob = default_prob
        self.random = random.Random(seed)

        if self.api is None:
            if api is None:
                with open(CREDENTIALS_PATH) as f:
                    cred = json.load(f)

                auth = tweepy.OAuthHandler(cred['consumer_key'], cred['consumer_secret'])
                auth.set_access_token(cred['access_token'], cred['access_secret'])

                api = tweepy.API(auth)
            type(self).api = api

    def _pick_saying(self, saying):
        """
        Randomly select a message for the given situation.

        Parameters
        ----------
        saying : Situation
            Enum for which newline-separated file to pick message from

        Returns
        -------
        str
        """
        with open(os.path.join(SAYINGS_ROOT, saying.value)) as f:
            lines = f.read().strip().split('\n')

        return self.random.choice(lines)

    def _permit(self, p=None):
        """Whether to permit a tweet to go through"""
        return self.random.random() < (p if p is None else self.default_prob)

    def tweet(self, msg, p=None):
        """
        Tweet the given message.

        Parameters
        ----------
        msg : str
            Message to tweet. This is not validated (for length etc.).
        p : float
            Between 0 and 1, the probability that this tweet will be sent

        Returns
        -------
        bool
            Whether the tweet sent
        """
        if self._permit(p):
            self.api.update_status(msg)
            return True
        return False

    def tweet_canned(self, saying, p=None):
        """
        Tweet a random one of a number of pre-defined sayings.

        Parameters
        ----------
        saying : Situation
            Enum for which newline-separated file to pick message from
        p : float
            Between 0 and 1, the probability that this tweet will be sent

        Returns
        -------
        bool
            Whether the tweet sent
        """
        if self._permit(p):
            msg = self._pick_saying(saying)
            self.api.update(msg)
            return True
        return False

    def tweet_blocks(self, blocks, p=None, msg='', title=None, **kwargs):
        """
        Tweet an image of a sequence of blocks

        Parameters
        ----------
        blocks : sequence
            Iterable sequence of Blocks, GenericBlock, or PixyBlock objects
        p : float
            Between 0 and 1, the probability that this tweet will be sent
        msg : str
            Message to tweet with the image (default empty string)
        title : str
            Title inside the image
        kwargs
            keyword arguments passed to `matplotlib.pyplot.savefig`

        Returns
        -------
        bool
            Whether the tweet sent
        """
        if self._permit(p):
            buf = BytesIO(self.image_creator.save_bytes(blocks, title, **kwargs))
            buf.seek(0)
            self.api.update_with_media('image.png', status=msg, file=buf)
            return True
        return False


if __name__ == '__main__':
    import sys
    try:
        msg = sys.argv[1]
    except IndexError:
        msg = "Testing one two three... is this thing on?"

    tweeter = Tweeter(default_prob=1)
    tweeter.tweet(msg)
