"""Bars-and-stripes: the toy dataset for block 2.1.

Every image is either all-horizontal bars or all-vertical stripes, each row (or column)
independently on or off. Small enough to see the whole distribution by eye, structured
enough that a bad sample is obvious at a glance. No external download needed.

Import with: from datasets import make_bars_and_stripes
"""

import numpy as np


def make_bars_and_stripes(n, size=8, p=0.5, seed=0):
    """Generate `n` bars-and-stripes images of shape (size, size), values in {0., 1.}.

    Each image picks an orientation (horizontal bars or vertical stripes) and then, for
    each line in that orientation, switches it on with probability `p`.
    """
    rng = np.random.default_rng(seed)
    imgs = np.zeros((n, size, size), dtype=np.float32)
    for i in range(n):
        horizontal = rng.random() < 0.5
        line_on = (rng.random(size) < p).astype(np.float32)
        if horizontal:
            imgs[i] = np.tile(line_on[:, None], (1, size))
        else:
            imgs[i] = np.tile(line_on[None, :], (size, 1))
    return imgs
