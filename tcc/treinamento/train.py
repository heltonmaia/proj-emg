"""Training orchestrator for the EMG binary classifier.

Current scope (Task 9): loads all rec_emg/ CSVs, filters them, slices into
labeled windows, extracts features, then runs Leave-One-Group-Out CV across
a sweep of (feature_set, max_depth) configurations. Prints the sweep table
and identifies the winning config.

Planned (Tasks 10-15): write metrics.txt, generate figures (confusion matrix,
decision tree, feature importance), save the winning .pkl, and regenerate
prediction.py at the project root with the trained tree.
"""

import os
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import accuracy_score

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


def logo_accuracy(ds: Dataset, max_depth: Optional[int]) -> Tuple[float, float, np.ndarray, np.ndarray]:
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


FEATURE_SETS = {
    "baseline":      ["rms", "mav", "sd", "wl"],
    "+ZC":           ["rms", "mav", "sd", "wl", "zc"],
    "+SSC":          ["rms", "mav", "sd", "wl", "ssc"],
    "+ZC+SSC":       ["rms", "mav", "sd", "wl", "zc", "ssc"],
    "+VAR":          ["rms", "mav", "sd", "wl", "var"],
    "tcc-1000hz":    ["rms", "mav", "wl", "ssc", "zc"],   # set used at 1000Hz in TCC
}
MAX_DEPTHS = [3, 5, 7, 10, None]


@dataclass
class ConfigResult:
    feature_set: str
    max_depth: object        # int or None
    mean_acc: float
    std_acc: float
    n_features: int

    @property
    def depth_str(self) -> str:
        return "None" if self.max_depth is None else str(self.max_depth)


def run_sweep(csv_paths: List[str]) -> List[ConfigResult]:
    """Run every (feature_set, max_depth) combination. Returns list of results."""
    results = []
    # Pre-build datasets per feature_set (so we don't re-filter for each depth)
    datasets = {}
    for name, feats in FEATURE_SETS.items():
        print(f"  Building dataset for feature_set={name} ...")
        datasets[name] = build_dataset(csv_paths, feats)
    # Sweep
    for name, feats in FEATURE_SETS.items():
        for depth in MAX_DEPTHS:
            ds = datasets[name]
            mean_acc, std_acc, _, _ = logo_accuracy(ds, max_depth=depth)
            r = ConfigResult(
                feature_set=name, max_depth=depth,
                mean_acc=mean_acc, std_acc=std_acc, n_features=len(feats),
            )
            results.append(r)
            print(f"  feature_set={name:<12} max_depth={r.depth_str:<5} "
                  f"→ {r.mean_acc:.3f} ± {r.std_acc:.3f}")
    return results


def select_winner(results: List[ConfigResult]) -> ConfigResult:
    """Highest mean accuracy, tiebreak by std, then n_features, then depth."""
    def sort_key(r: ConfigResult):
        depth = 999 if r.max_depth is None else r.max_depth
        return (-r.mean_acc, r.std_acc, r.n_features, depth)
    return sorted(results, key=sort_key)[0]


if __name__ == "__main__":
    csvs = list_csvs(os.path.join(PROJECT_ROOT, "rec_emg"))
    print(f"Loaded {len(csvs)} CSVs from rec_emg/")
    results = run_sweep(csvs)
    winner = select_winner(results)
    print()
    print(f"Winner: feature_set={winner.feature_set}, max_depth={winner.depth_str}")
    print(f"  Mean LOGO accuracy: {winner.mean_acc:.3f} ± {winner.std_acc:.3f}")
