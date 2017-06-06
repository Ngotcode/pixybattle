#!/usr/bin/env python
from __future__ import division
import logging
import os
import sys

python_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(python_dir)

from utils.constants import PixySerial

from six.moves import range
import serial

logger = logging.getLogger('serial_test')

REPS = 1000

fail_count = 0

for _ in range(REPS):
    try:
        logger.debug('Trying serial interface...')
        ser = serial.Serial(PixySerial.SERIAL_DEVICE, PixySerial.BAUD_RATE)
        ser.close()
        ser = None
        logger.info('Successful test!')
    except:
        fail_count += 1
        logger.error('FAILED TEST')

failure_rate = fail_count / REPS

logger.critical('Serial has failure rate of {:.03f}%'.format(failure_rate * 100))

