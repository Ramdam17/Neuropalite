"""LSL outlet management for streaming processed EEG data.

Creates and manages three types of LSL outlets per Muse device:

1. **Raw EEG** — 4 channels @ 256 Hz (passthrough from CircularBuffer)
2. **Frequency Bands** — 5 channels (δ, θ, α, β, γ) @ configurable rate
3. **Alpha Metrics** — 1 channel (normalized alpha) @ configurable rate

A separate ``AlphaMetrics`` outlet aggregates both devices into a single
2-channel stream for easy consumption by Unity.

References
----------
- LSL specification: https://labstreaminglayer.readthedocs.io/
- XDF format: https://github.com/sccn/xdf
"""

import logging
from typing import Any

import pylsl

logger = logging.getLogger(__name__)


class LSLOutlet:
    """Wrapper around a single pylsl.StreamOutlet.

    Parameters
    ----------
    name : str
        Stream name (e.g. ``"Muse1_Raw"``).
    stream_type : str
        LSL stream type (e.g. ``"EEG"``, ``"Markers"``, ``"Alpha"``).
    n_channels : int
        Number of channels.
    srate : float
        Nominal sampling rate in Hz. Use 0 for irregular rate.
    channel_names : list[str] | None
        Optional channel labels.
    source_id : str
        Unique source identifier for stream resolution.
    """

    def __init__(
        self,
        name: str,
        stream_type: str,
        n_channels: int,
        srate: float,
        channel_names: list[str] | None = None,
        source_id: str = "",
    ) -> None:
        self.name = name

        info = pylsl.StreamInfo(
            name=name,
            type=stream_type,
            channel_count=n_channels,
            nominal_srate=srate,
            channel_format=pylsl.cf_float32,
            source_id=source_id or f"neuropalite_{name}",
        )

        # Add channel metadata if provided
        if channel_names:
            channels = info.desc().append_child("channels")
            for ch_name in channel_names:
                ch = channels.append_child("channel")
                ch.append_child_value("label", ch_name)

        self._outlet = pylsl.StreamOutlet(info)
        logger.info(
            "LSL outlet created: %s (%s, %d ch @ %.0f Hz)",
            name,
            stream_type,
            n_channels,
            srate,
        )

    def push(self, sample: list[float]) -> None:
        """Push a single sample (list of floats)."""
        self._outlet.push_sample(sample)

    def push_chunk(self, chunk: list[list[float]]) -> None:
        """Push multiple samples at once."""
        self._outlet.push_chunk(chunk)

    @property
    def has_consumers(self) -> bool:
        """Whether any inlet is currently connected to this outlet."""
        return self._outlet.have_consumers()


class LSLStreamer:
    """Manages all LSL outlets for the Neuropalite system.

    Creates outlets for each Muse device (raw EEG, frequency bands)
    and a combined alpha metrics outlet.

    Parameters
    ----------
    muse_config : dict
        Parsed ``muse_config.yaml``.
    processing_config : dict
        Parsed ``processing_config.yaml``.
    """

    def __init__(
        self,
        muse_config: dict[str, Any],
        processing_config: dict[str, Any],
    ) -> None:
        self._muse_cfg = muse_config
        self._proc_cfg = processing_config

        acq = muse_config["acquisition"]
        self._sfreq = acq["sampling_rate"]
        self._channels = acq["channels"]
        stream_cfg = processing_config["streaming"]
        self._update_rate = stream_cfg["lsl_update_rate"]

        self._band_names = list(processing_config["frequency_bands"].keys())

        # Outlets indexed by device_id
        self.raw_outlets: dict[str, LSLOutlet] = {}
        self.band_outlets: dict[str, LSLOutlet] = {}

        # Per-device alpha outlets (AlphaPower_P1, AlphaPower_P2)
        self.alpha_outlets: dict[str, LSLOutlet] = {}

        self._device_ids: list[str] = []

    def setup(self, device_ids: list[str]) -> None:
        """Create all LSL outlets for the given devices.

        Parameters
        ----------
        device_ids : list[str]
            Active device identifiers (e.g. ``["muse_1", "muse_2"]``).
        """
        self._device_ids = device_ids

        for dev_id in device_ids:
            # Raw EEG outlet — full sampling rate
            self.raw_outlets[dev_id] = LSLOutlet(
                name=f"{dev_id}_Raw",
                stream_type="EEG",
                n_channels=len(self._channels),
                srate=self._sfreq,
                channel_names=self._channels,
                source_id=f"neuropalite_{dev_id}_raw",
            )

            # Frequency bands outlet — at LSL update rate
            self.band_outlets[dev_id] = LSLOutlet(
                name=f"{dev_id}_Bands",
                stream_type="FFT",
                n_channels=len(self._band_names),
                srate=self._update_rate,
                channel_names=self._band_names,
                source_id=f"neuropalite_{dev_id}_bands",
            )

        # Per-device alpha outlets: AlphaPower_P1, AlphaPower_P2, ...
        for i, dev_id in enumerate(device_ids, 1):
            stream_name = f"AlphaPower_P{i}"
            self.alpha_outlets[dev_id] = LSLOutlet(
                name=stream_name,
                stream_type="Alpha",
                n_channels=1,
                srate=self._update_rate,
                channel_names=["alpha"],
                source_id=f"neuropalite_{stream_name}",
            )

        logger.info(
            "LSL streamer setup complete: %d raw + %d band + %d alpha outlets",
            len(self.raw_outlets),
            len(self.band_outlets),
            len(self.alpha_outlets),
        )

    def push_raw(self, device_id: str, sample: list[float]) -> None:
        """Push a raw EEG sample for a device.

        Parameters
        ----------
        device_id : str
            Device identifier.
        sample : list[float]
            Single sample, length ``n_channels``.
        """
        if device_id in self.raw_outlets:
            self.raw_outlets[device_id].push(sample)

    def push_bands(
        self, device_id: str, band_powers: dict[str, float]
    ) -> None:
        """Push frequency band powers for a device.

        Parameters
        ----------
        device_id : str
            Device identifier.
        band_powers : dict[str, float]
            Mapping band name → mean power across channels.
        """
        if device_id in self.band_outlets:
            sample = [band_powers.get(b, 0.0) for b in self._band_names]
            self.band_outlets[device_id].push(sample)

    def push_alpha_metrics(self, metrics: dict[str, float]) -> None:
        """Push alpha metrics to per-device outlets (AlphaPower_P1, AlphaPower_P2).

        Parameters
        ----------
        metrics : dict[str, float]
            Mapping ``device_id → normalized_alpha``.
        """
        for dev_id, value in metrics.items():
            if dev_id in self.alpha_outlets:
                self.alpha_outlets[dev_id].push([value])

    def get_status(self) -> dict[str, Any]:
        """Return streaming status for all outlets.

        Returns
        -------
        dict[str, Any]
            Contains active outlet count, consumer info, update rate.
        """
        active = 0
        consumers = 0

        all_outlets = (
            list(self.raw_outlets.values())
            + list(self.band_outlets.values())
            + list(self.alpha_outlets.values())
        )
        for outlet in all_outlets:
            active += 1
            if outlet.has_consumers:
                consumers += 1

        return {
            "active_outlets": active,
            "connected_consumers": consumers,
            "update_rate_hz": self._update_rate,
            "streaming": active > 0,
        }
