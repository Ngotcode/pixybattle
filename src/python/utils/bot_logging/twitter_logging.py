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
from datetime import datetime
import shutil
import multiprocessing as mp
import Queue
from functools import wraps
import time

import tweepy

from utils.constants import ROOT_DIR, TWEET_DEFAULT_PROB, Situation, STARTED
from utils.bot_logging.image_logging import ImageCreator

logger = logging.getLogger(__name__)

for logger_name in ['requests', 'requests_oauthlib', 'oauthlib']:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

CREDENTIALS_PATH = os.path.join(ROOT_DIR, 'team4_keys.json')
CANNED_TWEETS_ROOT = os.path.join(ROOT_DIR, 'tweets')


def get_timestamp():
    delta = datetime.now() - STARTED
    return '{:.2f}: '.format(delta.total_seconds())


class TweeterProcess(mp.Process):
    def __init__(self, queue, default_prob=TWEET_DEFAULT_PROB, seed=None, api=None):
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
        super(TweeterProcess, self).__init__()
        self.queue = queue
        self.api = api

        self.image_creator = None
        self.default_prob = default_prob
        self.seed = seed
        self.canned_tweets = None
        self.random = None

    def setup(self):
        self.image_creator = ImageCreator()
        self.random = random.Random(self.seed)

        self.canned_tweets = dict()
        for situation in Situation:
            with open(os.path.join(CANNED_TWEETS_ROOT, situation.value)) as f:
                self.canned_tweets[situation] = json.load(f)

    def run(self):
        self.setup()

        while True:
            key, args, kwargs = self.queue.get()
            if key == 'tweet':
                self.tweet(*args, **kwargs)
            elif key == 'tweet_canned':
                self.tweet_canned(*args, **kwargs)
            elif key == 'tweet_blocks':
                self.tweet_blocks(*args, **kwargs)
            elif key == 'kill':
                break

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
        if not self._permit(p):
            return False

        self.api.update_status(get_timestamp() + msg)
        return True

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
        if not self._permit(p):
            return False

        try:
            selected = random.choice(self.canned_tweets[situation])

            if 'path' in selected:
                self.api.update_with_media(
                    os.path.join(CANNED_TWEETS_ROOT, selected['path']), status=get_timestamp() + selected.get('msg', '')
                )
            else:
                self.api.update_status(get_timestamp() + selected.get('msg', ''))

        except (tweepy.error.TweepError, IndexError, KeyError) as e:
            logger.exception(str(e))
            return False
        return True

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
        if not self._permit(p):
            return False

        buf = BytesIO(self.image_creator.save_bytes(blocks, title, **kwargs))
        buf.seek(0)

        try:
            self.api.update_with_media('image.png', status=get_timestamp() + msg, file=buf)
        except tweepy.error.TweepError as e:
            logger.exception(str(e))
            return False

        return True


class Tweeter(object):
    tweeter_process = None
    api = None

    def __init__(self, default_prob=TWEET_DEFAULT_PROB, seed=None, api=None):
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

        if self.tweeter_process:
            self.queue = self.tweeter_process.queue
        else:
            self.queue = mp.Queue()
            self.tweeter_process = TweeterProcess(self.queue, default_prob, seed, self.api)

    def _put(self, command, *args, **kwargs):
        try:
            self.queue.put((command, args, kwargs), False)
        except Queue.Full:
            logger.exception('Tweet queue is full')
            pass
        except Exception:
            logger.exception('Some sort of failure in queue handling')
            pass

    @wraps(TweeterProcess.tweet)
    def tweet(self, *args, **kwargs):
        self._put('tweet', *args, **kwargs)

    @wraps(TweeterProcess.tweet_blocks)
    def tweet_blocks(self, *args, **kwargs):
        self._put('tweet_blocks', *args, **kwargs)

    @wraps(TweeterProcess.tweet_canned)
    def tweet_canned(self, *args, **kwargs):
        self._put('tweet_canned', *args, **kwargs)

    def start(self):
        if not self.tweeter_process.is_alive():
            self.tweeter_process.start()

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def stop(self):
        while self.queue.qsize():
            try:
                self.queue.get(block=False)
            except Queue.Empty:
                break

        self._put('kill')

        killed_at = datetime.now()
        while self.tweeter_process.is_alive():
            time.sleep(0.01)
            if (datetime.now() - killed_at).total_seconds() > 1:
                self.tweeter_process.terminate()
        type(self).tweeter_process = None


class DummyTweepyApi(object):
    def __init__(self, output_path_prefix):
        if output_path_prefix.endswith('/'):
            output_path_prefix = output_path_prefix[:-1]

        self.path = os.path.join(output_path_prefix + '.txt')
        self.img_dir = os.path.join(output_path_prefix)

        if not os.path.isdir(self.img_dir):
            logger.debug('Creating image output dir at {}'.format(self.img_dir))
            os.makedirs(self.img_dir)
        with open(self.path, 'w'):
            logger.debug('Creating output file at {}'.format(self.path))
        self.img_count = 0

    def update_status(self, msg):
        with open(self.path, 'a') as f:
            logger.debug('Twitter API updating status with "{}" to {}'.format(msg, self.path))
            f.write(msg + '\n')

    def update_with_media(self, path='image.png', status='', file=None):
        self.img_count += 1
        ext = os.path.splitext(path)[1]
        output_path = os.path.join(self.img_dir, '{}{}'.format(self.img_count, ext))

        with open(self.path, 'a') as f:
            logger.debug(
                'Twitter API updating status with {} and image to {}'.format(status, output_path, self.path)
            )
            f.write(status + '|{}\n'.format(output_path))

        if file:
            with open(output_path, 'wb') as f:
                logger.debug('Twitter API creating image at {}'.format(output_path))
                f.write(file.read())
        else:
            logger.debug('Twitter API copying image to {}'.format(output_path))
            shutil.copy(path, output_path)


if __name__ == '__main__':
    import sys
    try:
        msg = sys.argv[1]
    except IndexError:
        msg = "Testing one two three... is this thing on?"

    tweeter = Tweeter(default_prob=1)
    tweeter.tweet(msg)
