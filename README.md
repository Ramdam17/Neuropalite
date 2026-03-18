# Neuropalite

![Neuropalite](Unity/Neuropalite/Assets/Art/Textures/background.png)

A real-time **dyadic neurofeedback** system built for science outreach. Two participants wear Muse S EEG headsets, and their alpha power (8–12 Hz) drives two dancing characters in a Unity nightclub scene — set to Taylor Swift's *Opalite* (BPM 125).

When alpha is low, the characters look sad and idle. As alpha rises, they dance with increasing energy. When both participants synchronize — high alpha and close together — center-stage fireworks explode.

The project has two components:
- **`Python/`** — BLE acquisition (Muse S via bleak), real-time signal processing, LSL streaming, and a web dashboard
- **`Unity/Neuropalite/`** — 3D visualization app that receives alpha power via LSL and animates the scene

---

## Architecture

```
┌──────────────┐     BLE GATT      ┌──────────────────────────────────┐
│   Muse S #1  │ ──────────────▶   │                                  │
└──────────────┘                   │     Python Backend               │
                                   │                                  │
┌──────────────┐     BLE GATT      │  MuseManager (bleak + bitstring) │
│   Muse S #2  │ ──────────────▶   │         ↓                        │
└──────────────┘                   │  CircularBuffer (10s @ 256 Hz)   │
                                   │         ↓                        │
                                   │  SignalProcessor (bandpass,      │
                                   │    notch, Welch PSD)             │
                                   │         ↓                        │
                                   │  AlphaMetrics (normalize 0–1)    │
                                   │         ↓                        │
                                   │  ┌──────────┬──────────────┐     │
                                   │  │ LSL @10Hz│ WebSocket@30Hz│    │
                                   │  └────┬─────┴──────┬───────┘     │
                                   └───────┼────────────┼─────────────┘
                                           │            │
                              ┌────────────┘            └──────────┐
                              ▼                                    ▼
                    ┌──────────────────┐              ┌────────────────┐
                    │  Unity App (LSL) │              │  Web Dashboard  │
                    │  AlphaPower_P1   │              │  (Flask-SocketIO│
                    │  AlphaPower_P2   │              │   port 5555)    │
                    └──────────────────┘              └────────────────┘
```

---

## Python Backend

### Quick Start

```bash
cd Python

# Install dependencies (requires uv)
uv sync

# Scan for Muse devices
uv run python scripts/scan_muse.py

# Edit config with discovered addresses
# → config/muse_config.yaml

# Run the backend
uv run python run.py
```

The web dashboard is available at `http://localhost:5555`.

### BLE Acquisition

Connects directly to Muse S headsets via **bleak** (BLE GATT), bypassing muse-lsl entirely. Raw 12-bit EEG samples are parsed from BLE notifications using **bitstring** and converted to µV:

```
µV = 0.48828125 × (raw_12bit - 2048)
```

Each Muse device runs its own asyncio event loop in a daemon thread. The trigger channel (AF7) fires buffer pushes — 12 samples per BLE packet across 4 EEG channels (TP9, AF7, AF8, TP10).

### Signal Processing Pipeline

| Stage | Method | Parameters |
|-------|--------|------------|
| Bandpass | Butterworth SOS, order 4 | 0.5 – 50 Hz |
| Notch | IIR notch filter | 60 Hz, Q = 30 |
| PSD | Welch periodogram | 4s window, 50% overlap, nfft = 1024 |
| Band extraction | Trapezoidal integration | Delta, theta, alpha (8–12), beta, gamma |

### Alpha Normalization

Four methods available, switchable from the dashboard:

| Method | Description |
|--------|-------------|
| **Min-Max** | Tracks running min/max of raw alpha power |
| **Z-Score + Sigmoid** | Standardize then squash to 0–1 |
| **Baseline Calibration** | 30s eyes-closed baseline, then ratio |
| **Percentile Ranking** | Exponentially-smoothed percentile position |

### LSL Outlets

Two separate streams, one per participant:

| Stream Name | Type | Channels | Rate |
|-------------|------|----------|------|
| `AlphaPower_P1` | Alpha | 1 float (0–1) | 10 Hz |
| `AlphaPower_P2` | Alpha | 1 float (0–1) | 10 Hz |

### Data Logging

Session data exports in BIDS-inspired format under `Python/data/derivative/ses-<timestamp>/`:
- CSV files with alpha metrics and band powers per device
- JSON session metadata

### Python Project Structure

```
Python/
├── config/
│   ├── muse_config.yaml          # BLE addresses for each Muse headset
│   └── processing_config.yaml    # DSP parameters, streaming rates
├── src/neuropalite/
│   ├── core/
│   │   ├── muse_manager.py       # BLE connection + EEG parsing (bleak)
│   │   ├── data_buffer.py        # Thread-safe circular buffer (numpy)
│   │   ├── signal_processor.py   # Bandpass, notch, Welch PSD
│   │   ├── alpha_metrics.py      # 4 normalization methods
│   │   ├── lsl_streamer.py       # Per-device LSL outlets
│   │   ├── streaming_orchestrator.py  # Main processing loop (10/30 Hz)
│   │   └── data_logger.py        # BIDS-inspired session export
│   ├── web/
│   │   ├── app.py                # Flask + SocketIO (threading mode)
│   │   ├── routes.py             # Dashboard route
│   │   ├── websocket_handlers.py # Real-time UI events
│   │   ├── templates/            # Jinja2 dashboard templates
│   │   └── static/               # CSS (Opalite theme), JS
│   └── utils/                    # Logger, validators
├── scripts/
│   └── scan_muse.py              # BLE scan utility
├── tests/                        # pytest suite
├── run.py                        # Entry point
└── pyproject.toml                # uv/hatch project config
```

### Python Requirements

- **Python 3.12+**
- **uv** (package manager)
- Key dependencies: `bleak`, `bitstring`, `pylsl`, `numpy`, `scipy`, `flask-socketio`

---

## Unity Visualization

### Scenes

| Scene | Description |
|-------|-------------|
| **StartOpalite** | Landing screen with LSL connection status indicators and a Start button |
| **RunOpalite** | Main experience — music, dancing, lights, fireworks. Continues running when the window loses focus. Auto-returns to Start when the song ends |

### Alpha → Animation Mapping

Each participant's **dance** is driven by their own alpha independently:

| Alpha Range | Dance Tier |
|-------------|-----------|
| 0.0 – 0.3 | Idle |
| 0.3 – 0.5 | Low energy (Dance 1–2) |
| 0.5 – 0.7 | Medium energy (Dance 3–5) |
| 0.7 – 1.0 | High energy (Dance 6–7) |

Animations play to completion before switching tiers — no mid-clip cuts.

**Facial expressions** are driven by inter-brain sync (`1 - |α₁ - α₂|`), shared across both characters:

| Sync Range | Expression |
|------------|-----------|
| 0.0 – 0.3 | Sad (100% → 0%) |
| 0.3 – 0.8 | Happy (0% → 100%) |

When both participants are in sync, both characters smile simultaneously.

### Fireworks (VFX Graph)

The three VFX effects run continuously and are placed off-screen (Z = 10000) when inactive, then teleported to their scene position when conditions are met — eliminating VFX Graph warm-up latency entirely.

| Condition | Firework | Position |
|-----------|----------|----------|
| P1 alpha > P2 alpha | Left | (-15, 0, 20) |
| P2 alpha > P1 alpha | Right | (15, 0, 20) |
| Both > 0.5 | Center | (0, -5, 20) |

Left and right are mutually exclusive. Rocket frequency and explosion size scale with the magnitude of the alpha difference (sides) or average alpha (center).

### Nightclub Lights

Seven SpaceZeta spotlight models rotate in true circles over the stage. Each has a fixed color from a vibrant palette. Programmatically created Unity Spot Lights project colored light onto the floor. Emission pulses on the beat.

### Unity Project Structure

```
Unity/Neuropalite/
├── Assets/
│   ├── Scripts/
│   │   ├── LSL/                 # LSLManager, AlphaPowerReceiver, StreamStatus
│   │   ├── Animation/           # DanceAnimationController, AlphaAnimationDriver
│   │   ├── Audio/               # MusicController, BeatSync
│   │   ├── Effects/             # ClubLightController, FireworkController, SyncIndicator
│   │   └── UI/                  # StartSceneUI, StreamStatusIndicator
│   ├── Scenes/
│   │   ├── StartOpalite.unity
│   │   └── RunOpalite.unity
│   ├── Art/                     # Textures, shaders, materials, models
│   ├── Audio/Music/             # Opalite.mp3
│   ├── Animations/              # Mixamo dance clips + Animator Controllers
│   └── Settings/                # URP render pipeline assets
└── Tests/
    └── python_mock_lsl_sender.py
```

### Unity Requirements

- **Unity 6** (6000.x) with **Universal Render Pipeline 17.x**
- **VFX Graph** package (for fireworks)
- **LSL4Unity** (via UPM — see fix below for macOS)

### LSL4Unity Fix for Unity 6 + macOS (Apple Silicon)

> **This is critical.** LSL4Unity bundles liblsl 1.16.0 which fails to discover streams on Unity 6 + macOS Apple Silicon. Stream resolution returns 0 results even though streams are visible from Python.

#### Fix: Replace with liblsl 1.17+

1. **Get a newer liblsl** from pylsl (which bundles 1.17.4+):
   ```bash
   pip install pylsl
   PYLSL_LIB=$(python -c "import pylsl; print(pylsl.lib.__file__)")
   ```

2. **Extract the arm64 slice** (pylsl ships a universal binary):
   ```bash
   lipo "$PYLSL_LIB" -thin arm64 -output /tmp/liblsl_arm64.dylib
   ```

3. **Fix the install name** (Unity requires a specific rpath):
   ```bash
   install_name_tool -id "@rpath/liblsl.2.dylib" /tmp/liblsl_arm64.dylib
   ```

4. **Re-sign** (required on macOS):
   ```bash
   codesign --force --sign - /tmp/liblsl_arm64.dylib
   ```

5. **Copy to all 3 dylib files** in the LSL4Unity plugin folder:
   ```bash
   PLUGIN_DIR="Packages/com.labstreaminglayer.lsl4unity/Plugins/LSL/macOS/arm64"
   cp /tmp/liblsl_arm64.dylib "$PLUGIN_DIR/liblsl.2.1.0.dylib"
   cp /tmp/liblsl_arm64.dylib "$PLUGIN_DIR/liblsl.2.dylib"
   cp /tmp/liblsl_arm64.dylib "$PLUGIN_DIR/liblsl.dylib"
   ```

6. **Restart Unity** — streams should now be discovered.

---

## Testing Without EEG Hardware

### Mock LSL Sender

```bash
cd Unity/Neuropalite
pip install pylsl numpy
python Tests/python_mock_lsl_sender.py
```

Sends two sine-wave alpha streams at 10 Hz — useful for testing the Unity app without Muse headsets.

---

## Assets & Credits

### Music
- *Opalite* by **Taylor Swift** — used for research/educational purposes only. All rights belong to the artist.

### Unity Asset Store
| Asset | Author | Usage |
|-------|--------|-------|
| [Modular Stage](https://assetstore.unity.com/packages/3d/environments/modular-stage-326786) | — | Main stage environment |
| [Casual 1 Anime Girl Characters](https://assetstore.unity.com/packages/3d/characters/humanoids/casual-1-anime-girl-characters-185076) | — | The two dancing characters |
| [Spotlight and Structure](https://assetstore.unity.com/packages/3d/props/interior/spotlight-and-structure-141453) | SpaceZeta | Rotating disco spotlights |
| [Cool Visual Effects Part 1 (URP)](https://assetstore.unity.com/packages/vfx/particles/cool-visual-effects-part-1-urp-support-176571) | — | VFX Graph firework effects |
| [Stylized Rocks](https://assetstore.unity.com/packages/3d/environments/landscapes/stylized-rocks-free-demo-pack-355500) | — | Decorative rocks (Opalite clip reference) |
| [LowPoly Cactus Pack](https://assetstore.unity.com/packages/3d/vegetation/lowpoly-cactus-pack-291590) | — | Decorative cactus (Opalite clip reference) |
| [Fireworks](https://assetstore.unity.com/packages/3d/props/weapons/fireworks-101035) | — | 3D firework launcher models |

### Dance Animations
- Downloaded from [Mixamo](https://www.mixamo.com/) — 7 dance clips + 1 idle, configured as Humanoid.

### Custom Assets
- Disco ball FBX model
- Background texture and friendship bracelet artwork

---

## License

This project is developed for science outreach and education at CHU Sainte-Justine (PPSP Lab). The music and Asset Store packages are subject to their respective licenses.
