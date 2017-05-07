import os
import logging
import io
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib import patches

from logging_constants import LOG_DIR


VIEW_EXTENTS = {'x': 1000, 'y': 1000}

# replace as necessary
SIGNATURE_KWARGS = {
    1: {'edgecolor': 'red', 'hatch': '/'},
    2: {'edgecolor': 'blue', 'hatch': '\\'},
    3: {'edgecolor': 'green', 'hatch': '|'},
    4: {'edgecolor': 'cyan', 'hatch': '-'},
    5: {'edgecolor': 'magenta', 'hatch': '+'},
    6: {'edgecolor': 'yellow', 'hatch': 'x'},
    7: {'edgecolor': 'black', 'hatch': 'o'},
    8: {'edgecolor': 'red', 'hatch': 'O'},
    9: {'edgecolor': 'red', 'hatch': '.'},
    10: {'edgecolor': 'red', 'hatch': '*'}
}

logger = logging.getLogger(__name__)

img_dir = os.path.join(LOG_DIR, 'img')


def timestamp_with_ms(dt=None):
    if dt is None:
        dt = datetime.now()
    return '{}.{:03.0f}'.format(dt.strftime('%Y-%m-%d %H:%M:%S'), dt.microsecond/1000)


class ImageCreator(object):
    """Class for taking array of blocks and turning them into an image, with axes, a legend and a title."""
    def __init__(self):
        self.fig, self.ax = plt.subplots()

        self.fig.tight_layout()
        self.ax.set_xlim(0, VIEW_EXTENTS['x'])
        self.ax.set_ylim(0, VIEW_EXTENTS['y'])
        self.ax.set_aspect('equal')

        self._patches = []

    def _create_image(self, blocks, title=None):
        if title:
            self.ax.set_title(title)

        for block in blocks:  # can you iterate through a ctypes array?
            patch = patches.Rectangle(
                (block.x, block.y), block.width, block.height, facecolor='none', fill=False,
                angle=block.angle, label='sig. {}'.format(block.signature), **SIGNATURE_KWARGS[block.signature]
            )  # x, y, width, height, angle may need to be adjusted
            self._patches.append(patch)
            self.ax.add_patch(patch)
        self.ax.legend(handles=self._patches)

    def save_bytes(self, blocks, title=None, **kwargs):
        """
        
        Parameters
        ----------
        blocks : array-like
            Sequence of Blocks objects
        title : str
            Can be None
        kwargs
            kwargs to be passed to `matplotlib.pyplot.savefig`

        Returns
        -------
        bytes
        """
        with self, io.BytesIO() as buf:
            self._create_image(blocks, title)
            self.fig.savefig(buf, format='png', bbox_inches='tight', **kwargs)
            buf.seek(0)
            data = buf.read()
            return data

    def save_file(self, blocks, path, title=None, **kwargs):
        """
        
        Parameters
        ----------
        blocks : array-like
            Sequence of Blocks objects
        path : str
            Output path for file.
        title : str
            Can be None
        kwargs
            kwargs to be passed to `matplotlib.pyplot.savefig`
        """
        with self:
            self._create_image(blocks, title)
            self.fig.savefig(path, bbox_inches='tight', **kwargs)

    def _clear(self):
        """Remove all patches from the axes"""
        while self._patches:
            self._patches.pop().remove()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._clear()


class ImageLogger(object):
    """Class which acts roughly like a logger, for dumping image files from blocks."""
    def __init__(self, level, root=img_dir):
        """
        
        Parameters
        ----------
        level : int
            Log severity threshold. Logs made below this level will not be saved as images.
        root : str
            Path to the directory in which images should be saved.
        """
        self.root = root
        self.level = level
        self.image_creator = ImageCreator()
        self.count = 0

    def log(self, lvl, blocks):
        if lvl < self.level:
            return

        title = 'log{:04d}_{}'.format(self.count, logging.getLevelName(lvl))

        file_path = os.path.join(self.root, title + '.png')
        self.count += 1

        self.image_creator.save_file(blocks, file_path, title)
        logger.log(lvl, 'Saved image to %s', file_path)

    def debug(self, blocks):
        self.log(logging.DEBUG, blocks)

    def info(self, blocks):
        self.log(logging.INFO, blocks)

    def warning(self, blocks):
        self.log(logging.WARNING, blocks)

    def error(self, blocks):
        self.log(logging.ERROR, blocks)

    def critical(self, blocks):
        self.log(logging.CRITICAL, blocks)
