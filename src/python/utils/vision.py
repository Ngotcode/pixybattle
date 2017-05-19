from __future__ import division
import itertools
from random import Random
from copy import copy

import numpy as np
import networkx as nx
import matplotlib
matplotlib.use('TkAgg')
from matplotlib import pyplot as plt


SIMILARITY_THRESHOLD = 0.9


class GenericBlock(object):
    """Python Block object with handy geometric functions"""
    KEYS = ['signature', 'x', 'y', 'width', 'height']
    """Properties to use for calculating hashcode and equality, override in subclasses"""

    def __init__(self, signature, x, y, width, height):
        self.signature = signature
        self.x = x
        self.y = y
        self.width = width
        self.height = height

        self.__key = None

    @property
    def _key(self):
        if self.__key is None:
            self.__key = tuple(getattr(self, key) for key in self.KEYS)
        return self.__key

    @property
    def xmin(self):
        return self.x

    @property
    def ymin(self):
        return self.y

    @property
    def xmax(self):
        return self.x + self.width

    @property
    def ymax(self):
        return self.y + self.height

    @property
    def area(self):
        return self.width * self.height

    @property
    def aspect_ratio(self):
        return self.width / self.height

    def __repr__(self):
        return '{}({{{}}})'.format(
            type(self).__name__,
            ', '.join('{}={}'.format(key, getattr(self, key)) for key in self.KEYS)
        )

    def __eq__(self, other):
        return self._key == other._key

    def __hash__(self):
        return hash(self._key)

    def __lt__(self, other):
        return (self.x, self.y) < (other.xmin, other.ymin)

    def intersection_area(self, other, check_sig=False):
        """
        Find the area of the intersection between this block and another block.
        
        Parameters
        ----------
        other : GenericBlock
        check_sig

        Returns
        -------
        int
        """
        if check_sig and self.signature != other.signature:
            return 0

        x_overlap = max(0, min(self.xmax, other.xmax) - max(self.x, other.x))
        y_overlap = max(0, min(self.ymax, other.ymax) - max(self.y, other.y))
        return x_overlap * y_overlap

    def intersects(self, other, check_sig=False):
        """Return whether this block intersects with the other block"""
        return bool(self.intersection_area(other, check_sig))

    def nearly_equals(self, other, threshold=SIMILARITY_THRESHOLD):
        """
        Return True if the intersection area of the two blocks is greater than the threshold proportion of the larger 
        block's area.
        
        Parameters
        ----------
        other
        threshold : float
            < 0 if everything is equal to everything

        Returns
        -------
        bool
        """
        return self.signature == other.signature and self.intersection_ppn(other) >= threshold

    def intersection_ppn(self, other, check_sig=False):
        """
        Find what proportion of the larger block's area intersects with the smaller block.
         
        Parameters
        ----------
        other : GenericBlock
        check_sig

        Returns
        -------
        float
            0 - 1
        """
        if check_sig and self.signature != other.signature:
            return 0
        area = self.intersection_area(other)
        return area / max(self.area, other.area)

    @classmethod
    def merge_blocks(cls, *blocks):
        """
        CLASS METHOD
        
        Given any number of blocks, return a block which has the mean size and position of all of them.
        
        Parameters
        ----------
        blocks

        Returns
        -------
        GenericBlock
        """
        signatures = set()
        xs, ys, widths, heights = [], [], [], []

        for block in blocks:
            signatures.add(block.signature)
            xs.append(block.xmin)
            ys.append(block.ymin)
            widths.append(block.width)
            heights.append(block.height)

        assert len(signatures) == 1

        x, y, width, height = np.mean([xs, ys, widths, heights], axis=1)
        return cls(signatures.pop(), x, y, width, height)


class PixyBlock(GenericBlock):
    """GenericBlock subclass with methods for construction from a ctypes-backed Blocks object"""

    KEYS = GenericBlock.KEYS + ['type', 'angle']

    def __init__(self, signature, x, y, width, height, type_=0, angle=0):
        super(PixyBlock, self).__init__(
            signature, x, y, width, height
        )
        self.type = type_  # todo: what is this?
        self.angle = angle  # todo: what is this?

    @classmethod
    def from_ctypes(cls, ctypes_block):
        """
        Instantiate PixyBlock from a ctypes-backed Blocks object
        
        Parameters
        ----------
        ctypes_block

        Returns
        -------
        PixyBlock
        """
        return cls(
            ctypes_block.signature,
            ctypes_block.x, ctypes_block.y,
            ctypes_block.width, ctypes_block.height,
            ctypes_block.type, ctypes_block.angle
        )

    @classmethod
    def from_ctypes_array(cls, ctypes_blocks, count):
        """
        Instantiate a list of PixyBlock objects from a ctypes-backed BlocksArray
        
        Parameters
        ----------
        ctypes_blocks
        count

        Returns
        -------
        list of PixyBlock
        """
        return [cls.from_ctypes(ctypes_blocks[i]) for i in range(count)]

    @classmethod
    def merge_blocks(cls, *blocks):
        """
        Given any number of other blocks, return a block which has the mean size and position of all of them.

        Parameters
        ----------
        blocks

        Returns
        -------
        GenericBlock
        """
        signatures = set()
        xs, ys, widths, heights = [], [], [], []  # todo: add types and angles after figuring out what they do
        for block in blocks:
            signatures.add(block.signature)
            xs.append(block.xmin)
            ys.append(block.ymin)
            widths.append(block.width)
            heights.append(block.height)

        assert len(signatures) == 1

        x, y, width, height = np.mean([xs, ys, widths, heights], axis=1)
        return cls(signatures.pop(), x, y, width, height)


def nearly_equal_pairs(blocks_1, blocks_2=None, threshold=SIMILARITY_THRESHOLD):
    """
    Find pairs of blocks which are likely to be the same object.
    
    If blocks_2 is None (default), all pairs within blocks_1 will be tested for near-equality. Otherwise, 
    pairs of objects from blocks_1, and blocks_2 will be tested.
    
    Parameters
    ----------
    blocks_1
    blocks_2
    threshold

    Returns
    -------

    """
    out = set()
    if blocks_2 is None:
        this_that = itertools.combinations(blocks_1, 2)
    else:
        this_that = itertools.product(blocks_1, blocks_2)

    for this, that in this_that:
        if this.nearly_equals(that, threshold):
            out.add((this, that))

    return out


def merge_similar_blocks(blocks_1, blocks_2=None, block_constructor=GenericBlock):
    g = nx.Graph()
    g.add_nodes_from(itertools.chain(blocks_1, blocks_2) if blocks_2 else blocks_1)
    g.add_edges_from(nearly_equal_pairs(blocks_1, blocks_2, threshold=SIMILARITY_THRESHOLD))
    out = set()

    for component in nx.connected_components(g):
        if len(component) == 1:
            out.add(component.pop())
        else:
            out.add(block_constructor.merge_blocks(*component))

    return out


class Scene(object):
    """Object describing a set of blocks"""

    def __init__(self, blocks, block_constructor=GenericBlock):
        """
        
        Parameters
        ----------
        blocks : sequence
            Python block objects
        block_constructor : type
        """
        self.blocks = set(blocks)
        self.block_constructor = block_constructor

    @classmethod
    def from_ctypes_array(cls, pixy_blocks, count):
        """
        Instantiate scene directly from pixy camera output
        
        Parameters
        ----------
        pixy_blocks : BlocksArray
        count

        Returns
        -------
        Scene
        """
        blocks = PixyBlock.from_ctypes_array(pixy_blocks, count)
        return cls(blocks, PixyBlock)

    def merge(self, other):
        """
        Union two scenes, merging any similar blocks.
        
        Parameters
        ----------
        other : Scene

        Returns
        -------
        Scene
        """
        return Scene(merge_similar_blocks(self.blocks, other.blocks, self.block_constructor), self.block_constructor)

    def diff(self, other):
        """
        Diff two scenes, returning a pair of sets. The first element contains blocks which exist in the other scene 
        without a likely counterpart in this scene; the second element contains blocks which exist in this 
        scene without a likely counterpart in the other scene.
        
        Parameters
        ----------
        other : Scene

        Returns
        -------
        tuple
            (new_blocks, disappeared_blocks)
        """
        ppns = nearly_equal_pairs(self.blocks, other.blocks, threshold=SIMILARITY_THRESHOLD)
        disappeared_blocks = set(self.blocks)
        new_blocks = set(other.blocks)
        for this_block, that_block in ppns:
            disappeared_blocks.remove(this_block)
            new_blocks.remove(that_block)

        return new_blocks, disappeared_blocks


# DIAGNOSTICS

class BlockJitterer(object):
    def __init__(self, sigma, seed=1, constructor=GenericBlock):
        self.random = Random(seed)
        self.sigma = sigma
        self.constructor = constructor

    def jitter_blocks(self, block, count=1):
        return (self._jitter_block(block) for _ in range(count))

    def _jitter_block(self, block):
        new_block = copy(block)
        new_block.x += self.random.gauss(0, self.sigma)
        new_block.y += self.random.gauss(0, self.sigma)
        new_block.width += self.random.gauss(0, self.sigma)
        new_block.height += self.random.gauss(0, self.sigma)
        return new_block


def near_equality_accuracy_for_sigma(block, sigma, replicates):
    jitterer = BlockJitterer(sigma=sigma, seed=1)
    return sum(block.nearly_equals(jittered) for jittered in jitterer.jitter_blocks(block, replicates)) / replicates


def plot_near_equality_power():
    TARGET_SIGMA = 0.05
    TARGET_CONFIDENCE = 0.95
    REPLICATES = 500

    block = GenericBlock(1, 0, 0, 1, 1)

    sigmas = np.linspace(0, TARGET_SIGMA * 2, 101, True)
    results = [near_equality_accuracy_for_sigma(block, sigma, REPLICATES) for sigma in sigmas]

    fig, ax = plt.subplots()
    ax.plot(sigmas, results, c='blue', label='near_equals() performance')
    ax.axvline(TARGET_SIGMA, c='red', label='Target $\sigma$, {}% of side length'.format(TARGET_SIGMA*100))
    ax.axhline(TARGET_CONFIDENCE, c='green', label='Target confidence, {}% correct'.format(TARGET_CONFIDENCE*100))
    ax.set_xlabel('Standard deviation of location, size ($\sigma$)')
    ax.set_ylabel('Proportion correct')
    plt.legend()
    plt.show()


if __name__ == '__main__':
    plot_near_equality_power()
