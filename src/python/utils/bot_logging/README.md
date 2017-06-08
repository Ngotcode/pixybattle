# Logging

It's very common to want to know what your program is doing while it's executing, and having a trace of where it got to if something goes wrong.
It's also very common to want to get rid of this trace when you're running in 'production' mode.
But that involves commenting and uncommenting `print` statements all the time, which is a pain and error-prone.

Enter logging!

Logging adds a single line of boilerplate to your code, but makes it very easy to format your log messages, and to switch them off and on.

## The short story

```python
import logging

my_logger = logging.getLogger(__name__)

my_logger.info("Logger created")
```

Using `logging.getLogger(__name__)` returns a logger object which is keyed to the name of your module (so you can track down
the source of messages easily), and means that if the same logger is used elsewhere, it just returns a reference to the same object,
rather than duplicating them and having them clash.

Then log your messages as you see fit!

## Severity levels

```python
my_logger.debug('Fine-grained information about exactly what is happening at every step')
my_logger.info('Informative message about general healthy functioning')
my_logger.warning("Suggestion that something might have gone a bit wrong, but it hasn't broken yet")
my_logger.error('Something has gone wrong and your program has fallen over')
my_logger.critical('Something has gone extremely wrong and your program may have caused other problems with your computer')
```

When you set your logging level (levels are accessed with `logging.DEBUG`, `logging.INFO` etc.), messages of that severity and
greater are processed. So during development, you might set the level to `logging.DEBUG`, and during competition, `logging.WARNING`.

## Robot-specific

To simplify matters, I've done all the logging setup, and it'll be initiated as soon as anything from `utils` is imported.

Log messages include a timestamp (in seconds since the robot started up).

All messages, regardless of their severity, will be logged to a text file in a timestamped subdirectory of the `logs/`
directory.
By default, they are all printed to the console as well. To set the level of logs printed to the console:

```python
from utils.bot_logging import set_log_level

if __name__ == '__main__':
    set_log_level(logging.WARNING)
```

This should ONLY be done in an entry point - i.e. a script you call directly from the command line, and in an
`if __name__ is '__main__':` block - otherwise you can mess with other people's scripts if they import from your module.

Log messages for every shot from the laser can be silenced two ways.
If you want to silence them in both the console log and the file log, use `logging.getLogger().setLevel(logging.DEBUG)`.
If you want to silence them in the console but keep them in the file log, use `from utils.bot_logging import set_log_level; set_log_level(logging.DEBUG)`.


### Image logging

To log a set of blocks seen by the robot as an image:

```python
import logging
from utils.bot_logging import ImageLogger

img_logger = ImageLogger(__name__, logging.DEBUG)
img_logger.debug(blocks, 'This is a message')
```

Set at whichever severity level you would like to log (this can be changed with `img_logger.setLevel()` - camelCase used for compatibility
with `logging` module). The image logger will ignore any log calls made to it below its current severity level, so you don't need to
comment out your debug level logs in production.

The message argument is optional. The logging level argument to the constructor defaults to logging everything.