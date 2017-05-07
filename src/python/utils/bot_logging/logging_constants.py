from __future__ import absolute_import

import os
from datetime import datetime

from utils.constants import ROOT_DIR

log_root = os.path.join(ROOT_DIR, 'logs')
timestamp = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')

LOG_DIR = os.path.join(log_root, timestamp)
