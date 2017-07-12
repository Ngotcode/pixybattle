#!/usr/bin/env python
import time
import logging
from argparse import ArgumentParser

from six.moves import input

from pixy import pixy

from utils.bot_logging import ImageCreator, Tweeter
from utils.vision import PixyBlock


logger = logging.getLogger('selfie')


def setup():
    """
    One time setup. Inialize pixy and set sigint handler
    """
    logger.info('Setting up')
    # global blocks
    pixy_init_status = pixy.pixy_init()
    if pixy_init_status != 0:
        logger.error('Error: pixy_init() [%d] ' % pixy_init_status)
        pixy.pixy_error(pixy_init_status)
        return
    else:
        logger.info("Pixy setup OK")


if __name__ == '__main__':
    parser = ArgumentParser(description='Start the robot in photo-taking mode!')

    parser.add_argument('path', default='selfie.png', help='Path to save the file')
    parser.add_argument('--title', '-t', default='', help='Title for the picture')
    parser.add_argument('--post-tweet', '-p', action='store_true', default=False, help='Tweet picture')

    parsed_args = parser.parse_args()

    try:
        setup()
        imager = ImageCreator()
        timer = input('Timer (empty to take photo immediately): ')
        time.sleep(0 if not timer else float(timer))
        blocks = PixyBlock.from_pixy()
        imager.save_file(blocks, parsed_args.path, parsed_args.title)
        logger.critical('Photo taken and saved to {}')
        if parsed_args.post_tweet:
            with Tweeter() as tweeter:
                tweeter.tweet_blocks(blocks, p=1.0, msg=parsed_args.title)
    finally:
        pixy.pixy_close()
