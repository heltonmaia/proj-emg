"""Feature functions for sEMG window analysis.

Each function takes a 1-D numpy array (one window of samples) and returns
a single scalar feature. All functions are pure — no I/O, no globals.
"""

import numpy as np


def rms(x: np.ndarray) -> float:
    """Root Mean Square — sqrt(mean(x**2))."""
    return float(np.sqrt(np.mean(x.astype(float) ** 2)))
