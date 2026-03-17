"""Thread-safe circular buffer for real-time EEG data.

Stores a rolling window of EEG samples in a pre-allocated numpy array,
enabling zero-copy reads for downstream processing (PSD, filtering, etc.).

Design choice: numpy array + modulo index rather than collections.deque,
because at 256 Hz x 4 channels we need to avoid per-sample Python allocations
and allow direct slicing for scipy/MNE operations.
"""

import logging
import threading

import numpy as np

logger = logging.getLogger(__name__)


class CircularBuffer:
    """Fixed-size circular buffer backed by a numpy array.

    Parameters
    ----------
    n_channels : int
        Number of EEG channels (e.g. 4 for Muse S).
    buffer_duration : float
        Duration of the rolling window in seconds.
    sampling_rate : float
        Sampling rate in Hz.

    Example
    -------
    >>> buf = CircularBuffer(n_channels=4, buffer_duration=10.0, sampling_rate=256.0)
    >>> buf.push(np.random.randn(4))       # single sample
    >>> buf.push_chunk(np.random.randn(4, 32))  # 32 samples
    >>> data = buf.get_data()              # shape (4, 2560) or less if not full
    """

    def __init__(
        self,
        n_channels: int,
        buffer_duration: float,
        sampling_rate: float,
    ) -> None:
        self.n_channels = n_channels
        self.sampling_rate = sampling_rate
        self.max_samples = int(buffer_duration * sampling_rate)

        self._buffer = np.zeros((n_channels, self.max_samples), dtype=np.float64)
        self._write_idx = 0
        self._count = 0  # how many samples have been written total
        self._lock = threading.Lock()

        logger.info(
            "CircularBuffer created: %d ch × %d samples (%.1fs @ %.0f Hz)",
            n_channels,
            self.max_samples,
            buffer_duration,
            sampling_rate,
        )

    def push(self, sample: np.ndarray) -> None:
        """Push a single sample into the buffer.

        Parameters
        ----------
        sample : np.ndarray
            Shape ``(n_channels,)``.
        """
        with self._lock:
            idx = self._write_idx % self.max_samples
            self._buffer[:, idx] = sample
            self._write_idx += 1
            self._count = min(self._count + 1, self.max_samples)

    def push_chunk(self, chunk: np.ndarray) -> None:
        """Push multiple samples at once.

        Parameters
        ----------
        chunk : np.ndarray
            Shape ``(n_channels, n_samples)``.
        """
        n_samples = chunk.shape[1]
        with self._lock:
            for i in range(n_samples):
                idx = self._write_idx % self.max_samples
                self._buffer[:, idx] = chunk[:, i]
                self._write_idx += 1
            self._count = min(self._count + n_samples, self.max_samples)

    def get_data(self) -> np.ndarray:
        """Return the current buffer contents in chronological order.

        Returns
        -------
        np.ndarray
            Shape ``(n_channels, n_valid_samples)`` where ``n_valid_samples``
            is ``min(total_pushed, max_samples)``.
        """
        with self._lock:
            if self._count < self.max_samples:
                return self._buffer[:, : self._count].copy()

            # Buffer is full — reorder so oldest sample is first
            idx = self._write_idx % self.max_samples
            return np.concatenate(
                [self._buffer[:, idx:], self._buffer[:, :idx]], axis=1
            ).copy()

    def get_last_n_seconds(self, duration: float) -> np.ndarray:
        """Return the last *duration* seconds of data.

        Parameters
        ----------
        duration : float
            How many seconds of recent data to return.

        Returns
        -------
        np.ndarray
            Shape ``(n_channels, n_samples)`` — may be shorter if the buffer
            doesn't contain enough data yet.
        """
        n_requested = int(duration * self.sampling_rate)
        data = self.get_data()
        n_available = data.shape[1]
        n_return = min(n_requested, n_available)
        return data[:, -n_return:]

    @property
    def is_full(self) -> bool:
        """Whether the buffer has been completely filled at least once."""
        with self._lock:
            return self._count >= self.max_samples

    @property
    def n_samples(self) -> int:
        """Number of valid samples currently in the buffer."""
        with self._lock:
            return self._count

    def reset(self) -> None:
        """Clear the buffer."""
        with self._lock:
            self._buffer[:] = 0.0
            self._write_idx = 0
            self._count = 0
            logger.info("CircularBuffer reset")
