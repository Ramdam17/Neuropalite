"""Alpha power metrics with multiple normalization strategies.

Computes relative alpha power from frequency band data and normalizes
it to [0, 1] using one of four methods. Each method suits different
experimental contexts:

1. **Min-Max** — sliding window, good for short sessions with known range.
2. **Z-Score + Sigmoid** — robust to outliers via sigmoid squashing.
3. **Baseline Calibration** — requires explicit calibration phase
   (e.g. eyes-closed / eyes-open).
4. **Percentile Ranking** — adaptive over long sessions (120 s window)
   with exponential smoothing.

References
----------
- Zoefel et al. (2011). Neurofeedback training of the upper alpha
  frequency band in EEG improves cognitive performance. NeuroImage.
- Escolano et al. (2014). A controlled study on the cognitive effect
  of alpha neurofeedback training. Frontiers in Behavioral Neuroscience.
"""

import logging
from collections import deque
from typing import Any

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class AlphaMetricsCalculator:
    """Computes and normalizes alpha power metrics for multiple devices.

    Parameters
    ----------
    processing_config : dict
        Parsed ``processing_config.yaml`` content.
    device_ids : list[str]
        List of device identifiers (e.g. ``["muse_1", "muse_2"]``).

    Example
    -------
    >>> calc = AlphaMetricsCalculator(proc_cfg, ["muse_1", "muse_2"])
    >>> calc.update("muse_1", relative_bands={"alpha": np.array([0.3, 0.4, 0.35, 0.32])})
    >>> result = calc.get_metric("muse_1", method="minmax")
    >>> print(f"Normalized alpha: {result:.3f}")
    """

    def __init__(
        self,
        processing_config: dict[str, Any],
        device_ids: list[str],
    ) -> None:
        norm_cfg = processing_config["normalization"]
        self._default_method = norm_cfg["default_method"]

        # Method-specific params
        self._minmax_window = norm_cfg["minmax"]["window_duration"]
        self._zscore_window = norm_cfg["zscore"]["window_duration"]
        self._zscore_temp = norm_cfg["zscore"]["temperature"]
        self._baseline_scale = norm_cfg["baseline"]["scaling_factor"]
        self._percentile_window = norm_cfg["percentile"]["window_duration"]
        self._percentile_smooth = norm_cfg["percentile"]["smoothing"]

        # Per-device state: history of mean alpha power values
        # Max history length based on longest window @ ~10 Hz update rate
        max_history = int(max(
            self._minmax_window,
            self._zscore_window,
            self._percentile_window,
        ) * 10)

        self._history: dict[str, deque[float]] = {
            did: deque(maxlen=max_history) for did in device_ids
        }

        # Baseline values (set via calibrate())
        self._baselines: dict[str, float] = {}

        # Previous percentile for exponential smoothing
        self._prev_percentile: dict[str, float] = {did: 0.5 for did in device_ids}

        logger.info(
            "AlphaMetricsCalculator initialized: %d devices, default=%s",
            len(device_ids),
            self._default_method,
        )

    def update(
        self,
        device_id: str,
        relative_bands: dict[str, np.ndarray],
    ) -> float:
        """Record a new alpha power observation for a device.

        Takes the mean relative alpha power across channels and appends
        it to the device's history.

        Parameters
        ----------
        device_id : str
            Device identifier.
        relative_bands : dict[str, np.ndarray]
            Output of ``SignalProcessor.extract_relative_band_powers()``.

        Returns
        -------
        float
            Raw mean relative alpha power (before normalization).
        """
        alpha_power = float(np.mean(relative_bands.get("alpha", np.array([0.0]))))
        self._history[device_id].append(alpha_power)
        return alpha_power

    def get_metric(
        self,
        device_id: str,
        method: str | None = None,
    ) -> float:
        """Get the normalized alpha metric for a device.

        Parameters
        ----------
        device_id : str
            Device identifier.
        method : str, optional
            Normalization method: ``"minmax"``, ``"zscore"``, ``"baseline"``,
            ``"percentile"``. Defaults to config's ``default_method``.

        Returns
        -------
        float
            Normalized alpha metric in [0, 1].
        """
        method = method or self._default_method
        history = self._history[device_id]

        if len(history) == 0:
            return 0.0

        current = history[-1]

        if method == "minmax":
            return self._normalize_minmax(current, history)
        elif method == "zscore":
            return self._normalize_zscore(current, history)
        elif method == "baseline":
            return self._normalize_baseline(current, device_id)
        elif method == "percentile":
            return self._normalize_percentile(current, history, device_id)
        else:
            logger.warning("Unknown normalization method '%s', using minmax", method)
            return self._normalize_minmax(current, history)

    def calibrate_baseline(
        self,
        device_id: str,
        baseline_data: list[float] | np.ndarray,
    ) -> float:
        """Set the baseline mean for baseline calibration method.

        Should be called after a calibration phase (e.g. 30 s eyes closed).

        Parameters
        ----------
        device_id : str
            Device identifier.
        baseline_data : array-like
            Alpha power values collected during calibration.

        Returns
        -------
        float
            Computed baseline mean.
        """
        baseline_mean = float(np.mean(baseline_data))
        self._baselines[device_id] = baseline_mean
        logger.info(
            "Baseline calibrated for %s: mean=%.4f", device_id, baseline_mean
        )
        return baseline_mean

    def get_all_metrics(
        self, method: str | None = None
    ) -> dict[str, float]:
        """Get normalized alpha for all devices.

        Returns
        -------
        dict[str, float]
            Mapping ``device_id → normalized alpha``.
        """
        return {
            did: self.get_metric(did, method) for did in self._history
        }

    def reset(self, device_id: str | None = None) -> None:
        """Clear history for one or all devices."""
        if device_id:
            self._history[device_id].clear()
            self._prev_percentile[device_id] = 0.5
        else:
            for did in self._history:
                self._history[did].clear()
                self._prev_percentile[did] = 0.5

    # ------------------------------------------------------------------
    # Normalization methods
    # ------------------------------------------------------------------

    def _normalize_minmax(
        self, current: float, history: deque[float]
    ) -> float:
        """Min-Max normalization over a sliding window.

        Formula: (x - min) / (max - min)

        Parameters from config: ``minmax.window_duration`` (seconds).
        """
        n_samples = int(self._minmax_window * 10)  # ~10 Hz update rate
        window = list(history)[-n_samples:]

        min_val = min(window)
        max_val = max(window)
        denom = max_val - min_val

        if denom < 1e-8:
            return 0.5

        return float(np.clip((current - min_val) / denom, 0.0, 1.0))

    def _normalize_zscore(
        self, current: float, history: deque[float]
    ) -> float:
        """Z-Score + Sigmoid normalization.

        Formula: sigmoid((x - μ) / σ / temperature)

        Maps the z-score through a sigmoid to get a [0, 1] output.
        Temperature controls the steepness (lower = steeper).
        """
        n_samples = int(self._zscore_window * 10)
        window = np.array(list(history)[-n_samples:])

        mean = np.mean(window)
        std = np.std(window)

        if std < 1e-8:
            return 0.5

        z = (current - mean) / std
        return float(1.0 / (1.0 + np.exp(-z / self._zscore_temp)))

    def _normalize_baseline(
        self, current: float, device_id: str
    ) -> float:
        """Baseline calibration normalization.

        Formula: clip((x - baseline_mean) * scaling_factor + 0.5, 0, 1)

        Requires prior call to ``calibrate_baseline()``.
        Centers output at 0.5 when current == baseline.
        """
        if device_id not in self._baselines:
            logger.warning(
                "No baseline for %s — returning 0.5. Call calibrate_baseline() first.",
                device_id,
            )
            return 0.5

        baseline = self._baselines[device_id]
        normalized = (current - baseline) * self._baseline_scale + 0.5
        return float(np.clip(normalized, 0.0, 1.0))

    def _normalize_percentile(
        self, current: float, history: deque[float], device_id: str
    ) -> float:
        """Percentile ranking with exponential smoothing.

        Computes the percentile rank of the current value within
        the history window, then applies exponential smoothing for
        temporal stability.

        Reference: Gruzelier (2014). EEG-neurofeedback for optimising
        performance. Neuroscience & Biobehavioral Reviews.
        """
        n_samples = int(self._percentile_window * 10)
        window = np.array(list(history)[-n_samples:])

        if len(window) < 2:
            return 0.5

        percentile = stats.percentileofscore(window, current) / 100.0

        # Exponential smoothing
        alpha = self._percentile_smooth
        prev = self._prev_percentile[device_id]
        smoothed = alpha * percentile + (1 - alpha) * prev
        self._prev_percentile[device_id] = smoothed

        return float(np.clip(smoothed, 0.0, 1.0))
