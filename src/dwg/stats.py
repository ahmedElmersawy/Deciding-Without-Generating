"""Statistics for repeated-trial benchmark runs (DECISIONS.md 2026-09-23).

Every measurement is repeated, so results are reported as distributions, not single numbers:
means with 95% bootstrap CIs, medians/p95, and IQR outliers. The bootstrap resamples whole
clusters (e.g. states or tasks) rather than individual calls, because repeated calls on the
same state are correlated — resampling calls independently would make the CIs too narrow.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Optional

import numpy as np


def bootstrap_ci(
    values: Sequence[float],
    clusters: Optional[Sequence] = None,
    n_boot: int = 10_000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple[float, float, float]:
    """Mean of `values` and its (1-alpha) percentile-bootstrap CI.

    With `clusters`, resamples whole clusters with replacement and takes the mean over all
    values in the resampled clusters (cluster bootstrap).
    """
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    if clusters is None:
        idx = rng.integers(0, values.size, size=(n_boot, values.size))
        boots = values[idx].mean(axis=1)
    else:
        clusters = np.asarray(clusters)
        keys, inverse = np.unique(clusters, return_inverse=True)
        sums = np.bincount(inverse, weights=values, minlength=keys.size)
        counts = np.bincount(inverse, minlength=keys.size)
        picks = rng.integers(0, keys.size, size=(n_boot, keys.size))
        boots = sums[picks].sum(axis=1) / counts[picks].sum(axis=1)
    lo, hi = np.quantile(boots, [alpha / 2, 1 - alpha / 2])
    return float(values.mean()), float(lo), float(hi)


def iqr_outliers(values: Sequence[float], k: float = 1.5) -> np.ndarray:
    """Boolean mask of Tukey outliers: outside [Q1 - k*IQR, Q3 + k*IQR]."""
    values = np.asarray(values, dtype=float)
    q1, q3 = np.quantile(values, [0.25, 0.75])
    iqr = q3 - q1
    return (values < q1 - k * iqr) | (values > q3 + k * iqr)


def describe(values: Sequence[float]) -> dict[str, float]:
    """Distribution summary used in every results table."""
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    if values.size == 0:
        return {"n": 0}
    return {
        "n": int(values.size),
        "mean": float(values.mean()),
        "std": float(values.std(ddof=1)) if values.size > 1 else 0.0,
        "min": float(values.min()),
        "p50": float(np.quantile(values, 0.5)),
        "p95": float(np.quantile(values, 0.95)),
        "max": float(values.max()),
        "n_outliers": int(iqr_outliers(values).sum()),
    }


def expected_calibration_error(confidence: Sequence[float], correct: Sequence[bool], n_bins: int = 10) -> float:
    """ECE with equal-width bins: sum over bins of |accuracy - mean confidence| * bin weight."""
    confidence = np.asarray(confidence, dtype=float)
    correct = np.asarray(correct, dtype=float)
    bins = np.minimum((confidence * n_bins).astype(int), n_bins - 1)
    ece = 0.0
    for b in range(n_bins):
        mask = bins == b
        if mask.any():
            ece += mask.mean() * abs(correct[mask].mean() - confidence[mask].mean())
    return float(ece)


def brier_score(confidence: Sequence[float], correct: Sequence[bool]) -> float:
    """Mean squared error between p(chosen action is correct) and the 0/1 outcome."""
    confidence = np.asarray(confidence, dtype=float)
    correct = np.asarray(correct, dtype=float)
    return float(np.mean((confidence - correct) ** 2))


def reliability_bins(confidence: Sequence[float], correct: Sequence[bool], n_bins: int = 10):
    """(mean confidence, accuracy, count) per non-empty bin, for reliability diagrams."""
    confidence = np.asarray(confidence, dtype=float)
    correct = np.asarray(correct, dtype=float)
    bins = np.minimum((confidence * n_bins).astype(int), n_bins - 1)
    rows = []
    for b in range(n_bins):
        mask = bins == b
        if mask.any():
            rows.append((float(confidence[mask].mean()), float(correct[mask].mean()), int(mask.sum())))
    return rows
