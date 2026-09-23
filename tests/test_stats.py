import numpy as np

from dwg.stats import bootstrap_ci, brier_score, describe, expected_calibration_error, iqr_outliers


def test_bootstrap_ci_brackets_the_mean():
    values = np.random.default_rng(1).normal(10, 1, size=200)
    mean, lo, hi = bootstrap_ci(values)
    assert lo < mean < hi
    assert abs(mean - values.mean()) < 1e-12


def test_cluster_bootstrap_is_wider_than_naive_for_correlated_repeats():
    # 20 states, 10 identical repeats each: the effective sample size is 20, not 200.
    per_state = np.random.default_rng(2).integers(0, 2, size=20).astype(float)
    values = np.repeat(per_state, 10)
    clusters = np.repeat(np.arange(20), 10)
    _, naive_lo, naive_hi = bootstrap_ci(values)
    _, clus_lo, clus_hi = bootstrap_ci(values, clusters)
    assert (clus_hi - clus_lo) > 2 * (naive_hi - naive_lo)


def test_iqr_outliers_flags_only_the_spike():
    values = [1.0, 1.1, 0.9, 1.05, 0.95, 1.0, 12.0]
    assert iqr_outliers(values).tolist() == [False] * 6 + [True]


def test_describe_reports_outlier_count():
    d = describe([1.0, 1.1, 0.9, 1.05, 0.95, 1.0, 12.0])
    assert d["n"] == 7 and d["n_outliers"] == 1 and d["max"] == 12.0


def test_calibration_perfect_and_overconfident():
    conf = [0.8] * 10
    assert expected_calibration_error(conf, [True] * 8 + [False] * 2) < 1e-9
    assert abs(expected_calibration_error([1.0] * 10, [True] * 5 + [False] * 5) - 0.5) < 1e-9
    assert brier_score([1.0, 0.0], [True, False]) == 0.0
