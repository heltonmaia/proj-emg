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
from datetime import datetime
from typing import List, Optional, Tuple

import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

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


RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")


def ensure_results_dir():
    os.makedirs(RESULTS_DIR, exist_ok=True)


def write_metrics(results: List[ConfigResult], winner: ConfigResult,
                  ds_winner: Dataset, y_true: np.ndarray, y_pred: np.ndarray):
    """Write metrics.txt with top 5 + winner + classification report."""
    ensure_results_dir()
    out = os.path.join(RESULTS_DIR, "metrics.txt")

    def sort_key(r):
        depth = 999 if r.max_depth is None else r.max_depth
        return (-r.mean_acc, r.std_acc, r.n_features, depth)
    sorted_results = sorted(results, key=sort_key)
    top5 = sorted_results[:5]

    with open(out, "w") as f:
        f.write(f"# Sweep results — Classificador EMG 500 Hz\n")
        f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Total configs tested: {len(results)}\n")
        f.write(f"# Dataset: {ds_winner.X.shape[0]} windows × {ds_winner.X.shape[1]} features\n")
        f.write(f"\n")
        f.write(f"## Top 5 configs (by mean LOGO accuracy)\n\n")
        f.write(f"{'#':<4}{'feature_set':<14}{'depth':<8}{'n_feat':<8}{'mean_acc':<12}{'std_acc':<10}\n")
        for i, r in enumerate(top5, start=1):
            f.write(f"{i:<4}{r.feature_set:<14}{r.depth_str:<8}{r.n_features:<8}"
                    f"{r.mean_acc:.4f}      {r.std_acc:.4f}\n")
        f.write(f"\n")
        f.write(f"## Winner\n\n")
        f.write(f"feature_set: {winner.feature_set}\n")
        f.write(f"max_depth:   {winner.depth_str}\n")
        f.write(f"n_features:  {winner.n_features}\n")
        f.write(f"mean_acc:    {winner.mean_acc:.4f}\n")
        f.write(f"std_acc:     {winner.std_acc:.4f}\n")
        f.write(f"\n")
        f.write(f"## Classification report (LOGO aggregated)\n\n")
        f.write(classification_report(y_true, y_pred,
                                       target_names=["aberta (0)", "fechada (1)"],
                                       digits=4))
        cm = confusion_matrix(y_true, y_pred)
        f.write(f"\n## Confusion matrix (absolute counts)\n\n")
        f.write(f"             Predicted aberta  Predicted fechada\n")
        f.write(f"True aberta       {cm[0,0]:>5}             {cm[0,1]:>5}\n")
        f.write(f"True fechada      {cm[1,0]:>5}             {cm[1,1]:>5}\n")
    print(f"Saved {out}")


if __name__ == "__main__":
    csvs = list_csvs(os.path.join(PROJECT_ROOT, "rec_emg"))
    print(f"Loaded {len(csvs)} CSVs from rec_emg/")
    results = run_sweep(csvs)
    winner = select_winner(results)
    print()
    print(f"Winner: feature_set={winner.feature_set}, max_depth={winner.depth_str}")
    print(f"  Mean LOGO accuracy: {winner.mean_acc:.3f} ± {winner.std_acc:.3f}")

    # Re-run LOGO on the winner config to aggregate y_true/y_pred for metrics
    ds_winner = build_dataset(csvs, FEATURE_SETS[winner.feature_set])
    _, _, y_true, y_pred = logo_accuracy(ds_winner, max_depth=winner.max_depth)
    write_metrics(results, winner, ds_winner, y_true, y_pred)
