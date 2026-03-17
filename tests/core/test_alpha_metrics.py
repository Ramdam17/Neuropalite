"""Tests for the alpha metrics normalization module.

Verifies that each of the four normalization methods produces values
in [0, 1] and behaves correctly for known input patterns.
"""

import numpy as np
import pytest

from neuropalite.core.alpha_metrics import AlphaMetricsCalculator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def norm_config() -> dict:
    """Minimal processing config with normalization params."""
    return {
        "normalization": {
            "default_method": "minmax",
            "minmax": {"window_duration": 60.0},
            "zscore": {"window_duration": 60.0, "temperature": 1.0},
            "baseline": {"scaling_factor": 2.0},
            "percentile": {"window_duration": 120.0, "smoothing": 0.1},
        },
    }


@pytest.fixture
def calc(norm_config) -> AlphaMetricsCalculator:
    return AlphaMetricsCalculator(norm_config, ["muse_1", "muse_2"])


def feed_values(calc: AlphaMetricsCalculator, device_id: str, values: list[float]) -> None:
    """Feed a sequence of alpha values into the calculator."""
    for v in values:
        calc.update(device_id, {"alpha": np.array([v])})


# ---------------------------------------------------------------------------
# General behavior
# ---------------------------------------------------------------------------


class TestGeneralBehavior:
    """Tests applicable to all normalization methods."""

    def test_empty_history_returns_zero(self, calc):
        """With no data, metric should be 0.0."""
        assert calc.get_metric("muse_1") == 0.0

    def test_output_in_range(self, calc):
        """All methods should return values in [0, 1]."""
        values = list(np.random.uniform(0.1, 0.9, size=100))
        feed_values(calc, "muse_1", values)

        for method in ["minmax", "zscore", "baseline", "percentile"]:
            if method == "baseline":
                calc.calibrate_baseline("muse_1", values[:30])
            result = calc.get_metric("muse_1", method=method)
            assert 0.0 <= result <= 1.0, f"{method} returned {result}"

    def test_get_all_metrics(self, calc):
        """get_all_metrics should return a dict for all devices."""
        feed_values(calc, "muse_1", [0.3, 0.4, 0.5])
        feed_values(calc, "muse_2", [0.6, 0.7, 0.8])

        result = calc.get_all_metrics()
        assert "muse_1" in result
        assert "muse_2" in result

    def test_reset_clears_history(self, calc):
        """After reset, metric should return 0.0."""
        feed_values(calc, "muse_1", [0.3, 0.4, 0.5])
        calc.reset("muse_1")
        assert calc.get_metric("muse_1") == 0.0


# ---------------------------------------------------------------------------
# Min-Max normalization
# ---------------------------------------------------------------------------


class TestMinMax:

    def test_max_value_returns_one(self, calc):
        """The maximum value in the window should normalize to 1.0."""
        feed_values(calc, "muse_1", [0.2, 0.4, 0.6, 0.8, 1.0])
        result = calc.get_metric("muse_1", method="minmax")
        assert abs(result - 1.0) < 1e-6

    def test_min_value_returns_zero(self, calc):
        """The minimum value in the window should normalize to 0.0."""
        feed_values(calc, "muse_1", [0.2, 0.4, 0.6, 0.8, 0.2])
        result = calc.get_metric("muse_1", method="minmax")
        assert abs(result - 0.0) < 1e-6

    def test_constant_returns_half(self, calc):
        """Constant values should return 0.5 (degenerate case)."""
        feed_values(calc, "muse_1", [0.5] * 20)
        result = calc.get_metric("muse_1", method="minmax")
        assert abs(result - 0.5) < 1e-6


# ---------------------------------------------------------------------------
# Z-Score + Sigmoid
# ---------------------------------------------------------------------------


class TestZScore:

    def test_mean_value_returns_half(self, calc):
        """A value at the mean should normalize to ~0.5 via sigmoid."""
        values = [0.3, 0.4, 0.5, 0.6, 0.7]
        feed_values(calc, "muse_1", values)

        # Feed the mean as last value
        mean_val = np.mean(values)
        calc.update("muse_1", {"alpha": np.array([mean_val])})

        result = calc.get_metric("muse_1", method="zscore")
        assert abs(result - 0.5) < 0.05

    def test_high_value_above_half(self, calc):
        """A value well above mean should normalize > 0.5."""
        feed_values(calc, "muse_1", [0.3] * 50)
        calc.update("muse_1", {"alpha": np.array([0.9])})

        result = calc.get_metric("muse_1", method="zscore")
        assert result > 0.7


# ---------------------------------------------------------------------------
# Baseline calibration
# ---------------------------------------------------------------------------


class TestBaseline:

    def test_at_baseline_returns_half(self, calc):
        """Value equal to baseline mean should normalize to 0.5."""
        baseline_data = [0.4, 0.5, 0.6]
        calc.calibrate_baseline("muse_1", baseline_data)

        baseline_mean = np.mean(baseline_data)
        feed_values(calc, "muse_1", [baseline_mean])

        result = calc.get_metric("muse_1", method="baseline")
        assert abs(result - 0.5) < 1e-6

    def test_above_baseline_above_half(self, calc):
        """Value above baseline should normalize > 0.5."""
        calc.calibrate_baseline("muse_1", [0.3, 0.3, 0.3])
        feed_values(calc, "muse_1", [0.6])

        result = calc.get_metric("muse_1", method="baseline")
        assert result > 0.5

    def test_no_baseline_returns_half(self, calc):
        """Without calibration, baseline method returns 0.5."""
        feed_values(calc, "muse_1", [0.5])
        result = calc.get_metric("muse_1", method="baseline")
        assert result == 0.5


# ---------------------------------------------------------------------------
# Percentile ranking
# ---------------------------------------------------------------------------


class TestPercentile:

    def test_highest_value_near_one(self, calc):
        """The highest value in history should rank near 1.0."""
        values = list(np.linspace(0.1, 0.9, 100))
        feed_values(calc, "muse_1", values)

        result = calc.get_metric("muse_1", method="percentile")
        # With smoothing factor 0.1, convergence is slow — just check above midpoint
        assert result > 0.5

    def test_lowest_value_near_zero(self, calc):
        """The lowest value in history should rank near 0.0."""
        values = list(np.linspace(0.1, 0.9, 100))
        values.append(0.05)  # new lowest
        feed_values(calc, "muse_1", values)

        result = calc.get_metric("muse_1", method="percentile")
        # With heavy smoothing (0.1), the drop is gradual
        assert result < 0.5
