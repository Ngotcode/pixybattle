import logging
import os
import sys

from logging_constants import LOG_DIR, LOG_PATH


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


root_logger = logging.getLogger()

if not os.path.isdir(LOG_DIR):
    os.makedirs(LOG_DIR)

formatter = TimerFormatter('%(adjustedTime)s %(adjustedLevel)s: [%(name)s] %(message)s')

file_handler = logging.FileHandler(filename=LOG_PATH)
file_handler.setLevel(logging.NOTSET)
file_handler.setFormatter(formatter)
root_logger.addHandler(file_handler)

stderr_handler = logging.StreamHandler(stream=sys.stderr)
stderr_handler.setLevel(logging.NOTSET)
stderr_handler.setFormatter(formatter)
root_logger.addHandler(stderr_handler)

root_logger.setLevel(logging.NOTSET)

logging.getLogger(__name__).info('Created log file at %s', LOG_PATH)


def set_log_level(level=logging.DEBUG):
    """
    Set the severity threshold for logs to be printed out to the command line. This does not affect logs printed to
    the timestamped file.

    N.B. THIS SHOULD ONLY BE CALLED IN AN ENTRY POINT, i.e. in an `if __name__ == '__main__':` block. Otherwise you
    will interfere with logging which should be controlled by other entry points.

    Parameters
    ----------
    level : int
        Integer between 0 and 50. Ideally, use one of the log levels specified in the `logging` module:
        logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR or logging.CRITICAL.
    """
    stderr_handler.setLevel(level)


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    logger.debug('Fine-grained information about exactly what is happening at every step')
    logger.info('Informative message about general healthy functioning')
    logger.warning("Suggestion that something might have gone a bit wrong, but it hasn't broken yet")
    logger.error('Something has gone wrong and your program has fallen over')
    logger.critical('Something has gone extremely wrong and your program may have caused other problems with your computer')

    set_log_level(logging.WARNING)
    logger.debug('This DEBUG message should show up in the log file, but not the console')
    logger.info('This INFO message should show up in the log file, but not the console')
    logger.warning("This WARNING message should show up in both the log file and the console")
    logger.error('This ERROR message should show up in both the log file and the console')
    logger.critical('This CRITICAL message should show up in both the log file and the console')
