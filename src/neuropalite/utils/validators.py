"""YAML configuration validation for Neuropalite.

Validates ``muse_config.yaml`` and ``processing_config.yaml`` at startup to fail
fast on missing or malformed parameters.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = PROJECT_ROOT / "config"


def load_yaml(filename: str) -> dict[str, Any]:
    """Load and return a YAML config file from ``config/``.

    Parameters
    ----------
    filename : str
        Name of the YAML file (e.g. ``"muse_config.yaml"``).

    Returns
    -------
    dict[str, Any]
        Parsed YAML contents.

    Raises
    ------
    FileNotFoundError
        If the config file does not exist.
    yaml.YAMLError
        If the file is not valid YAML.
    """
    path = CONFIG_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    logger.info("Loaded config: %s", path)
    return data


def validate_muse_config(config: dict[str, Any]) -> None:
    """Validate muse_config.yaml structure and required fields.

    Parameters
    ----------
    config : dict[str, Any]
        Parsed YAML from ``muse_config.yaml``.

    Raises
    ------
    ValueError
        If required fields are missing or invalid.
    """
    _require_keys(config, ["muse_devices", "acquisition"], context="muse_config")

    devices = config["muse_devices"]
    if not isinstance(devices, dict) or len(devices) == 0:
        raise ValueError("muse_config: muse_devices must contain at least one device")

    for name, device in devices.items():
        _require_keys(
            device,
            ["name", "bluetooth_address", "enabled"],
            context=f"muse_devices.{name}",
        )

    acq = config["acquisition"]
    _require_keys(
        acq,
        ["sampling_rate", "channels", "buffer_duration"],
        context="acquisition",
    )

    if acq["sampling_rate"] <= 0:
        raise ValueError("acquisition.sampling_rate must be positive")

    logger.info("Muse config validated OK")


def validate_processing_config(config: dict[str, Any]) -> None:
    """Validate processing_config.yaml structure and required fields.

    Parameters
    ----------
    config : dict[str, Any]
        Parsed YAML from ``processing_config.yaml``.

    Raises
    ------
    ValueError
        If required fields are missing or invalid.
    """
    _require_keys(
        config,
        ["filtering", "psd", "frequency_bands", "normalization", "streaming"],
        context="processing_config",
    )

    # Filtering
    filt = config["filtering"]
    _require_keys(filt, ["bandpass", "notch"], context="filtering")
    bp = filt["bandpass"]
    if bp["low_freq"] >= bp["high_freq"]:
        raise ValueError("filtering.bandpass: low_freq must be < high_freq")

    # Frequency bands — check ordering
    bands = config["frequency_bands"]
    expected_bands = ["delta", "theta", "alpha", "beta", "gamma"]
    for band_name in expected_bands:
        if band_name not in bands:
            raise ValueError(f"frequency_bands: missing band '{band_name}'")
        band = bands[band_name]
        _require_keys(band, ["fmin", "fmax"], context=f"frequency_bands.{band_name}")
        if band["fmin"] >= band["fmax"]:
            raise ValueError(f"frequency_bands.{band_name}: fmin must be < fmax")

    logger.info("Processing config validated OK")


def _require_keys(
    d: dict[str, Any], keys: list[str], context: str = ""
) -> None:
    """Check that all required keys are present in a dict."""
    for key in keys:
        if key not in d:
            raise ValueError(f"{context}: missing required key '{key}'")
