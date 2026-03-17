"""Tests for the LSL streamer module.

Tests outlet creation and push methods. Since pylsl outlets require
a running LSL layer, these tests verify the API surface and configuration
rather than end-to-end streaming (which requires LabRecorder or a real inlet).
"""

import pytest

from neuropalite.core.lsl_streamer import LSLOutlet, LSLStreamer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def muse_config() -> dict:
    return {
        "muse_devices": {
            "muse_1": {"name": "A", "bluetooth_address": "00:00:00:00:00:01", "enabled": True},
            "muse_2": {"name": "B", "bluetooth_address": "00:00:00:00:00:02", "enabled": True},
        },
        "acquisition": {
            "sampling_rate": 256,
            "channels": ["TP9", "AF7", "AF8", "TP10"],
            "buffer_duration": 10,
        },
    }


@pytest.fixture
def processing_config() -> dict:
    return {
        "filtering": {
            "bandpass": {"low_freq": 0.5, "high_freq": 50.0, "order": 4},
            "notch": {"freq": 60.0, "quality_factor": 30.0},
        },
        "psd": {"method": "welch", "window_duration": 4.0, "overlap_fraction": 0.5, "nfft": 1024},
        "frequency_bands": {
            "delta": {"fmin": 0.5, "fmax": 4.0},
            "theta": {"fmin": 4.0, "fmax": 8.0},
            "alpha": {"fmin": 8.0, "fmax": 13.0},
            "beta": {"fmin": 13.0, "fmax": 30.0},
            "gamma": {"fmin": 30.0, "fmax": 50.0},
        },
        "normalization": {
            "default_method": "minmax",
            "minmax": {"window_duration": 60.0},
            "zscore": {"window_duration": 60.0, "temperature": 1.0},
            "baseline": {"scaling_factor": 2.0},
            "percentile": {"window_duration": 120.0, "smoothing": 0.1},
        },
        "streaming": {"lsl_update_rate": 10, "websocket_update_rate": 30},
    }


# ---------------------------------------------------------------------------
# LSLOutlet tests
# ---------------------------------------------------------------------------


class TestLSLOutlet:
    """Test individual LSL outlet creation and push."""

    def test_create_outlet(self):
        """Outlet should be created without error."""
        outlet = LSLOutlet(
            name="test_outlet",
            stream_type="EEG",
            n_channels=4,
            srate=256.0,
            channel_names=["TP9", "AF7", "AF8", "TP10"],
        )
        assert outlet.name == "test_outlet"

    def test_push_sample(self):
        """Pushing a sample should not raise."""
        outlet = LSLOutlet(
            name="test_push",
            stream_type="EEG",
            n_channels=4,
            srate=256.0,
        )
        outlet.push([1.0, 2.0, 3.0, 4.0])

    def test_push_chunk(self):
        """Pushing a chunk should not raise."""
        outlet = LSLOutlet(
            name="test_chunk",
            stream_type="EEG",
            n_channels=2,
            srate=10.0,
        )
        outlet.push_chunk([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])


# ---------------------------------------------------------------------------
# LSLStreamer tests
# ---------------------------------------------------------------------------


class TestLSLStreamer:
    """Test the multi-outlet streamer setup and push methods."""

    def test_setup_creates_outlets(self, muse_config, processing_config):
        """Setup should create raw, band, and alpha outlets."""
        streamer = LSLStreamer(muse_config, processing_config)
        streamer.setup(["muse_1", "muse_2"])

        assert "muse_1" in streamer.raw_outlets
        assert "muse_2" in streamer.raw_outlets
        assert "muse_1" in streamer.band_outlets
        assert "muse_2" in streamer.band_outlets
        assert streamer.alpha_outlet is not None

    def test_push_bands(self, muse_config, processing_config):
        """Pushing band powers should not raise."""
        streamer = LSLStreamer(muse_config, processing_config)
        streamer.setup(["muse_1"])

        streamer.push_bands("muse_1", {
            "delta": 0.1, "theta": 0.2, "alpha": 0.4, "beta": 0.2, "gamma": 0.1,
        })

    def test_push_alpha_metrics(self, muse_config, processing_config):
        """Pushing alpha metrics should not raise."""
        streamer = LSLStreamer(muse_config, processing_config)
        streamer.setup(["muse_1", "muse_2"])

        streamer.push_alpha_metrics({"muse_1": 0.75, "muse_2": 0.62})

    def test_get_status(self, muse_config, processing_config):
        """Status should report correct outlet count."""
        streamer = LSLStreamer(muse_config, processing_config)
        streamer.setup(["muse_1", "muse_2"])

        status = streamer.get_status()
        # 2 raw + 2 band + 1 alpha = 5
        assert status["active_outlets"] == 5
        assert status["update_rate_hz"] == 10
        assert status["streaming"] is True

    def test_push_to_unknown_device(self, muse_config, processing_config):
        """Pushing to a non-existent device should be a no-op."""
        streamer = LSLStreamer(muse_config, processing_config)
        streamer.setup(["muse_1"])

        # Should not raise
        streamer.push_bands("muse_99", {"alpha": 0.5})
        streamer.push_raw("muse_99", [1.0, 2.0, 3.0, 4.0])
