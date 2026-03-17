"""Streaming orchestrator — ties the real-time processing loop together.

Runs in a background thread at the configured LSL update rate (default 10 Hz).
Each tick:
1. Pulls the latest data from each device's CircularBuffer
2. Runs the SignalProcessor (filter → PSD → bands)
3. Updates AlphaMetricsCalculator
4. Pushes results to LSL outlets
5. Emits WebSocket events for the frontend

This is the central coordination point between all core modules.
"""

import logging
import threading
import time
from typing import Any, Callable

import numpy as np

from neuropalite.core.alpha_metrics import AlphaMetricsCalculator
from neuropalite.core.lsl_streamer import LSLStreamer
from neuropalite.core.muse_manager import MuseManager
from neuropalite.core.signal_processor import SignalProcessor

logger = logging.getLogger(__name__)


class StreamingOrchestrator:
    """Coordinates the real-time processing and streaming pipeline.

    Parameters
    ----------
    muse_manager : MuseManager
        Manages Muse device connections and buffers.
    signal_processor : SignalProcessor
        Stateless DSP pipeline.
    alpha_calculator : AlphaMetricsCalculator
        Alpha power normalization module.
    lsl_streamer : LSLStreamer
        LSL outlet manager.
    update_rate : float
        Processing loop frequency in Hz (default from config).
    on_metrics_update : Callable, optional
        Callback ``(metrics_dict)`` fired each tick with all computed data.
        Used by WebSocket handlers to emit to frontend.
    """

    def __init__(
        self,
        muse_manager: MuseManager,
        signal_processor: SignalProcessor,
        alpha_calculator: AlphaMetricsCalculator,
        lsl_streamer: LSLStreamer,
        update_rate: float = 10.0,
        on_metrics_update: Callable | None = None,
    ) -> None:
        self._muse = muse_manager
        self._processor = signal_processor
        self._alpha = alpha_calculator
        self._lsl = lsl_streamer
        self._update_rate = update_rate
        self._on_metrics_update = on_metrics_update

        self._running = False
        self._thread: threading.Thread | None = None
        self._current_method = "minmax"

        # Sampling rate from first device's buffer
        self._sfreq = 256.0  # default, updated on start

    def start(self) -> None:
        """Start the processing loop in a background thread."""
        if self._running:
            logger.warning("Orchestrator already running")
            return

        # Get sfreq from muse manager config
        self._sfreq = self._muse._sampling_rate

        self._running = True
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="orchestrator",
        )
        self._thread.start()
        logger.info("Orchestrator started @ %.0f Hz", self._update_rate)

    def stop(self) -> None:
        """Stop the processing loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("Orchestrator stopped")

    def set_normalization_method(self, method: str) -> None:
        """Change the active normalization method.

        Parameters
        ----------
        method : str
            One of ``"minmax"``, ``"zscore"``, ``"baseline"``, ``"percentile"``.
        """
        self._current_method = method
        logger.info("Normalization method set to: %s", method)

    @property
    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        """Main processing loop — runs at ``update_rate`` Hz."""
        interval = 1.0 / self._update_rate

        while self._running:
            tick_start = time.monotonic()

            try:
                self._tick()
            except Exception:
                logger.exception("Error in orchestrator tick")

            # Sleep for remainder of interval
            elapsed = time.monotonic() - tick_start
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _tick(self) -> None:
        """Single processing tick — process all devices and push results."""
        all_bands: dict[str, dict[str, float]] = {}
        all_relative: dict[str, dict[str, float]] = {}

        for device_id, device in self._muse.devices.items():
            if device.buffer is None or device.buffer.n_samples == 0:
                continue

            # Get current buffer data
            data = device.buffer.get_data()

            # Need minimum samples for meaningful PSD
            min_samples = int(self._sfreq * 2)  # at least 2 seconds
            if data.shape[1] < min_samples:
                continue

            # Run full DSP pipeline
            result = self._processor.process(data, self._sfreq)

            # Mean band power across channels for LSL/UI
            abs_bands_mean = {
                name: float(np.mean(power))
                for name, power in result["absolute_bands"].items()
            }
            rel_bands_mean = {
                name: float(np.mean(power))
                for name, power in result["relative_bands"].items()
            }

            all_bands[device_id] = abs_bands_mean
            all_relative[device_id] = rel_bands_mean

            # Update alpha metrics
            self._alpha.update(device_id, result["relative_bands"])

            # Push to LSL
            self._lsl.push_bands(device_id, abs_bands_mean)

        # Get normalized alpha for all devices
        alpha_metrics = self._alpha.get_all_metrics(method=self._current_method)

        # Push combined alpha to LSL
        self._lsl.push_alpha_metrics(alpha_metrics)

        # Emit to WebSocket callback
        if self._on_metrics_update and (all_bands or alpha_metrics):
            self._on_metrics_update({
                "alpha_metrics": alpha_metrics,
                "absolute_bands": all_bands,
                "relative_bands": all_relative,
                "normalization_method": self._current_method,
            })
