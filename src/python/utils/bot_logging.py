import logging
from datetime import datetime
from constants import ROOT_DIR
import os
import sys

LOGGER_NAME = 'team4bot'
LOG_ROOT = os.path.join(ROOT_DIR, 'logs')
TIMESTAMP = datetime.now().strftime('%Y-%m-%d_%H:%M:%S')


class InfoFilter(logging.Filter):
    def filter(self, rec):
        return rec.levelno in (logging.DEBUG, logging.INFO)


class TimerFormatter(logging.Formatter):
    def format(self, record):
        record.adjustedTime = self.reformat_ms(record.relativeCreated)
        record.adjustedLevel = self.reformat_level(record.levelname)
        return super(TimerFormatter, self).format(record)

    @staticmethod
    def reformat_ms(relativeCreated):
        seconds = float(relativeCreated) / 1000
        return '{:09.3f}'.format(seconds)

    @staticmethod
    def reformat_level(levelname):
        return levelname.rjust(8)


def get_logger_name(stdout_level=logging.INFO):
    """
    Performs basic configuration of logging for the robot, including creating a timestamped log file. Every line 
    starts with the time in seconds since the logger was created (usually at the start of the script).
    
    Parameters
    ----------
    stdout_level : int
        Log level to print to stdout (default is defined in utils/constants.py). N.B. this does not effect logging to a 
        timestamped file with level logging.DEBUG, or logging to stderr with level logging.WARNING.
        
    Returns
    -------
    str
        Name of root logger
        
    Examples
    --------
    Import logging and this function:
    
    >>> import logging
    >>> from utils.bot_logging import get_logger_name  # assuming you're in the src/python directory
    
    Call this function, which performs initial setup, tells the logger to print all messages out to the command line, 
    and returns the logger name:
    
    >>> logger_name = get_logger_name(logging.DEBUG)
    >>> logger = logging.getLogger(logger_name)
    
    Then log some messages as you deem appropriate!
    
    >>> logger.debug('Fine-grained information about exactly what is happening at every step')
    >>> logger.info('Informative message about general healthy functioning')
    >>> logger.warning("Suggestion that something might have gone a bit wrong, but it hasn't broken yet")
    >>> logger.error('Something has gone wrong and your program has fallen over')
    >>> logger.critical('Something has gone extremely wrong and your program may have caused other problems with your computer')
    
    Warning and above will be written to STDERR (usually red text in your console).
    Info and debug will be written to STDOUT (plain text in your console).
    Everything will be written to a timestamped log file.
    
    If you don't need to see all the debug-level messages in your STDOUT, just leave that argument out of 
    `get_logger_name()`.
    """
    log_path = os.path.join(LOG_ROOT, TIMESTAMP + '.txt')

    if not os.path.isdir(LOG_ROOT):
        os.makedirs(LOG_ROOT)

    logger = logging.getLogger(LOGGER_NAME)

    if not os.path.isfile(log_path):
        formatter = TimerFormatter('%(adjustedTime)s %(adjustedLevel)s: %(message)s')

        file_handler = logging.FileHandler(filename=log_path)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        stdout_handler = logging.StreamHandler(stream=sys.stdout)
        stdout_handler.setLevel(stdout_level)
        stdout_handler.setFormatter(formatter)
        logger.addHandler(stdout_handler)

        stderr_handler = logging.StreamHandler(stream=sys.stderr)
        stderr_handler.setLevel(logging.WARNING)
        stderr_handler.addFilter(InfoFilter())
        stderr_handler.setFormatter(formatter)
        logger.addHandler(stderr_handler)

        logger.setLevel(logging.DEBUG)

        logger.debug('Created log file at %s', log_path)
        logger.debug('Logging to STDOUT at level %d', stdout_level)

        logger.info('Logging set up')

    return LOGGER_NAME


if __name__ == '__main__':
    name = get_logger_name()
    logger = logging.getLogger(name)
    logger.debug('Fine-grained information about exactly what is happening at every step')
    logger.info('Informative message about general healthy functioning')
    logger.warning("Suggestion that something might have gone a bit wrong, but it hasn't broken yet")
    logger.error('Something has gone wrong and your program has fallen over')
    logger.critical('Something has gone extremely wrong and your program may have caused other problems with your computer')
