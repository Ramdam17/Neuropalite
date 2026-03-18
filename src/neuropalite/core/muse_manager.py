"""Muse headband connection manager via Bleak (BLE GATT).

Handles direct Bluetooth Low Energy connection to Muse S devices,
binary EEG data parsing, and ingestion into CircularBuffers. Replaces
the previous muse-lsl subprocess approach with direct BLE communication
using the Bleak library.

Architecture
------------
Each Muse device gets its own:
- ``bleak.BleakClient`` (async BLE connection)
- Notification handlers for EEG GATT characteristics
- ``CircularBuffer`` (rolling window for DSP)
- Dedicated asyncio event loop in a daemon thread
- Optional telemetry monitoring (battery, temperature)

BLE Protocol
------------
The Muse S exposes a proprietary GATT service (``0000fe8d-...``) with
characteristics for each EEG channel. Each notification contains 12
samples packed as ``uint:12`` (12-bit unsigned integers). Raw values are
converted to microvolts via::

    µV = SCALE_FACTOR × (raw - 2048)

where ``SCALE_FACTOR = 0.48828125``.

Data is accumulated across 4 channel notifications. When the last
channel (AF7, handle 0x0024) fires, all 12 samples × 4 channels are
pushed to the CircularBuffer as a single chunk.

References
----------
- Bleak: https://bleak.readthedocs.io/
- Muse BLE protocol: reverse-engineered from BleMuse project
- Bitstring: https://github.com/scott-griffiths/bitstring
"""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

import bitstring
import numpy as np
from bleak import BleakClient, BleakScanner

from neuropalite.core.data_buffer import CircularBuffer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Muse BLE constants (from BleMuse/constants.py)
# ---------------------------------------------------------------------------

MUSE_GATT_CUSTOM_SERVICE = "0000fe8d-0000-1000-8000-00805f9b34fb"
MUSE_GATT_ATTR_STREAM_TOGGLE = "273e0001-4c4d-454d-96be-f03bac821358"
MUSE_GATT_ATTR_TP9 = "273e0003-4c4d-454d-96be-f03bac821358"
MUSE_GATT_ATTR_AF7 = "273e0004-4c4d-454d-96be-f03bac821358"
MUSE_GATT_ATTR_AF8 = "273e0005-4c4d-454d-96be-f03bac821358"
MUSE_GATT_ATTR_TP10 = "273e0006-4c4d-454d-96be-f03bac821358"
MUSE_GATT_ATTR_TELEMETRY = "273e000b-4c4d-454d-96be-f03bac821358"

# Commands sent to the stream toggle characteristic
S_ASK = b"\x02\x73\x0a"  # Query device state
S_STREAM = b"\x02\x64\x0a"  # Start streaming

# EEG data parameters
MUSE_EEG_SCALE_FACTOR = 0.48828125  # Convert raw 12-bit to µV
MUSE_EEG_SAMPLES_PER_PACKET = 12  # Samples per BLE notification
MUSE_SAMPLING_RATE = 256  # Hz

# EEG channel GATT characteristics in notification order
EEG_CHANNEL_ATTRS = [
    MUSE_GATT_ATTR_TP9,
    MUSE_GATT_ATTR_AF7,
    MUSE_GATT_ATTR_AF8,
    MUSE_GATT_ATTR_TP10,
]

# Channel names in data array order (TP9=0, AF7=1, AF8=2, TP10=3)
EEG_CHANNEL_NAMES = ["TP9", "AF7", "AF8", "TP10"]

# Mapping from GATT characteristic UUID → row index in the data array.
# This determines where each channel's samples are stored.
EEG_CHAR_TO_INDEX = {
    MUSE_GATT_ATTR_TP9: 0,
    MUSE_GATT_ATTR_AF7: 1,
    MUSE_GATT_ATTR_AF8: 2,
    MUSE_GATT_ATTR_TP10: 3,
}

# The characteristic whose notification triggers a push to the buffer.
# AF7 is the last channel notified in each Muse BLE cycle.
EEG_TRIGGER_CHAR = MUSE_GATT_ATTR_AF7


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
        Bluetooth MAC address or CoreBluetooth UUID.
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

    # Internal BLE state (not serialized)
    _client: BleakClient | None = field(default=None, repr=False)
    _eeg_data: np.ndarray | None = field(default=None, repr=False)
    _loop: asyncio.AbstractEventLoop | None = field(default=None, repr=False)
    _thread: threading.Thread | None = field(default=None, repr=False)


class MuseManager:
    """Manages BLE connections to one or more Muse S headbands.

    Uses Bleak for direct BLE GATT communication. Each device runs its
    own asyncio event loop in a daemon thread.

    Parameters
    ----------
    muse_config : dict
        Parsed ``muse_config.yaml`` content.
    on_status_change : Callable, optional
        Callback ``(device_id, status, device_info)`` fired on status changes.

    Example
    -------
    >>> manager = MuseManager(muse_config)
    >>> manager.connect_all()
    >>> # ... data flows into device.buffer ...
    >>> manager.disconnect_all()
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
                _eeg_data=np.zeros(
                    (self._n_channels, MUSE_EEG_SAMPLES_PER_PACKET),
                    dtype=np.float64,
                ),
            )

        logger.info("MuseManager initialized with %d device(s)", len(self.devices))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def connect(self, device_id: str) -> bool:
        """Connect a single Muse device via BLE.

        Starts a dedicated thread running an asyncio event loop for the
        Bleak BLE client. Returns True once the connection is established
        and EEG streaming has started.

        Parameters
        ----------
        device_id : str
            Key in ``self.devices``.

        Returns
        -------
        bool
            True if connection was established successfully.
        """
        device = self.devices[device_id]
        device.status = DeviceStatus.CONNECTING
        self._emit_status(device)

        # Event to signal when connection is established (or failed)
        connected_event = threading.Event()
        connection_result: dict[str, bool] = {"success": False}

        def _run_loop():
            """Thread target: create event loop and run the BLE connection."""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            device._loop = loop

            try:
                loop.run_until_complete(
                    self._ble_connect(device, connected_event, connection_result)
                )
            except Exception:
                logger.exception("BLE loop error for %s", device_id)
            finally:
                loop.close()

        device._thread = threading.Thread(
            target=_run_loop,
            daemon=True,
            name=f"ble-{device_id}",
        )
        device._thread.start()

        # Wait for connection result (timeout 30s)
        connected_event.wait(timeout=30.0)

        if connection_result["success"]:
            logger.info("Connected: %s (%s)", device.name, device_id)
            return True
        else:
            logger.error("Failed to connect: %s", device_id)
            device.status = DeviceStatus.ERROR
            self._emit_status(device)
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
    # BLE connection (async)
    # ------------------------------------------------------------------

    async def _ble_connect(
        self,
        device: MuseDevice,
        connected_event: threading.Event,
        connection_result: dict[str, bool],
    ) -> None:
        """Async BLE connection flow for a single device.

        Discovers the device, connects, enables streaming, subscribes to
        EEG notifications, and keeps the connection alive.

        Parameters
        ----------
        device : MuseDevice
            The device to connect.
        connected_event : threading.Event
            Signalled when connection succeeds or fails.
        connection_result : dict
            Mutable dict to communicate success/failure to the calling thread.
        """
        try:
            # Discover BLE devices
            logger.info(
                "Scanning for %s (%s)...",
                device.name,
                device.bluetooth_address,
            )
            ble_devices = await BleakScanner.discover(timeout=10.0)
            ble_device = next(
                (d for d in ble_devices if d.address == device.bluetooth_address),
                None,
            )

            if not ble_device:
                logger.error(
                    "Device %s not found during BLE scan", device.bluetooth_address
                )
                connected_event.set()
                return

            # Connect
            client = BleakClient(ble_device)
            await client.connect()
            device._client = client

            logger.info("BLE connected to %s", device.bluetooth_address)

            # Find Muse GATT service and enable streaming
            services = client.services
            muse_service = next(
                (s for s in services if s.uuid == MUSE_GATT_CUSTOM_SERVICE),
                None,
            )

            if not muse_service:
                logger.error("Muse GATT service not found on %s", device.device_id)
                await client.disconnect()
                connected_event.set()
                return

            # Send stream commands
            await client.write_gatt_char(MUSE_GATT_ATTR_STREAM_TOGGLE, S_ASK)
            await client.write_gatt_char(MUSE_GATT_ATTR_STREAM_TOGGLE, S_STREAM)
            logger.info("Streaming enabled on %s", device.device_id)

            # Subscribe to EEG notifications
            def _make_eeg_handler(char_uuid: str):
                """Create a notification handler bound to a specific characteristic."""
                channel_idx = EEG_CHAR_TO_INDEX[char_uuid]

                def handler(sender, data: bytearray):
                    self._handle_eeg_notification(device, channel_idx, char_uuid, data)

                return handler

            for char_uuid in EEG_CHANNEL_ATTRS:
                await client.start_notify(char_uuid, _make_eeg_handler(char_uuid))

            # Subscribe to telemetry (battery/temperature)
            try:
                await client.start_notify(
                    MUSE_GATT_ATTR_TELEMETRY,
                    lambda sender, data: self._handle_telemetry(device, data),
                )
            except Exception:
                logger.warning("Telemetry not available on %s", device.device_id)

            # Mark as connected
            device.status = DeviceStatus.CONNECTED
            device.signal_quality = 1.0
            self._emit_status(device)
            connection_result["success"] = True
            connected_event.set()

            # Keep alive — the BLE connection stays open as long as
            # this coroutine is running and the event loop is active.
            while self._running and device.status == DeviceStatus.CONNECTED:
                await asyncio.sleep(1.0)

        except Exception:
            logger.exception("BLE connection error for %s", device.device_id)
            device.status = DeviceStatus.ERROR
            self._emit_status(device)
            connected_event.set()

            if self._auto_reconnect and self._running:
                await self._attempt_reconnect_async(device)

    # ------------------------------------------------------------------
    # BLE notification handlers
    # ------------------------------------------------------------------

    def _handle_eeg_notification(
        self,
        device: MuseDevice,
        channel_idx: int,
        char_uuid: str,
        raw_data: bytearray,
    ) -> None:
        """Process a raw EEG BLE notification.

        Each notification contains 12 samples packed as uint:12.
        The first uint:16 is a packet counter (discarded).

        Data is accumulated in ``device._eeg_data``. When the trigger
        channel (AF7) fires, the complete 4×12 chunk is pushed to the
        CircularBuffer.

        Parameters
        ----------
        device : MuseDevice
            The source device.
        channel_idx : int
            Row index in the data array (0=TP9, 1=AF7, 2=AF8, 3=TP10).
        char_uuid : str
            GATT characteristic UUID (used to detect trigger channel).
        raw_data : bytearray
            Raw BLE notification payload.
        """
        # Parse: 1 × uint:16 (counter) + 12 × uint:12 (samples)
        bits = bitstring.Bits(bytes=raw_data)
        pattern = "uint:16," + ",".join(["uint:12"] * MUSE_EEG_SAMPLES_PER_PACKET)
        values = bits.unpack(pattern)
        samples = values[1:]  # Discard packet counter

        # Convert to µV: SCALE_FACTOR × (raw - 2048)
        device._eeg_data[channel_idx, :] = MUSE_EEG_SCALE_FACTOR * (
            np.array(samples, dtype=np.float64) - 2048
        )

        # Push to buffer when the trigger channel fires
        if char_uuid == EEG_TRIGGER_CHAR:
            device.buffer.push_chunk(device._eeg_data.copy())
            if device.buffer.n_samples % 256 == 0:  # Log every ~1 second
                logger.debug(
                    "%s: %d samples in buffer (%.1fs)",
                    device.device_id,
                    device.buffer.n_samples,
                    device.buffer.n_samples / MUSE_SAMPLING_RATE,
                )

    def _handle_telemetry(
        self,
        device: MuseDevice,
        raw_data: bytearray,
    ) -> None:
        """Process a telemetry notification (battery, temperature, etc.).

        Parameters
        ----------
        device : MuseDevice
            The source device.
        raw_data : bytearray
            Raw BLE notification payload.
        """
        try:
            bits = bitstring.Bits(bytes=raw_data)
            pattern = "uint:16,uint:16,uint:16,uint:16,uint:16"
            values = bits.unpack(pattern)
            data = values[1:]

            device.battery = data[0] / 512.0  # Percentage
            # data[1] = fuel gauge (× 2.2), data[2] = ADC voltage, data[3] = temperature
            logger.debug(
                "Telemetry %s: battery=%.0f%%",
                device.device_id,
                device.battery,
            )
        except Exception:
            logger.debug("Failed to parse telemetry for %s", device.device_id)

    # ------------------------------------------------------------------
    # Reconnection
    # ------------------------------------------------------------------

    async def _attempt_reconnect_async(self, device: MuseDevice) -> None:
        """Async reconnection loop for a device."""
        device.status = DeviceStatus.RECONNECTING
        self._emit_status(device)

        for attempt in range(1, self._max_reconnect + 1):
            if not self._running:
                return

            logger.info(
                "Reconnect attempt %d/%d for %s",
                attempt,
                self._max_reconnect,
                device.device_id,
            )
            await asyncio.sleep(self._reconnect_delay)

            try:
                connected_event = threading.Event()
                result = {"success": False}
                await self._ble_connect(device, connected_event, result)
                if result["success"]:
                    return
            except Exception:
                logger.exception("Reconnect failed for %s", device.device_id)

        logger.error("Max reconnect attempts reached for %s", device.device_id)
        device.status = DeviceStatus.ERROR
        self._emit_status(device)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def _cleanup_device(self, device: MuseDevice) -> None:
        """Disconnect BLE client and stop the event loop thread."""
        if device._client and device._client.is_connected:
            # Schedule disconnect on the device's event loop
            if device._loop and device._loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    device._client.disconnect(), device._loop
                )
            device._client = None

        if device._loop and device._loop.is_running():
            device._loop.call_soon_threadsafe(device._loop.stop)

        if device._thread and device._thread.is_alive():
            device._thread.join(timeout=5)

        device._loop = None
        device._thread = None

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
