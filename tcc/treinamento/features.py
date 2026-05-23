"""Feature functions for sEMG window analysis.

Each function takes a 1-D numpy array (one window of samples) and returns
a single scalar feature. All functions are pure — no I/O, no globals.
"""

import numpy as np


def rms(x: np.ndarray) -> float:
    """Root Mean Square — sqrt(mean(x**2))."""
    return float(np.sqrt(np.mean(x.astype(float) ** 2)))


def mav(x: np.ndarray) -> float:
    """Mean Absolute Value — mean(|x|). Distinct from arithmetic mean."""
    return float(np.mean(np.abs(x.astype(float))))


def sd(x: np.ndarray) -> float:
    """Standard deviation, population (ddof=0)."""
    return float(np.std(x.astype(float), ddof=0))


def wl(x: np.ndarray) -> float:
    """Waveform Length — sum of absolute consecutive differences."""
    return float(np.sum(np.abs(np.diff(x.astype(float)))))


def var(x: np.ndarray) -> float:
    """Variance, population (ddof=0). Equal to sd(x)**2."""
    return float(np.var(x.astype(float), ddof=0))
