import os
import json
import logging
from io import BytesIO

import tweepy

from utils.constants import ROOT_DIR
from utils.bot_logging.image_logging import ImageCreator

logger = logging.getLogger(__name__)

CREDENTIALS_PATH = os.path.join(ROOT_DIR, 'team4_keys.json')
MAX_LENGTH = 140
CHARACTERS_RESERVED = 24


class Tweeter(object):
    _instance = None

    def __init__(self):
        with open(CREDENTIALS_PATH) as f:
            cred = json.load(f)

        auth = tweepy.OAuthHandler(cred['consumer_key'], cred['consumer_secret'])
        auth.set_access_token(cred['access_token'], cred['access_secret'])

        self.api = tweepy.API(auth)
        self.image_creator = ImageCreator()

    def tweet(self, msg):
        self.api.update_status(msg)

    def tweet_blocks(self, blocks, msg='', title=None, **kwargs):
        buf = BytesIO(self.image_creator.save_bytes(blocks, title, **kwargs))
        buf.seek(0)
        self.api.update_with_media('image.png', status=msg, file=buf)

    @classmethod
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = cls()

        return cls._instance
