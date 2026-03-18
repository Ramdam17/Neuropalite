"""Tests for the CircularBuffer module."""

import numpy as np
import pytest

from neuropalite.core.data_buffer import CircularBuffer


@pytest.fixture
def buffer():
    """Create a small test buffer: 4 channels, 2 seconds @ 256 Hz."""
    return CircularBuffer(n_channels=4, buffer_duration=2.0, sampling_rate=256.0)


class TestCircularBuffer:

    def test_push_single_sample(self, buffer):
        sample = np.array([1.0, 2.0, 3.0, 4.0])
        buffer.push(sample)
        assert buffer.n_samples == 1
        data = buffer.get_data()
        assert data.shape == (4, 1)
        np.testing.assert_array_equal(data[:, 0], sample)

    def test_push_chunk(self, buffer):
        chunk = np.random.randn(4, 64)
        buffer.push_chunk(chunk)
        assert buffer.n_samples == 64
        data = buffer.get_data()
        np.testing.assert_array_almost_equal(data, chunk)

    def test_circular_overwrite(self, buffer):
        """When buffer is full, oldest data should be overwritten."""
        max_samples = buffer.max_samples  # 512

        # Fill completely
        full_chunk = np.random.randn(4, max_samples)
        buffer.push_chunk(full_chunk)
        assert buffer.is_full

        # Push 10 more samples — should overwrite oldest 10
        extra = np.ones((4, 10)) * 99.0
        buffer.push_chunk(extra)

        data = buffer.get_data()
        assert data.shape == (4, max_samples)
        # Last 10 samples should be the extra data
        np.testing.assert_array_almost_equal(data[:, -10:], extra)

    def test_get_last_n_seconds(self, buffer):
        chunk = np.random.randn(4, 256)  # 1 second of data
        buffer.push_chunk(chunk)

        # Request 0.5 seconds = 128 samples
        result = buffer.get_last_n_seconds(0.5)
        assert result.shape == (4, 128)
        np.testing.assert_array_almost_equal(result, chunk[:, -128:])

    def test_get_last_n_seconds_more_than_available(self, buffer):
        chunk = np.random.randn(4, 64)
        buffer.push_chunk(chunk)

        # Request 5 seconds but only ~0.25s available
        result = buffer.get_last_n_seconds(5.0)
        assert result.shape == (4, 64)

    def test_reset(self, buffer):
        buffer.push_chunk(np.random.randn(4, 100))
        buffer.reset()
        assert buffer.n_samples == 0
        assert not buffer.is_full

    def test_is_full(self, buffer):
        assert not buffer.is_full
        buffer.push_chunk(np.random.randn(4, buffer.max_samples))
        assert buffer.is_full
