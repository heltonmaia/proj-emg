import numpy as np
import os
import tempfile
import pandas as pd

from data import load_csv, FS, DURATION


def _write_fake_csv(path):
    """Make a minimal 30s recording for testing."""
    n = FS * DURATION
    t = np.arange(n) / FS
    sig = np.sin(2 * np.pi * 100 * t) * 1000  # some EMG-ish-looking signal
    pd.DataFrame({"Tempo(s)": t, "EMG_Value": sig.astype(int)}).to_csv(path, index=False)


def test_load_csv_returns_right_lengths():
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        path = f.name
    try:
        _write_fake_csv(path)
        sig, labels = load_csv(path)
        assert len(sig) == FS * DURATION
        assert len(labels) == FS * DURATION
    finally:
        os.unlink(path)


def test_load_csv_label_schedule():
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        path = f.name
    try:
        _write_fake_csv(path)
        _, labels = load_csv(path)
        # Sample at t=2.5s (middle of first interval, mao aberta) -> 0
        assert labels[int(2.5 * FS)] == 0
        # Sample at t=7.5s (middle of second interval, mao fechada) -> 1
        assert labels[int(7.5 * FS)] == 1
        # Sample at t=27.5s (middle of last interval, mao fechada) -> 1
        assert labels[int(27.5 * FS)] == 1
    finally:
        os.unlink(path)
