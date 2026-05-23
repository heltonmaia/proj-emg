"""Load and label EMG recordings from rec_emg/.

Each recording is 30 s x 500 Hz with prompts at 0/5/10/15/20/25 s
alternating: open (0s) -> closed (5s) -> open (10s) -> closed (15s) ->
open (20s) -> closed (25s).
"""

import os
from typing import List, Tuple

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
