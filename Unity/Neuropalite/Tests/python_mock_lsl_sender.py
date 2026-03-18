"""
Mock LSL sender for Neuropalite testing.

Sends two streams (AlphaPower_P1, AlphaPower_P2) with synthetic alpha power
values, simulating natural alpha fluctuations (~0.1 Hz envelope).

Requirements:
    pip install pylsl numpy

Usage:
    python Tests/python_mock_lsl_sender.py
    # Ctrl+C to stop

Reference:
    Alpha power typically ranges 0.0–1.0 (normalized).
    Slow sinusoidal modulation simulates natural alpha fluctuations
    observed in resting-state and neurofeedback paradigms.

    Klimesch, W. (1999). EEG alpha and theta oscillations reflect
    cognitive and memory performance. Brain Research Reviews, 29(2-3), 169-195.
"""

import time
import numpy as np
from pylsl import StreamInfo, StreamOutlet


def create_outlet(name: str, source_id: str) -> StreamOutlet:
    """Create an LSL outlet for a single-channel alpha power stream.

    Parameters
    ----------
    name : str
        Stream name (e.g., "AlphaPower_P1").
    source_id : str
        Unique source identifier.

    Returns
    -------
    StreamOutlet
        The LSL outlet ready to push samples.
    """
    info = StreamInfo(
        name=name,
        type="EEG",
        channel_count=1,
        nominal_srate=10.0,
        channel_format="float32",
        source_id=source_id,
    )
    return StreamOutlet(info)


def generate_alpha(t: float, freq: float, phase: float) -> float:
    """Generate a synthetic alpha power value.

    Combines a slow sinusoidal envelope with Gaussian noise
    to simulate natural alpha power fluctuations.

    Parameters
    ----------
    t : float
        Current time in seconds.
    freq : float
        Modulation frequency in Hz (typically ~0.1 Hz).
    phase : float
        Phase offset in radians (to differentiate participants).

    Returns
    -------
    float
        Alpha power value clamped to [0, 1].
    """
    value = 0.5 + 0.3 * np.sin(2 * np.pi * freq * t + phase) + 0.05 * np.random.randn()
    return float(np.clip(value, 0.0, 1.0))


def main() -> None:
    """Run the mock LSL sender with two alpha power streams."""
    outlet_p1 = create_outlet("AlphaPower_P1", "mock_p1")
    outlet_p2 = create_outlet("AlphaPower_P2", "mock_p2")

    print("=" * 50)
    print("  Neuropalite Mock LSL Sender")
    print("=" * 50)
    print(f"  Stream 1: AlphaPower_P1 (10 Hz, 1 channel)")
    print(f"  Stream 2: AlphaPower_P2 (10 Hz, 1 channel)")
    print(f"  Press Ctrl+C to stop")
    print("=" * 50)

    t = 0.0
    dt = 1.0 / 10.0  # 10 Hz update rate

    try:
        while True:
            alpha_p1 = generate_alpha(t, freq=0.10, phase=0.0)
            alpha_p2 = generate_alpha(t, freq=0.08, phase=1.0)

            outlet_p1.push_sample([alpha_p1])
            outlet_p2.push_sample([alpha_p2])

            if int(t * 10) % 20 == 0:  # Log every 2 seconds
                print(f"  t={t:6.1f}s  |  P1={alpha_p1:.3f}  |  P2={alpha_p2:.3f}")

            t += dt
            time.sleep(dt)
    except KeyboardInterrupt:
        print("\n  Stopped.")


if __name__ == "__main__":
    main()
