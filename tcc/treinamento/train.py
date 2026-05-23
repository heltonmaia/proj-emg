"""Training orchestrator for the EMG binary classifier.

Loads all rec_emg/ CSVs, filters them, slices into labeled windows,
extracts features, then runs Leave-One-Group-Out CV on each (feature_set,
max_depth) config in a sweep. Picks the best, retrains on all data,
saves artifacts, and regenerates prediction.py.
"""

import os
import sys
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import accuracy_score, confusion_matrix

# allow running as `python train.py` from tcc/treinamento/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from data import load_csv, list_csvs, make_windows, extract_features  # noqa: E402
from filter import filter_emg  # noqa: E402

PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))   # .../proj-emg


@dataclass
class Dataset:
    X: np.ndarray         # (N, n_features) features
    y: np.ndarray         # (N,) labels 0/1
    groups: np.ndarray    # (N,) group id per window (= CSV index)


def build_dataset(csv_paths: List[str], feature_names: List[str]) -> Dataset:
    """Load + filter + window + extract features from every CSV."""
    all_X, all_y, all_g = [], [], []
    for g, path in enumerate(csv_paths):
        sig, labels = load_csv(path)
        filtered = filter_emg(sig)
        wins, win_y = make_windows(filtered, labels)
        feats = extract_features(wins, feature_names)
        all_X.append(feats)
        all_y.append(win_y)
        all_g.append(np.full(len(win_y), g, dtype=np.int8))
    return Dataset(
        X=np.vstack(all_X),
        y=np.concatenate(all_y),
        groups=np.concatenate(all_g),
    )


def logo_accuracy(ds: Dataset, max_depth) -> Tuple[float, float, np.ndarray, np.ndarray]:
    """Run LOGO CV; return mean accuracy, std accuracy, aggregated y_true and y_pred."""
    logo = LeaveOneGroupOut()
    fold_acc = []
    y_true_all, y_pred_all = [], []
    for tr, te in logo.split(ds.X, ds.y, ds.groups):
        clf = DecisionTreeClassifier(max_depth=max_depth, random_state=42)
        clf.fit(ds.X[tr], ds.y[tr])
        y_pred = clf.predict(ds.X[te])
        fold_acc.append(accuracy_score(ds.y[te], y_pred))
        y_true_all.append(ds.y[te])
        y_pred_all.append(y_pred)
    return (float(np.mean(fold_acc)),
            float(np.std(fold_acc)),
            np.concatenate(y_true_all),
            np.concatenate(y_pred_all))


if __name__ == "__main__":
    csvs = list_csvs(os.path.join(PROJECT_ROOT, "rec_emg"))
    print(f"Loaded {len(csvs)} CSVs from rec_emg/")
    ds = build_dataset(csvs, ["rms", "mav", "sd", "wl"])
    print(f"Dataset: {ds.X.shape[0]} windows × {ds.X.shape[1]} features")
    mean_acc, std_acc, y_true, y_pred = logo_accuracy(ds, max_depth=5)
    print(f"Baseline (4 features, max_depth=5): {mean_acc:.3f} ± {std_acc:.3f}")
    print("Confusion matrix:")
    print(confusion_matrix(y_true, y_pred))
