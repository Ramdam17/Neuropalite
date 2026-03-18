"""Streaming orchestrator — the central real-time processing loop.

Ties together all core modules into a single processing pipeline:

    MuseManager (buffers) → SignalProcessor → AlphaMetricsCalculator
                                ↓                    ↓
                          LSLStreamer            SocketIO
                          (10 Hz)               (30 Hz)

The orchestrator runs in a background thread, pulling data from each
device's CircularBuffer at a configurable rate, processing it through
the DSP pipeline, and pushing results to both LSL outlets (for Unity /
LabRecorder) and WebSocket events (for the Opalite dashboard).

Two output loops run at different rates:
- **Processing loop** (10 Hz): DSP + LSL push — this is the "science" rate
- **UI broadcast loop** (30 Hz): WebSocket emit — this is the "display" rate,
  which re-sends the latest computed values for smooth animation.

References
----------
- Lachaux et al. (1999). Measuring phase synchrony in brain signals.
  Human Brain Mapping, 8(4), 194–208.
"""

import logging
import threading
import time
from typing import Any

import numpy as np

from neuropalite.core.alpha_metrics import AlphaMetricsCalculator
from neuropalite.core.lsl_streamer import LSLStreamer
from neuropalite.core.muse_manager import DeviceStatus, MuseManager
from neuropalite.core.signal_processor import SignalProcessor

logger = logging.getLogger(__name__)

# Minimum samples needed for meaningful PSD estimation
# At 256 Hz with 4s Welch window, need at least 1024 samples
MIN_SAMPLES_FOR_PROCESSING = 1024


class StreamingOrchestrator:
    """Orchestrates the full real-time processing pipeline.

    Parameters
    ----------
    muse_manager : MuseManager
        Connected Muse device manager.
    signal_processor : SignalProcessor
        Configured signal processing pipeline.
    alpha_calculator : AlphaMetricsCalculator
        Alpha metrics calculator with normalization.
    lsl_streamer : LSLStreamer
        LSL outlet manager.
    processing_config : dict
        Parsed ``processing_config.yaml``.

    Example
    -------
    >>> orch = StreamingOrchestrator(muse_mgr, proc, alpha, lsl, proc_cfg)
    >>> orch.start()
    >>> # ... application runs ...
    >>> orch.stop()
    """

    def __init__(
        self,
        muse_manager: MuseManager,
        signal_processor: SignalProcessor,
        alpha_calculator: AlphaMetricsCalculator,
        lsl_streamer: LSLStreamer,
        processing_config: dict[str, Any],
    ) -> None:
        self._muse = muse_manager
        self._processor = signal_processor
        self._alpha = alpha_calculator
        self._lsl = lsl_streamer
        self._config = processing_config

        stream_cfg = processing_config["streaming"]
        self._lsl_rate = stream_cfg["lsl_update_rate"]
        self._ws_rate = stream_cfg["websocket_update_rate"]
        self._sfreq = muse_manager.config["acquisition"]["sampling_rate"]

        # Current normalization method (switchable from UI)
        self._norm_method: str = processing_config["normalization"]["default_method"]

        # Latest computed values for UI broadcast
        self._latest_bands: dict[str, dict[str, float]] = {}
        self._latest_alpha: dict[str, float] = {}
        self._latest_lock = threading.Lock()

        # SocketIO reference — set via set_socketio()
        self._socketio = None

        # Control flags
        self._running = False
        self._recording = False
        self._processing_thread: threading.Thread | None = None
        self._broadcast_thread: threading.Thread | None = None

        logger.info(
            "StreamingOrchestrator initialized: LSL@%d Hz, WS@%d Hz",
            self._lsl_rate,
            self._ws_rate,
        )

    def set_socketio(self, socketio) -> None:
        """Attach the SocketIO instance for WebSocket broadcasting.

        Parameters
        ----------
        socketio : flask_socketio.SocketIO
            The initialized SocketIO instance from the Flask app.
        """
        self._socketio = socketio

    def set_normalization(self, method: str) -> None:
        """Change the active normalization method.

        Parameters
        ----------
        method : str
            One of ``"minmax"``, ``"zscore"``, ``"baseline"``, ``"percentile"``.
        """
        self._norm_method = method
        logger.info("Normalization method changed to: %s", method)

    def start_baseline_calibration(self, duration: float = 30.0) -> None:
        """Start a baseline calibration phase.

        Collects alpha power values for ``duration`` seconds, then sets
        the baseline for each device. This enables the "baseline"
        normalization method.

        Parameters
        ----------
        duration : float
            Calibration duration in seconds (default: 30).
        """
        threading.Thread(
            target=self._calibration_loop,
            args=(duration,),
            daemon=True,
            name="baseline-calibration",
        ).start()

    def _calibration_loop(self, duration: float) -> None:
        """Collect baseline data and calibrate each device."""
        logger.info("Baseline calibration started (%.0fs)...", duration)

        if self._socketio:
            self._socketio.emit("calibration_status", {"active": True, "duration": duration})

        baseline_data: dict[str, list[float]] = {
            did: [] for did in self._muse.devices
        }

        start_time = time.monotonic()
        interval = 1.0 / self._lsl_rate

        while time.monotonic() - start_time < duration:
            for device_id, device in self._muse.devices.items():
                if device.status != DeviceStatus.CONNECTED or device.buffer is None:
                    continue
                if device.buffer.n_samples < MIN_SAMPLES_FOR_PROCESSING:
                    continue

                data = device.buffer.get_data()
                result = self._processor.process(data, self._sfreq)
                raw_alpha = self._alpha.update(device_id, result["relative_bands"])
                baseline_data[device_id].append(raw_alpha)

            time.sleep(interval)

        # Set baselines
        for device_id, values in baseline_data.items():
            if values:
                self._alpha.calibrate_baseline(device_id, values)

        logger.info("Baseline calibration complete")
        if self._socketio:
            self._socketio.emit("calibration_status", {"active": False})

    def start(self) -> None:
        """Start the processing and broadcast loops."""
        if self._running:
            logger.warning("Orchestrator already running")
            return

        self._running = True
        self._recording = True

        self._processing_thread = threading.Thread(
            target=self._processing_loop,
            daemon=True,
            name="processing-loop",
        )
        self._broadcast_thread = threading.Thread(
            target=self._broadcast_loop,
            daemon=True,
            name="broadcast-loop",
        )

        self._processing_thread.start()
        self._broadcast_thread.start()

        logger.info("Orchestrator started")

    def stop(self) -> None:
        """Stop all processing and broadcast loops."""
        self._running = False
        self._recording = False

        if self._processing_thread:
            self._processing_thread.join(timeout=5)
        if self._broadcast_thread:
            self._broadcast_thread.join(timeout=5)

        logger.info("Orchestrator stopped")

    @property
    def is_running(self) -> bool:
        """Whether the orchestrator is actively processing."""
        return self._running

    # ------------------------------------------------------------------
    # Processing loop — runs at LSL rate (10 Hz)
    # ------------------------------------------------------------------

    def _processing_loop(self) -> None:
        """Main DSP loop: buffer → filter → PSD → bands → alpha → LSL."""
        interval = 1.0 / self._lsl_rate
        logger.info("Processing loop started @ %d Hz", self._lsl_rate)

        while self._running:
            loop_start = time.monotonic()

            for device_id, device in self._muse.devices.items():
                if device.status != DeviceStatus.CONNECTED:
                    continue
                if device.buffer is None or device.buffer.n_samples < MIN_SAMPLES_FOR_PROCESSING:
                    continue

                try:
                    self._process_device(device_id, device)
                except Exception:
                    logger.exception("Processing error for %s", device_id)

            # Sleep for remaining interval
            elapsed = time.monotonic() - loop_start
            sleep_time = max(0, interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _process_device(self, device_id: str, device) -> None:
        """Run DSP pipeline for a single device and push to LSL."""
        data = device.buffer.get_data()

        # Full DSP pipeline
        result = self._processor.process(data, self._sfreq)

        # Update alpha metrics
        self._alpha.update(device_id, result["relative_bands"])
        alpha_value = self._alpha.get_metric(device_id, self._norm_method)

        # Mean band powers across channels for LSL + UI
        mean_bands = {
            name: float(np.mean(power))
            for name, power in result["relative_bands"].items()
        }

        # Push to LSL outlets
        self._lsl.push_bands(device_id, mean_bands)

        # Store latest values for UI broadcast
        with self._latest_lock:
            self._latest_bands[device_id] = mean_bands
            self._latest_alpha[device_id] = alpha_value

        # Push combined alpha metrics
        all_alpha = self._alpha.get_all_metrics(self._norm_method)
        self._lsl.push_alpha_metrics(all_alpha)

    # ------------------------------------------------------------------
    # Broadcast loop — runs at WebSocket rate (30 Hz)
    # ------------------------------------------------------------------

    def _broadcast_loop(self) -> None:
        """WebSocket broadcast loop: emit latest values to the dashboard."""
        interval = 1.0 / self._ws_rate
        logger.info("Broadcast loop started @ %d Hz", self._ws_rate)

        while self._running:
            loop_start = time.monotonic()

            if self._socketio:
                self._emit_status()
                self._emit_metrics()

            elapsed = time.monotonic() - loop_start
            sleep_time = max(0, interval - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _emit_status(self) -> None:
        """Emit Muse device status to the dashboard."""
        self._socketio.emit("muse_status", {
            "devices": self._muse.get_all_info(),
        })

    def _emit_metrics(self) -> None:
        """Emit alpha metrics and frequency bands to the dashboard."""
        with self._latest_lock:
            bands = dict(self._latest_bands)
            alpha = dict(self._latest_alpha)

        if not alpha:
            return

        # Alpha metrics: { a: float, b: float }
        device_ids = list(self._muse.devices.keys())
        alpha_payload = {}
        if len(device_ids) >= 1:
            alpha_payload["a"] = alpha.get(device_ids[0], 0.0)
        if len(device_ids) >= 2:
            alpha_payload["b"] = alpha.get(device_ids[1], 0.0)

        self._socketio.emit("alpha_metrics", alpha_payload)

        # Frequency bands: { a: [5 values], b: [5 values] }
        band_names = list(self._processor.band_defs.keys())
        bands_payload = {}
        if len(device_ids) >= 1 and device_ids[0] in bands:
            bands_payload["a"] = [bands[device_ids[0]].get(b, 0.0) for b in band_names]
        if len(device_ids) >= 2 and device_ids[1] in bands:
            bands_payload["b"] = [bands[device_ids[1]].get(b, 0.0) for b in band_names]

        if bands_payload:
            self._socketio.emit("frequency_bands", bands_payload)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> dict[str, Any]:
        """Return orchestrator status for API/logging.

        Returns
        -------
        dict[str, Any]
            Running state, normalization method, LSL status, device count.
        """
        return {
            "running": self._running,
            "recording": self._recording,
            "normalization_method": self._norm_method,
            "lsl": self._lsl.get_status(),
            "devices": self._muse.get_all_info(),
        }
