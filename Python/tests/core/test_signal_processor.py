"""Tests for the signal processing pipeline.

Uses synthetic signals with known frequency content to verify that
filtering, PSD estimation, and band extraction work correctly.
"""

import numpy as np
import pytest

from neuropalite.core.signal_processor import SignalProcessor

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SFREQ = 256.0  # Hz — Muse S sampling rate
DURATION = 10.0  # seconds of synthetic data
N_CHANNELS = 4
N_SAMPLES = int(SFREQ * DURATION)


@pytest.fixture
def proc_config() -> dict:
    """Minimal processing config for tests."""
    return {
        "filtering": {
            "bandpass": {"low_freq": 0.5, "high_freq": 50.0, "order": 4},
            "notch": {"freq": 60.0, "quality_factor": 30.0},
        },
        "psd": {
            "method": "welch",
            "window_duration": 4.0,
            "overlap_fraction": 0.5,
            "nfft": 1024,
        },
        "frequency_bands": {
            "delta": {"fmin": 0.5, "fmax": 4.0},
            "theta": {"fmin": 4.0, "fmax": 8.0},
            "alpha": {"fmin": 8.0, "fmax": 13.0},
            "beta": {"fmin": 13.0, "fmax": 30.0},
            "gamma": {"fmin": 30.0, "fmax": 50.0},
        },
    }


@pytest.fixture
def processor(proc_config) -> SignalProcessor:
    return SignalProcessor(proc_config)


def make_sine(freq: float, sfreq: float = SFREQ, duration: float = DURATION) -> np.ndarray:
    """Generate a pure sine wave at a given frequency."""
    t = np.arange(int(sfreq * duration)) / sfreq
    return np.sin(2 * np.pi * freq * t)


# ---------------------------------------------------------------------------
# Bandpass filter tests
# ---------------------------------------------------------------------------


class TestBandpassFilter:
    """Verify bandpass filter passes in-band and attenuates out-of-band."""

    def test_passes_alpha_signal(self, processor):
        """A 10 Hz sine (alpha band) should survive bandpass filtering."""
        alpha_signal = make_sine(10.0)
        data = np.tile(alpha_signal, (N_CHANNELS, 1))

        filtered = processor.apply_filters(data, SFREQ)

        # Signal power should be largely preserved
        input_power = np.mean(data ** 2)
        output_power = np.mean(filtered ** 2)
        assert output_power / input_power > 0.8, "Alpha signal should pass through"

    def test_attenuates_dc(self, processor):
        """DC offset (0 Hz) should be removed by the highpass at 0.5 Hz."""
        dc_signal = np.ones((N_CHANNELS, N_SAMPLES)) * 5.0
        filtered = processor.apply_filters(dc_signal, SFREQ)

        assert np.abs(np.mean(filtered)) < 0.1, "DC should be attenuated"

    def test_attenuates_high_frequency(self, processor):
        """100 Hz signal should be attenuated by the 50 Hz lowpass."""
        hf_signal = make_sine(100.0)
        data = np.tile(hf_signal, (N_CHANNELS, 1))

        filtered = processor.apply_filters(data, SFREQ)
        output_power = np.mean(filtered ** 2)

        assert output_power < 0.01, "100 Hz should be heavily attenuated"


# ---------------------------------------------------------------------------
# PSD tests
# ---------------------------------------------------------------------------


class TestPSD:
    """Verify Welch PSD estimation produces expected frequency peaks."""

    def test_psd_shape(self, processor):
        """PSD output should have correct shape."""
        data = np.random.randn(N_CHANNELS, N_SAMPLES)
        freqs, psd = processor.compute_psd(data, SFREQ)

        assert freqs.ndim == 1
        assert psd.shape[0] == N_CHANNELS
        assert psd.shape[1] == len(freqs)

    def test_peak_at_injected_frequency(self, processor):
        """PSD should show a clear peak at the frequency of a sine wave."""
        freq_inject = 10.0  # alpha band
        signal = make_sine(freq_inject)
        data = np.tile(signal, (N_CHANNELS, 1))

        # Filter first (as in real pipeline)
        filtered = processor.apply_filters(data, SFREQ)
        freqs, psd = processor.compute_psd(filtered, SFREQ)

        # Find peak frequency for channel 0
        peak_idx = np.argmax(psd[0])
        peak_freq = freqs[peak_idx]

        assert abs(peak_freq - freq_inject) < 1.0, (
            f"PSD peak at {peak_freq:.1f} Hz, expected ~{freq_inject} Hz"
        )


# ---------------------------------------------------------------------------
# Band extraction tests
# ---------------------------------------------------------------------------


class TestBandExtraction:
    """Verify frequency band power extraction."""

    def test_alpha_dominant_for_10hz(self, processor):
        """A 10 Hz signal should produce dominant alpha band power."""
        signal = make_sine(10.0)
        data = np.tile(signal, (N_CHANNELS, 1))

        result = processor.process(data, SFREQ)
        rel = result["relative_bands"]

        # Alpha should be the dominant band
        alpha_mean = np.mean(rel["alpha"])
        for band_name in ["delta", "theta", "beta", "gamma"]:
            other_mean = np.mean(rel[band_name])
            assert alpha_mean > other_mean, (
                f"Alpha ({alpha_mean:.3f}) should dominate over {band_name} ({other_mean:.3f})"
            )

    def test_relative_bands_sum_to_one(self, processor):
        """Relative band powers should approximately sum to 1.0."""
        data = np.random.randn(N_CHANNELS, N_SAMPLES) * 10
        result = processor.process(data, SFREQ)
        rel = result["relative_bands"]

        total = sum(np.mean(v) for v in rel.values())
        assert abs(total - 1.0) < 0.05, f"Relative powers sum to {total:.3f}, expected ~1.0"

    def test_all_five_bands_present(self, processor):
        """All 5 canonical bands should be in the output."""
        data = np.random.randn(N_CHANNELS, N_SAMPLES)
        result = processor.process(data, SFREQ)

        expected = {"delta", "theta", "alpha", "beta", "gamma"}
        assert set(result["absolute_bands"].keys()) == expected
        assert set(result["relative_bands"].keys()) == expected
