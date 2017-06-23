from __future__ import absolute_import

import os

from utils.constants import ROOT_DIR, STARTED

log_root = os.path.join(ROOT_DIR, 'logs')
timestamp = STARTED.strftime('%Y-%m-%d_%H:%M:%S')

LOG_DIR = os.path.join(log_root, timestamp)
LOG_PATH = os.path.join(LOG_DIR, 'logs.txt')
