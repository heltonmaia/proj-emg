"""Load and label EMG recordings from rec_emg/.

Each recording is 30 s x 500 Hz with prompts at 0/5/10/15/20/25 s
alternating: open (0s) -> closed (5s) -> open (10s) -> closed (15s) ->
open (20s) -> closed (25s).
"""

import os
from typing import List, Sequence, Tuple

import numpy as np
import pandas as pd

FS = 500
DURATION = 30
PROMPT_TIMES = [0, 5, 10, 15, 20, 25]
PROMPT_LABELS = [0, 1, 0, 1, 0, 1]   # 0 = aberta, 1 = fechada


def load_csv(path: str) -> Tuple[np.ndarray, np.ndarray]:
    """Load a CSV; return (signal, per-sample labels).

    Labels are derived from the prompt schedule: each sample belongs to
    the prompt interval containing its timestamp.
    """
    df = pd.read_csv(path)
    if "EMG_Value" not in df.columns:
        raise ValueError(f"{path}: missing EMG_Value column")
    sig = df["EMG_Value"].values.astype(float)
    n = len(sig)
    if n != FS * DURATION:
        raise ValueError(
            f"{path}: expected {FS * DURATION} samples ({DURATION}s × {FS} Hz), got {n}"
        )
    # Build per-sample timestamps from index (more robust than reading Tempo column)
    t = np.arange(n) / FS
    labels = np.empty(n, dtype=np.int8)
    for i, ts in enumerate(PROMPT_TIMES):
        end = PROMPT_TIMES[i + 1] if i + 1 < len(PROMPT_TIMES) else DURATION
        mask = (t >= ts) & (t < end)
        labels[mask] = PROMPT_LABELS[i]
    return sig, labels


def list_csvs(dir_path: str = "rec_emg") -> List[str]:
    """Return sorted absolute paths of rec_emg/new_emg_data*.csv."""
    import glob
    pattern = os.path.join(dir_path, "new_emg_data*.csv")
    paths = sorted(glob.glob(pattern))
    if not paths:
        raise SystemExit(f"No CSVs found at {pattern}. Aborting.")
    return paths


WINDOW_SIZE = 100              # 200 ms at 500 Hz, matches prediction.py
STEP_SIZE = 50                 # 50% overlap
TRANSITION_MARGIN_SAMPLES = 250   # 500 ms each side of a label change


def make_windows(signal: np.ndarray,
                 labels: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Slide a window of WINDOW_SIZE samples with STEP_SIZE step.

    Skips any window whose start lies within TRANSITION_MARGIN_SAMPLES
    of a label change, and any window that internally spans more than
    one label (defensive — shouldn't occur given the margin).
    """
    n = len(signal)
    assert n == len(labels)
    # Indexes where label changes (transitions)
    transitions = np.where(np.diff(labels) != 0)[0] + 1   # index of new-label start
    transition_zones = []
    for t in transitions:
        transition_zones.append((t - TRANSITION_MARGIN_SAMPLES,
                                 t + TRANSITION_MARGIN_SAMPLES))

    def in_transition_zone(start: int) -> bool:
        end = start + WINDOW_SIZE
        for lo, hi in transition_zones:
            if start < hi and end > lo:
                return True
        return False

    Xs, ys = [], []
    for start in range(0, n - WINDOW_SIZE + 1, STEP_SIZE):
        if in_transition_zone(start):
            continue
        win = signal[start:start + WINDOW_SIZE]
        win_labels = labels[start:start + WINDOW_SIZE]
        if win_labels.min() != win_labels.max():
            continue          # mixed-label window (defensive)
        Xs.append(win)
        ys.append(int(win_labels[0]))
    if not Xs:
        return (np.empty((0, WINDOW_SIZE), dtype=float),
                np.empty((0,), dtype=np.int8))
    return np.asarray(Xs), np.asarray(ys, dtype=np.int8)


import features as feat_module


FEATURE_FUNCS = {
    "rms": feat_module.rms,
    "mav": feat_module.mav,
    "sd": feat_module.sd,
    "wl": feat_module.wl,
    "var": feat_module.var,
    "zc": feat_module.zc,
    "ssc": feat_module.ssc,
    # wamp omitted from default registry — it needs a per-call threshold
}


def extract_features(windows: np.ndarray,
                     feature_names: Sequence[str]) -> np.ndarray:
    """Apply each feature function to each window. Returns (N_windows, N_features)."""
    out = np.zeros((len(windows), len(feature_names)))
    for j, name in enumerate(feature_names):
        fn = FEATURE_FUNCS[name]
        for i, w in enumerate(windows):
            out[i, j] = fn(w)
    return out
