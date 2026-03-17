"""Muse headband connection manager.

Handles Bluetooth discovery, LSL stream creation, data ingestion into
CircularBuffers, and auto-reconnection logic for one or more Muse S devices.

Architecture
------------
Each Muse device gets its own:
- ``muselsl.stream`` process (Bluetooth → LSL)
- ``pylsl.StreamInlet`` (LSL → Python)
- ``CircularBuffer`` (rolling window for DSP)
- Monitoring thread (quality, battery, reconnect)

References
----------
- muselsl: https://github.com/alexandrebarachant/muse-lsl
- pylsl:   https://github.com/labstreaminglayer/pylsl
"""

import logging
import subprocess
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

import numpy as np

from neuropalite.core.data_buffer import CircularBuffer

logger = logging.getLogger(__name__)


class DeviceStatus(Enum):
    """Connection status for a Muse device."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class MuseDevice:
    """State container for a single Muse headband.

    Parameters
    ----------
    device_id : str
        Identifier key from config (e.g. ``"muse_1"``).
    name : str
        Human-readable name (e.g. ``"Participant A"``).
    bluetooth_address : str
        Bluetooth MAC address.
    color : str
        Hex color for UI display.
    enabled : bool
        Whether this device should be connected.
    """

    device_id: str
    name: str
    bluetooth_address: str
    color: str = "#FFFFFF"
    enabled: bool = True
    status: DeviceStatus = DeviceStatus.DISCONNECTED
    battery: float = -1.0
    signal_quality: float = 0.0
    buffer: CircularBuffer | None = None
    _stream_process: subprocess.Popen | None = field(default=None, repr=False)
    _inlet: Any = field(default=None, repr=False)
    _monitor_thread: threading.Thread | None = field(default=None, repr=False)


class MuseManager:
    """Manages connections to one or more Muse S headbands.

    Parameters
    ----------
    muse_config : dict
        Parsed ``muse_config.yaml`` content.
    on_status_change : Callable, optional
        Callback ``(device_id, status, device_info)`` fired on status changes.
    """

    def __init__(
        self,
        muse_config: dict[str, Any],
        on_status_change: Callable | None = None,
    ) -> None:
        self.config = muse_config
        self.on_status_change = on_status_change
        self.devices: dict[str, MuseDevice] = {}
        self._running = False

        acq = muse_config["acquisition"]
        self._sampling_rate = acq["sampling_rate"]
        self._n_channels = len(acq["channels"])
        self._buffer_duration = acq["buffer_duration"]
        self._auto_reconnect = acq.get("auto_reconnect", True)
        self._reconnect_delay = acq.get("reconnect_delay", 5)
        self._max_reconnect = acq.get("max_reconnect_attempts", 10)

        # Initialize device objects
        for dev_id, dev_cfg in muse_config["muse_devices"].items():
            if not dev_cfg.get("enabled", True):
                logger.info("Device %s is disabled, skipping", dev_id)
                continue

            self.devices[dev_id] = MuseDevice(
                device_id=dev_id,
                name=dev_cfg["name"],
                bluetooth_address=dev_cfg["bluetooth_address"],
                color=dev_cfg.get("color", "#FFFFFF"),
                enabled=True,
                buffer=CircularBuffer(
                    n_channels=self._n_channels,
                    buffer_duration=self._buffer_duration,
                    sampling_rate=self._sampling_rate,
                ),
            )

        logger.info("MuseManager initialized with %d device(s)", len(self.devices))

    def connect(self, device_id: str) -> bool:
        """Attempt to connect a single Muse device.

        Starts the ``muselsl stream`` subprocess which handles Bluetooth
        connection and creates an LSL outlet, then resolves that outlet
        with ``pylsl`` and begins pulling samples into the CircularBuffer.

        Parameters
        ----------
        device_id : str
            Key in ``self.devices``.

        Returns
        -------
        bool
            True if connection was established successfully.
        """
        import pylsl

        device = self.devices[device_id]
        device.status = DeviceStatus.CONNECTING
        self._emit_status(device)

        try:
            # Start muselsl stream subprocess
            logger.info(
                "Starting muselsl stream for %s (%s)...",
                device.name,
                device.bluetooth_address,
            )
            device._stream_process = subprocess.Popen(
                [
                    "muselsl",
                    "stream",
                    "--address",
                    device.bluetooth_address,
                    "--name",
                    device.device_id,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Wait for LSL stream to become available
            logger.info("Waiting for LSL stream '%s'...", device.device_id)
            streams = pylsl.resolve_byprop("name", device.device_id, timeout=30.0)

            if not streams:
                raise ConnectionError(
                    f"No LSL stream found for {device.device_id} after 30s"
                )

            device._inlet = pylsl.StreamInlet(streams[0], max_chunklen=12)
            device.status = DeviceStatus.CONNECTED
            self._emit_status(device)

            # Start ingestion thread
            device._monitor_thread = threading.Thread(
                target=self._ingest_loop,
                args=(device,),
                daemon=True,
                name=f"ingest-{device.device_id}",
            )
            device._monitor_thread.start()

            logger.info("Connected: %s (%s)", device.name, device.device_id)
            return True

        except Exception:
            logger.exception("Failed to connect %s", device.device_id)
            device.status = DeviceStatus.ERROR
            self._emit_status(device)
            self._cleanup_device(device)
            return False

    def connect_all(self) -> dict[str, bool]:
        """Connect all enabled devices.

        Returns
        -------
        dict[str, bool]
            Mapping ``device_id → success``.
        """
        self._running = True
        results = {}
        for device_id in self.devices:
            results[device_id] = self.connect(device_id)
        return results

    def disconnect(self, device_id: str) -> None:
        """Disconnect a single Muse device."""
        device = self.devices[device_id]
        self._cleanup_device(device)
        device.status = DeviceStatus.DISCONNECTED
        self._emit_status(device)
        logger.info("Disconnected: %s", device.device_id)

    def disconnect_all(self) -> None:
        """Disconnect all devices and stop monitoring."""
        self._running = False
        for device_id in list(self.devices.keys()):
            self.disconnect(device_id)

    def get_device_info(self, device_id: str) -> dict[str, Any]:
        """Return a serializable snapshot of device state.

        Parameters
        ----------
        device_id : str
            Device key.

        Returns
        -------
        dict[str, Any]
            Contains status, battery, signal_quality, name, color, n_samples.
        """
        device = self.devices[device_id]
        return {
            "device_id": device.device_id,
            "name": device.name,
            "color": device.color,
            "status": device.status.value,
            "battery": device.battery,
            "signal_quality": device.signal_quality,
            "n_samples": device.buffer.n_samples if device.buffer else 0,
        }

    def get_all_info(self) -> dict[str, dict[str, Any]]:
        """Return info for all devices."""
        return {did: self.get_device_info(did) for did in self.devices}

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _ingest_loop(self, device: MuseDevice) -> None:
        """Pull samples from LSL inlet and push into the CircularBuffer.

        Runs in a daemon thread until ``self._running`` is False or the
        inlet disconnects.
        """
        logger.info("Ingestion started for %s", device.device_id)
        consecutive_failures = 0

        while self._running and device.status == DeviceStatus.CONNECTED:
            try:
                samples, timestamps = device._inlet.pull_chunk(
                    timeout=1.0, max_samples=64
                )
                if timestamps:
                    chunk = np.array(samples).T  # (n_channels, n_samples)
                    device.buffer.push_chunk(chunk)
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    if consecutive_failures > 10:
                        logger.warning(
                            "No data from %s for ~10s, may be disconnected",
                            device.device_id,
                        )
                        if self._auto_reconnect:
                            self._attempt_reconnect(device)
                            return

            except Exception:
                logger.exception("Ingestion error for %s", device.device_id)
                if self._auto_reconnect:
                    self._attempt_reconnect(device)
                    return
                break

        logger.info("Ingestion stopped for %s", device.device_id)

    def _attempt_reconnect(self, device: MuseDevice) -> None:
        """Try to reconnect a device up to ``max_reconnect_attempts`` times."""
        device.status = DeviceStatus.RECONNECTING
        self._emit_status(device)
        self._cleanup_device(device)

        for attempt in range(1, self._max_reconnect + 1):
            if not self._running:
                return
            logger.info(
                "Reconnect attempt %d/%d for %s",
                attempt,
                self._max_reconnect,
                device.device_id,
            )
            time.sleep(self._reconnect_delay)
            if self.connect(device.device_id):
                return

        logger.error("Max reconnect attempts reached for %s", device.device_id)
        device.status = DeviceStatus.ERROR
        self._emit_status(device)

    def _cleanup_device(self, device: MuseDevice) -> None:
        """Stop stream process and close inlet for a device."""
        if device._inlet:
            try:
                device._inlet.close_stream()
            except Exception:
                pass
            device._inlet = None

        if device._stream_process:
            try:
                device._stream_process.terminate()
                device._stream_process.wait(timeout=5)
            except Exception:
                pass
            device._stream_process = None

    def _emit_status(self, device: MuseDevice) -> None:
        """Fire the on_status_change callback if registered."""
        if self.on_status_change:
            try:
                self.on_status_change(
                    device.device_id,
                    device.status.value,
                    self.get_device_info(device.device_id),
                )
            except Exception:
                logger.exception("Error in on_status_change callback")
