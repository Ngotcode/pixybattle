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
>>> from utils.constants import Situation
>>> print([situation.name for situation in Situation])  # see what situations are available

To tweet a canned statement, simply
>>> tweeter.tweet_canned(Situation.LASER_FIRING)

All of the tweet methods take the optional argument `p`, which defines the probability of sending that particular
tweet, to override the instance default set in the constructor.

To add new canned statements, simply edit the files corresponding to each situation in the `tweets` directory in the
pixybattle root.

Tweets are not validated for length etc., user beware!
"""
import os
import json
import logging
from io import BytesIO
import random

import tweepy

from utils.constants import ROOT_DIR, TWEET_DEFAULT_PROB, Situation
from utils.bot_logging.image_logging import ImageCreator

logger = logging.getLogger(__name__)

for logger_name in ['requests', 'requests_oauthlib', 'oauthlib']:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

CREDENTIALS_PATH = os.path.join(ROOT_DIR, 'team4_keys.json')
CANNED_TWEETS_ROOT = os.path.join(ROOT_DIR, 'tweets')


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

        if api is not None:
            self.api = api
        elif self.api is None:
            try:
                with open(CREDENTIALS_PATH) as f:
                    cred = json.load(f)

                auth = tweepy.OAuthHandler(cred['consumer_key'], cred['consumer_secret'])
                auth.set_access_token(cred['access_token'], cred['access_secret'])

                api = tweepy.API(auth)
            except IOError:
                logger.warn('API credentials not found at {}. Tweets will not be submitted.'.format(CREDENTIALS_PATH))
            type(self).api = api

    def _pick_canned_tweet(self, situation):
        """
        Randomly select a message for the given situation.

        Parameters
        ----------
        situation : Situation
            Enum for which newline-separated file to pick message from

        Returns
        -------
        str
        """
        with open(os.path.join(CANNED_TWEETS_ROOT, situation.value)) as f:
            lines = f.read().strip().split('\n')

        return self.random.choice(lines)

    def _permit(self, p=None):
        """Whether to permit a tweet to go through"""
        if self.api is None:
            logger.debug('No twitter API available, tweet will not be submitted.')
            return False
        is_permitted = self.random.random() <= (p if p is not None else self.default_prob)
        logger.debug('Tweeting' if is_permitted else 'Not tweeting (randomly)')
        return is_permitted

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

    def tweet_canned(self, situation, p=None):
        """
        Tweet a random one of a number of pre-defined situations.

        Parameters
        ----------
        situation : Situation
            Enum for which newline-separated file to pick message from
        p : float
            Between 0 and 1, the probability that this tweet will be sent

        Returns
        -------
        bool
            Whether the tweet sent
        """
        if self._permit(p):
            msg = self._pick_canned_tweet(situation)
            try:
                self.api.update_status(msg)
            except tweepy.error.TweepError:
                pass
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
