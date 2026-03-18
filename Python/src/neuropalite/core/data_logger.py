"""Session data logger for metrics export.

Records timestamped alpha metrics and frequency band powers during a
session, and exports them as BIDS-inspired CSV files. Raw EEG is
captured via LabRecorder (subscribing to LSL outlets) → XDF files.

Output structure::

    data/derivative/
        ses-YYYYMMDDTHHMMSS/
            neuropalite_alpha-metrics.csv
            neuropalite_band-powers.csv
            neuropalite_session-info.json

References
----------
- BIDS specification: https://bids.neuroimaging.io/
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DataLogger:
    """Collects and exports session metrics.

    Parameters
    ----------
    muse_config : dict
        Parsed ``muse_config.yaml``.
    processing_config : dict
        Parsed ``processing_config.yaml``.
    output_dir : str | Path
        Root output directory (default: ``data/derivative``).
    """

    def __init__(
        self,
        muse_config: dict[str, Any],
        processing_config: dict[str, Any],
        output_dir: str | Path = "data/derivative",
    ) -> None:
        self._muse_cfg = muse_config
        self._proc_cfg = processing_config
        self._output_dir = Path(output_dir)

        self._session_start: datetime | None = None
        self._alpha_records: list[dict[str, Any]] = []
        self._band_records: list[dict[str, Any]] = []

        self._band_names = list(processing_config["frequency_bands"].keys())
        self._device_ids = list(muse_config["muse_devices"].keys())

        logger.info("DataLogger initialized, output: %s", self._output_dir)

    def start_session(self) -> None:
        """Mark the beginning of a recording session."""
        self._session_start = datetime.now(timezone.utc)
        self._alpha_records.clear()
        self._band_records.clear()
        logger.info("Session started: %s", self._session_start.isoformat())

    def log_alpha(
        self,
        timestamp: float,
        device_id: str,
        raw_alpha: float,
        normalized_alpha: float,
        method: str,
    ) -> None:
        """Record an alpha metric observation.

        Parameters
        ----------
        timestamp : float
            Unix timestamp (``time.time()``).
        device_id : str
            Device identifier.
        raw_alpha : float
            Raw relative alpha power (before normalization).
        normalized_alpha : float
            Normalized alpha metric in [0, 1].
        method : str
            Normalization method used.
        """
        self._alpha_records.append({
            "timestamp": timestamp,
            "device_id": device_id,
            "raw_alpha": raw_alpha,
            "normalized_alpha": normalized_alpha,
            "method": method,
        })

    def log_bands(
        self,
        timestamp: float,
        device_id: str,
        band_powers: dict[str, float],
    ) -> None:
        """Record frequency band powers.

        Parameters
        ----------
        timestamp : float
            Unix timestamp.
        device_id : str
            Device identifier.
        band_powers : dict[str, float]
            Mapping band name → mean power.
        """
        record = {
            "timestamp": timestamp,
            "device_id": device_id,
        }
        record.update(band_powers)
        self._band_records.append(record)

    def export(self, fmt: str = "both") -> Path:
        """Export session data to disk.

        Parameters
        ----------
        fmt : str
            Export format: ``"csv"``, ``"xdf"``, or ``"both"``.
            XDF export is a reminder — actual XDF capture is via
            LabRecorder. This method exports CSV metrics.

        Returns
        -------
        Path
            Session output directory.
        """
        if not self._session_start:
            self._session_start = datetime.now(timezone.utc)

        session_id = self._session_start.strftime("ses-%Y%m%dT%H%M%S")
        session_dir = self._output_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Export alpha metrics CSV
        if self._alpha_records:
            alpha_df = pd.DataFrame(self._alpha_records)
            alpha_path = session_dir / "neuropalite_alpha-metrics.csv"
            alpha_df.to_csv(alpha_path, index=False, float_format="%.6f")
            logger.info("Alpha metrics exported: %s (%d rows)", alpha_path, len(alpha_df))

        # Export band powers CSV
        if self._band_records:
            bands_df = pd.DataFrame(self._band_records)
            bands_path = session_dir / "neuropalite_band-powers.csv"
            bands_df.to_csv(bands_path, index=False, float_format="%.6f")
            logger.info("Band powers exported: %s (%d rows)", bands_path, len(bands_df))

        # Export session info JSON
        session_info = {
            "session_start": self._session_start.isoformat(),
            "session_end": datetime.now(timezone.utc).isoformat(),
            "n_alpha_records": len(self._alpha_records),
            "n_band_records": len(self._band_records),
            "devices": self._device_ids,
            "band_names": self._band_names,
            "normalization_default": self._proc_cfg["normalization"]["default_method"],
            "sampling_rate": self._muse_cfg["acquisition"]["sampling_rate"],
            "channels": self._muse_cfg["acquisition"]["channels"],
            "software": "Neuropalite v0.1.0",
        }
        info_path = session_dir / "neuropalite_session-info.json"
        with open(info_path, "w") as f:
            json.dump(session_info, f, indent=2)
        logger.info("Session info exported: %s", info_path)

        return session_dir

    @property
    def n_records(self) -> int:
        """Total number of recorded observations."""
        return len(self._alpha_records) + len(self._band_records)
