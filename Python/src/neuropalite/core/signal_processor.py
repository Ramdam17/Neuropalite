"""Real-time signal processing pipeline for Muse EEG data.

Applies bandpass filtering, notch filtering, Welch PSD estimation,
and frequency band power extraction. All operations work on numpy arrays
from the CircularBuffer, with no internal state.

Filter design
-------------
- Butterworth IIR filters in second-order sections (SOS) form for
  numerical stability (Smith, 2007).
- ``sosfiltfilt`` for zero-phase filtering (offline/buffered use).
- ``sosfilt`` available for causal real-time filtering if needed.

PSD estimation
--------------
- Welch's method with 4 s Hanning windows and 50 % overlap
  (Welch, 1967). Parameters configurable via ``processing_config.yaml``.

References
----------
- Welch, P. D. (1967). The use of fast Fourier transform for the
  estimation of power spectra. IEEE Trans. Audio Electroacoust.
- Smith, S. W. (2007). The Scientist and Engineer's Guide to Digital
  Signal Processing, Ch. 20 (Butterworth filter stability).
"""

import logging
from typing import Any

import numpy as np
from scipy import signal as sig

logger = logging.getLogger(__name__)


class SignalProcessor:
    """Stateless EEG signal processing pipeline.

    Reads filter and PSD parameters from the processing config dict,
    pre-computes filter coefficients, and exposes methods for each
    processing step.

    Parameters
    ----------
    processing_config : dict
        Parsed ``processing_config.yaml`` content.

    Example
    -------
    >>> proc = SignalProcessor(processing_config)
    >>> filtered = proc.apply_filters(raw_data, sfreq=256)
    >>> freqs, psd = proc.compute_psd(filtered, sfreq=256)
    >>> bands = proc.extract_bands(freqs, psd)
    """

    def __init__(self, processing_config: dict[str, Any]) -> None:
        filt_cfg = processing_config["filtering"]
        psd_cfg = processing_config["psd"]
        self.band_defs = processing_config["frequency_bands"]

        # Bandpass parameters
        bp = filt_cfg["bandpass"]
        self._bp_low = bp["low_freq"]
        self._bp_high = bp["high_freq"]
        self._bp_order = bp["order"]

        # Notch parameters
        notch = filt_cfg["notch"]
        self._notch_freq = notch["freq"]
        self._notch_q = notch["quality_factor"]

        # PSD parameters
        self._psd_window_sec = psd_cfg["window_duration"]
        self._psd_overlap_frac = psd_cfg["overlap_fraction"]
        self._nfft = psd_cfg["nfft"]

        logger.info(
            "SignalProcessor initialized: BP=%.1f–%.1f Hz (order %d), "
            "Notch=%.0f Hz (Q=%.0f), PSD window=%.1fs",
            self._bp_low,
            self._bp_high,
            self._bp_order,
            self._notch_freq,
            self._notch_q,
            self._psd_window_sec,
        )

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def apply_filters(
        self, data: np.ndarray, sfreq: float
    ) -> np.ndarray:
        """Apply bandpass + notch filters to EEG data.

        Parameters
        ----------
        data : np.ndarray
            EEG data, shape ``(n_channels, n_samples)``.
        sfreq : float
            Sampling frequency in Hz.

        Returns
        -------
        np.ndarray
            Filtered data, same shape as input.
        """
        filtered = self._bandpass(data, sfreq)
        filtered = self._notch(filtered, sfreq)
        return filtered

    def _bandpass(self, data: np.ndarray, sfreq: float) -> np.ndarray:
        """Apply zero-phase Butterworth bandpass filter.

        Uses SOS representation for numerical stability.
        """
        nyq = sfreq / 2.0
        low = self._bp_low / nyq
        high = self._bp_high / nyq
        sos = sig.butter(self._bp_order, [low, high], btype="band", output="sos")
        return sig.sosfiltfilt(sos, data, axis=-1)

    def _notch(self, data: np.ndarray, sfreq: float) -> np.ndarray:
        """Apply notch (band-stop) filter at power line frequency.

        Uses ``iirnotch`` for a narrow rejection band.
        """
        b, a = sig.iirnotch(self._notch_freq, self._notch_q, fs=sfreq)
        return sig.filtfilt(b, a, data, axis=-1)

    # ------------------------------------------------------------------
    # PSD estimation
    # ------------------------------------------------------------------

    def compute_psd(
        self, data: np.ndarray, sfreq: float
    ) -> tuple[np.ndarray, np.ndarray]:
        """Compute power spectral density using Welch's method.

        Parameters
        ----------
        data : np.ndarray
            Filtered EEG data, shape ``(n_channels, n_samples)``.
        sfreq : float
            Sampling frequency in Hz.

        Returns
        -------
        freqs : np.ndarray
            Frequency vector in Hz, shape ``(n_freqs,)``.
        psd : np.ndarray
            Power spectral density in µV²/Hz, shape ``(n_channels, n_freqs)``.
        """
        nperseg = int(self._psd_window_sec * sfreq)
        noverlap = int(nperseg * self._psd_overlap_frac)

        freqs, psd = sig.welch(
            data,
            fs=sfreq,
            window="hann",
            nperseg=nperseg,
            noverlap=noverlap,
            nfft=self._nfft,
            axis=-1,
        )
        return freqs, psd

    # ------------------------------------------------------------------
    # Band power extraction
    # ------------------------------------------------------------------

    def extract_bands(
        self, freqs: np.ndarray, psd: np.ndarray
    ) -> dict[str, np.ndarray]:
        """Extract average power in each canonical frequency band.

        Integrates PSD over each band's frequency range using the
        trapezoidal rule (``np.trapezoid``).

        Parameters
        ----------
        freqs : np.ndarray
            Frequency vector from ``compute_psd``, shape ``(n_freqs,)``.
        psd : np.ndarray
            PSD array, shape ``(n_channels, n_freqs)``.

        Returns
        -------
        dict[str, np.ndarray]
            Mapping band name → absolute power per channel,
            shape ``(n_channels,)``.

        Example
        -------
        >>> bands = proc.extract_bands(freqs, psd)
        >>> bands["alpha"]  # array([0.42, 0.38, 0.45, 0.41])
        """
        band_powers = {}
        for band_name, band_range in self.band_defs.items():
            fmin = band_range["fmin"]
            fmax = band_range["fmax"]
            mask = (freqs >= fmin) & (freqs <= fmax)

            if not np.any(mask):
                band_powers[band_name] = np.zeros(psd.shape[0])
                continue

            # Trapezoidal integration over the band
            band_powers[band_name] = np.trapezoid(psd[:, mask], freqs[mask], axis=-1)

        return band_powers

    def extract_relative_band_powers(
        self, freqs: np.ndarray, psd: np.ndarray
    ) -> dict[str, np.ndarray]:
        """Extract relative power (fraction of total) for each band.

        Parameters
        ----------
        freqs : np.ndarray
            Frequency vector.
        psd : np.ndarray
            PSD array, shape ``(n_channels, n_freqs)``.

        Returns
        -------
        dict[str, np.ndarray]
            Mapping band name → relative power per channel (sums to ~1.0).
        """
        abs_powers = self.extract_bands(freqs, psd)
        total = sum(abs_powers.values())
        # Avoid division by zero
        total = np.where(total > 0, total, 1.0)

        return {name: power / total for name, power in abs_powers.items()}

    # ------------------------------------------------------------------
    # Convenience: full pipeline
    # ------------------------------------------------------------------

    def process(
        self, data: np.ndarray, sfreq: float
    ) -> dict[str, Any]:
        """Run the full DSP pipeline on a data chunk.

        Parameters
        ----------
        data : np.ndarray
            Raw EEG data, shape ``(n_channels, n_samples)``.
        sfreq : float
            Sampling frequency in Hz.

        Returns
        -------
        dict[str, Any]
            Keys: ``"filtered"``, ``"freqs"``, ``"psd"``,
            ``"absolute_bands"``, ``"relative_bands"``.
        """
        filtered = self.apply_filters(data, sfreq)
        freqs, psd = self.compute_psd(filtered, sfreq)
        abs_bands = self.extract_bands(freqs, psd)
        rel_bands = self.extract_relative_band_powers(freqs, psd)

        return {
            "filtered": filtered,
            "freqs": freqs,
            "psd": psd,
            "absolute_bands": abs_bands,
            "relative_bands": rel_bands,
        }
