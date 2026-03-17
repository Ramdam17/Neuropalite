# 🧠 NEUROPALITE
## Interface Neurofeedback Dyadique
### Muse EEG • LSL Streaming • Unity Integration

---

**Design Inspiration:** Taylor Swift • Lover/Midnights Era  
**Document généré:** 17 Mars 2026

---

## 📑 Table des Matières

1. [Charte Graphique "Opalite - Neuropalite Edition"](#1-charte-graphique-opalite---neuropalite-edition)
2. [Architecture Système](#2-architecture-système)
3. [Structure des Fichiers](#3-structure-des-fichiers)
4. [Wireframes & Mockups Interface](#4-wireframes--mockups-interface)
5. [Plan de Développement - Sprints](#5-plan-de-développement---sprints)
6. [Diagrammes de Flux Détaillés](#6-diagrammes-de-flux-détaillés)
7. [Spécifications Techniques](#7-spécifications-techniques)
8. [Dependencies & Installation](#8-dependencies--installation)

---

## 1. Charte Graphique "Opalite - Neuropalite Edition"

Inspirée de l'univers visuel de Taylor Swift (ères **Lover** & **Midnights**) et de l'esthétique glitter/sparkle moderne, la charte Opalite fusionne technologie neuroscience et design émotionnel.

### 1.1 Palette de Couleurs

| Couleur | Code HEX | Usage |
|---------|----------|-------|
| **Turquoise Opalite** | `#00CED1` | Primaire - Titres, accents principaux |
| **Rose Corail** | `#FF6B9D` | Secondaire - Participant A, éléments chauds |
| **Orange Chaleureux** | `#FF8C42` | Accent - Participant B, highlights |
| **Blanc Cassé Azure** | `#F0F8FF` | Background cards, texte sur foncé |
| **Bleu Nuit Profond** | `#1A1A2E` | Background principal, texte dark mode |
| **Cyan Sparkle** | `#E0FFFF` | Effets scintillants, overlays |

**Gradients signature:**
```css
/* Fond principal */
background: radial-gradient(circle at 50% 50%, #00CED1 0%, #1A1A2E 100%);

/* Cards glassmorphism */
background: rgba(240, 248, 255, 0.1);
backdrop-filter: blur(10px);

/* Boutons actifs */
background: linear-gradient(135deg, #FF6B9D 0%, #FF8C42 100%);
```

### 1.2 Typographie

| Type | Font | Usage |
|------|------|-------|
| **Display** | Quicksand (Google Fonts) | Titres, headings, noms participants |
| **Body** | Outfit (Google Fonts) | Texte général, descriptions |
| **Monospace** | JetBrains Mono | Valeurs métriques, logs, code |

```css
@import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;700&family=Outfit:wght@300;400;600&display=swap');

--font-display: 'Quicksand', sans-serif;
--font-body: 'Outfit', sans-serif;
--font-mono: 'JetBrains Mono', monospace;
```

### 1.3 Effets Visuels & Animations

- ✨ **Sparkles animés**: Particules CSS scintillantes en arrière-plan (keyframes animation)
- 💎 **Glassmorphism**: Cards semi-transparentes avec `backdrop-filter: blur(10px)`
- 🌟 **Glow effects**: `box-shadow` avec couleurs Opalite sur connexions actives
- 🎬 **Smooth transitions**: 300-400ms `ease-out` pour tous les changements d'état
- 💗 **Pulsing indicators**: Animation breathing (`scale` + `opacity`) pour statuts Muse connectés
- 🌈 **Gradient overlays**: Radial gradients turquoise→bleu profond avec superposition sparkle

**Principe directeur:** Chaque élément UI doit évoquer la connexion cerveau-à-cerveau, la synchronie, et la beauté de l'activité neuronale partagée.

---

## 2. Architecture Système

L'architecture Neuropalite se compose de **4 modules principaux** interconnectés via des buffers circulaires et LSL streaming.

### 2.1 Vue d'Ensemble

```
┌─────────────────────────────────────────────────────────────┐
│                    NEUROPALITE SYSTEM                       │
└─────────────────────────────────────────────────────────────┘

 ┌──────────────┐        ┌──────────────┐
 │   Muse S 1   │        │   Muse S 2   │
 │  (Bluetooth) │        │  (Bluetooth) │
 └──────┬───────┘        └──────┬───────┘
        │                       │
        └───────┬───────────────┘
                │
                ▼
    ┌───────────────────────────┐
    │   Muse Manager Module     │
    │  - Connection handling    │
    │  - Auto-reconnect         │
    │  - Quality monitoring     │
    └───────────┬───────────────┘
                │
                ▼
    ┌───────────────────────────┐
    │   Circular Data Buffers   │
    │  - 10s rolling window     │
    │  - Thread-safe access     │
    └───────────┬───────────────┘
                │
                ▼
    ┌───────────────────────────┐
    │  Signal Processor Module  │
    │  - Bandpass filtering     │
    │  - Welch PSD estimation   │
    │  - Frequency bands        │
    └───────────┬───────────────┘
                │
                ▼
    ┌───────────────────────────┐
    │   Alpha Metrics Module    │
    │  - 4 normalization methods│
    │  - Real-time calculation  │
    └───────────┬───────────────┘
                │
                ├─────────────────────────┬───────────────────┐
                │                         │                   │
                ▼                         ▼                   ▼
    ┌────────────────────┐   ┌──────────────────┐   ┌──────────────┐
    │   LSL Streamer     │   │  Flask WebSocket │   │  Data Logger │
    │  - Raw EEG         │   │  - Real-time UI  │   │  - XDF files │
    │  - Freq Bands      │   │  - Visualizations│   │  - CSV       │
    │  - Alpha Metrics   │   │  - Controls      │   │  - BIDS      │
    └─────────┬──────────┘   └──────────────────┘   └──────────────┘
              │
              ▼
    ┌─────────────────────┐
    │   Unity VR/AR App   │
    │  - Biofeedback viz  │
    │  - Dancers sync     │
    └─────────────────────┘
```

### 2.2 Composants Détaillés

| Module | Responsabilité | Technologies |
|--------|----------------|-------------|
| **Muse Manager** | Connexion BT, monitoring qualité signal, auto-reconnect | `muse-lsl`, `bluepy`/`bleak` |
| **Data Buffer** | Circular buffers thread-safe, 10s rolling window | `numpy`, `threading.Lock` |
| **Signal Processor** | Filtering, PSD, frequency bands extraction | `scipy.signal`, `MNE-Python` |
| **Alpha Metrics** | Calcul + 4 normalisations (min-max, z-score, baseline, percentile) | `numpy`, `scipy.stats` |
| **LSL Streamer** | Outlets LSL (raw, bands, metrics) @ 10 Hz | `pylsl` |
| **Flask App** | Server HTTP, WebSocket, routing | `Flask`, `Flask-SocketIO`, `eventlet` |
| **WebSocket Handlers** | Events temps réel (status, metrics, bands) | `python-socketio` |
| **Frontend Opalite** | Interface utilisateur, visualisations, controls | HTML5, CSS3, Vanilla JS, Chart.js |
| **Data Logger** | Export XDF (raw), CSV (metrics), BIDS-compliant | `pyxdf`, `pandas` |

---

## 3. Structure des Fichiers

```
neuropalite/
├── config/
│   ├── muse_config.yaml              # Adresses BT, sampling, channels
│   └── processing_config.yaml        # Bandes freq, normalization params
│
├── core/
│   ├── __init__.py
│   ├── muse_manager.py               # Gestion connexion/déconnexion Muse
│   ├── signal_processor.py           # Pipeline DSP (filtering, PSD, bands)
│   ├── alpha_metrics.py              # Calcul métriques alpha normalisées
│   ├── lsl_streamer.py               # LSL outlets (raw + bands + metrics)
│   └── data_buffer.py                # Circular buffers pour visualisation
│
├── web/
│   ├── app.py                        # Flask app + SocketIO
│   ├── routes.py                     # Routes HTTP
│   ├── websocket_handlers.py        # Handlers Socket.IO temps réel
│   │
│   ├── static/
│   │   ├── css/
│   │   │   ├── opalite-theme.css          # Charte graphique
│   │   │   ├── animations.css             # Sparkles, glows, transitions
│   │   │   └── components.css             # Styles composants
│   │   │
│   │   ├── js/
│   │   │   ├── socket-client.js           # WebSocket client
│   │   │   ├── charts-manager.js          # Gestion Chart.js/Plotly
│   │   │   ├── connection-status.js       # UI status Muse
│   │   │   └── sparkles.js                # Effet sparkles animés
│   │   │
│   │   └── assets/
│   │       ├── background-sparkle.png     # Texture glitter
│   │       └── icons/                     # Icons custom
│   │
│   └── templates/
│       ├── base.html                      # Template de base
│       ├── dashboard.html                 # Vue principale
│       └── components/
│           ├── muse-status-card.html      # Card status par Muse
│           ├── alpha-metric-gauge.html    # Gauge métrique alpha
│           └── band-spectrum-plot.html    # Visualisation bandes
│
├── utils/
│   ├── logger.py                     # Logging configuré
│   └── validators.py                 # Validation config YAML
│
├── data/                             # Généré runtime (logs, XDF, CSV)
├── logs/                             # Généré runtime
├── requirements.txt
├── README.md
└── run.py                            # Entry point
```

---

## 4. Wireframes & Mockups Interface

### 4.1 Dashboard Principal

**Layout:** Grid 2x2 avec header fullwidth et footer controls.

```
╔═══════════════════════════════════════════════════════════════════╗
║                    NEUROPALITE DASHBOARD                          ║
║                 🧠 Dyadic Neurofeedback System                    ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  ┌─────────────────────────────┐  ┌─────────────────────────────┐║
║  │  MUSE 1 - PARTICIPANT A     │  │  MUSE 2 - PARTICIPANT B     │║
║  │  ────────────────────────   │  │  ────────────────────────   │║
║  │  Status: ● CONNECTED        │  │  Status: ● CONNECTED        │║
║  │  Battery: 87%               │  │  Battery: 92%               │║
║  │  Signal Quality: ████ Good  │  │  Signal Quality: ███▫ Fair  │║
║  │                             │  │                             │║
║  │  [Live EEG Trace...]        │  │  [Live EEG Trace...]        │║
║  └─────────────────────────────┘  └─────────────────────────────┘║
║                                                                   ║
║  ┌─────────────────────────────────────────────────────────────┐ ║
║  │  ALPHA METRICS (Normalized 0-1)                            │ ║
║  │                                                             │ ║
║  │  Participant A: ████████▫▫  0.78                           │ ║
║  │  Participant B: ██████▫▫▫▫  0.62                           │ ║
║  │                                                             │ ║
║  │  Normalization: [●] Min-Max  [ ] Z-Score  [ ] Baseline    │ ║
║  │                 [ ] Percentile                             │ ║
║  └─────────────────────────────────────────────────────────────┘ ║
║                                                                   ║
║  ┌─────────────────────────────────────────────────────────────┐ ║
║  │  FREQUENCY BANDS SPECTRUM                                  │ ║
║  │  [Interactive Chart.js visualization]                      │ ║
║  │   Delta │ Theta │ Alpha │ Beta │ Gamma                     │ ║
║  │     ▃      ▅      ████     ▆      ▂   (Participant A)     │ ║
║  │     ▄      ▆      ███      ▅      ▃   (Participant B)     │ ║
║  └─────────────────────────────────────────────────────────────┘ ║
║                                                                   ║
╠═══════════════════════════════════════════════════════════════════╣
║  Controls:                                                        ║
║  [Start Baseline]  [Stop Recording]  [Export Data (XDF)]         ║
║  LSL Streaming: ● Active @ 10 Hz                                 ║
╚═══════════════════════════════════════════════════════════════════╝
```

### 4.2 Composants UI Détaillés

| Composant | Description | Features |
|-----------|-------------|----------|
| **Muse Status Card** | Card affichant connexion, batterie, qualité signal par Muse | Pulsing indicator, color-coded quality, battery icon |
| **Alpha Metric Gauge** | Gauge horizontale (progress bar) 0-1 normalisée | Animated fill, glow effect, real-time value display |
| **Normalization Selector** | Radio buttons pour sélection méthode normalisation | 4 options, active method highlighted, instant switch |
| **Band Spectrum Plot** | Chart.js bar chart des 5 bandes de fréquence | Dual series (2 Muse), color-coded, auto-update @ 30 Hz |
| **Spectrogramme** | Heatmap temps-fréquence en temps réel (optionnel) | Plotly.js heatmap, scrolling window, channel selector |
| **Control Panel** | Boutons Start/Stop, baseline calibration, export | Gradient buttons, confirm dialogs, status feedback |
| **LSL Status Indicator** | Badge affichant status streaming LSL | Pulsing dot, update rate display, connection count |

---

## 5. Plan de Développement - Sprints

Développement itératif sur **10 jours** avec validation incrémentale à chaque sprint.

---

### 🏃 Sprint 1: Foundation & Setup (Jours 1-2)

**Objectif:** Infrastructure de base fonctionnelle

**Tasks:**
- ☐ Setup virtualenv + dependencies (`requirements.txt`)
- ☐ Création structure directories (`config/`, `core/`, `web/`, `utils/`)
- ☐ Configuration YAML (`muse_config.yaml` avec BT addresses)
- ☐ Logger configuré (`coloredlogs`)
- ☐ Validators pour YAML
- ☐ `muse_manager.py`: Connexion à 1 Muse (test avec `muse-lsl`)
- ☐ `data_buffer.py`: Circular buffer simple
- ☐ Flask app minimale + route `/`
- ☐ Test: Connexion 1 Muse + status dans terminal

**Deliverable:** ✅ Connexion réussie à 1 Muse Bluetooth avec affichage console

---

### 🧪 Sprint 2: Signal Processing Pipeline (Jours 3-4)

**Objectif:** Pipeline DSP complet opérationnel

**Tasks:**
- ☐ `signal_processor.py` - Filtrage bandpass (0.5-50 Hz)
- ☐ `signal_processor.py` - Notch filter 60 Hz
- ☐ `signal_processor.py` - Welch PSD estimation (4s window, 50% overlap)
- ☐ `signal_processor.py` - Extraction bandes (delta, theta, alpha, beta, gamma)
- ☐ `alpha_metrics.py` - Calcul métrique alpha (relative power)
- ☐ `alpha_metrics.py` - **4 méthodes normalisation** (min-max, z-score, baseline, percentile)
- ☐ Tests unitaires sur signaux synthétiques
- ☐ `muse_manager.py` - Extension pour 2 Muse simultanés
- ☐ Test: Métriques alpha calculées pour 2 Muse simultanément

**Deliverable:** ✅ Pipeline traitement 2 Muse avec métriques alpha normalisées

---

### 📡 Sprint 3: LSL Streaming (Jour 5)

**Objectif:** Streaming LSL opérationnel vers Unity

**Tasks:**
- ☐ `lsl_streamer.py` - Outlets `Muse1_Raw`, `Muse2_Raw`
- ☐ `lsl_streamer.py` - Outlets `Muse1_Bands`, `Muse2_Bands`
- ☐ `lsl_streamer.py` - Outlet `AlphaMetrics` (2 channels)
- ☐ Configuration `update_rate` 10 Hz
- ☐ Gestion reconnexion automatique LSL
- ☐ Validation avec LabRecorder (capture test XDF)
- ☐ Test Unity: Réception basique LSL streams
- ☐ Test: 3 types de streams actifs et validés

**Deliverable:** ✅ LSL streams testés et validés avec Unity (réception basique)

---

### 🎨 Sprint 4: Frontend Opalite - Design & Templates (Jours 6-7)

**Objectif:** Interface graphique complète avec charte Opalite

**Tasks:**
- ☐ `opalite-theme.css` - Palette couleurs, CSS variables
- ☐ `animations.css` - Keyframes sparkles, glows, pulses
- ☐ `components.css` - Styles cards, gauges, charts
- ☐ `sparkles.js` - Particules animées background
- ☐ Template `base.html` - Structure HTML + head
- ☐ Template `dashboard.html` - Layout grid complet
- ☐ Component `muse-status-card.html` - Status 2 Muse
- ☐ Component `alpha-metric-gauge.html` - Gauges normalisées
- ☐ Component `band-spectrum-plot.html` - Chart.js setup
- ☐ Test: Interface complète avec données mockées en HTML statique

**Deliverable:** ✅ Interface Opalite complète et fonctionnelle (données mockées)

---

### 🔌 Sprint 5: Real-time Integration Backend ↔ Frontend (Jours 8-9)

**Objectif:** Connexion temps réel complète

**Tasks:**
- ☐ Flask-SocketIO setup (`app.py`, `websocket_handlers.py`)
- ☐ `socket-client.js` - Connexion WebSocket client
- ☐ Event `muse_status` (connexion, batterie, qualité)
- ☐ Event `alpha_metrics` (valeurs normalisées 0-1)
- ☐ Event `frequency_bands` (spectres 5 bandes)
- ☐ `charts-manager.js` - Update Chart.js temps réel
- ☐ `connection-status.js` - UI feedback connexions Muse
- ☐ Thread backend broadcast @ 30 Hz (optimisé)
- ☐ Gestion déconnexion/reconnexion UI
- ☐ Test: Système end-to-end avec 2 Muse réels

**Deliverable:** ✅ Application fonctionnelle end-to-end avec feedback temps réel

---

### ✨ Sprint 6: Polish & Production-Ready (Jour 10)

**Objectif:** Application production-ready avec robustesse

**Tasks:**
- ☐ Gestion erreurs robuste (try/except, fallbacks)
- ☐ Logging complet (fichiers + console, rotation)
- ☐ Data export BIDS-compliant (XDF + CSV)
- ☐ Performance optimization (buffer sizes, throttling)
- ☐ Documentation README.md complète
- ☐ Tests système end-to-end automatisés
- ☐ Config validation stricte au démarrage
- ☐ Easter eggs design (hover sparkles subtils)
- ☐ Guide installation + quickstart
- ☐ Test: Déploiement complet et session complète 30min

**Deliverable:** ✅ Application production-ready testée en conditions réelles

---

## 6. Diagrammes de Flux Détaillés

### 6.1 Flux de Connexion Muse

```
START
  │
  ▼
┌─────────────────────────┐
│ Lecture muse_config.yaml│
│ Adresses BT récupérées  │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Pour chaque Muse:      │
│  - Scan Bluetooth       │
│  - Tentative connexion  │
└────────────┬────────────┘
             │
             ├────── Success ──────┐
             │                      ▼
             │            ┌──────────────────┐
             │            │ Connexion établie│
             │            │ Stream LSL créé  │
             │            │ Buffer circulaire│
             │            └─────────┬────────┘
             │                      │
             │                      ▼
             │            ┌──────────────────┐
             │            │ Monitoring actif │
             │            │ - Qualité signal │
             │            │ - Batterie       │
             │            │ - Impédance      │
             │            └─────────┬────────┘
             │                      │
             │                      ▼
             │            ┌──────────────────┐
             │            │ WebSocket emit   │
             │            │ 'muse_connected' │
             │            └──────────────────┘
             │
             └────── Échec ────────┐
                                   ▼
                         ┌──────────────────┐
                         │ Log erreur       │
                         │ Wait 5s          │
                         │ Retry (max 10x)  │
                         └─────────┬────────┘
                                   │
                                   └──> Retour tentative connexion

Déconnexion détectée pendant session:
  │
  ▼
┌──────────────────┐
│ WebSocket emit   │
│ 'muse_disconnect'│
└─────────┬────────┘
          │
          ▼
┌──────────────────┐
│ Auto-reconnect   │
│ activé (config)  │
└──────────────────┘
```

### 6.2 Pipeline Traitement Signal (DSP)

```
┌────────────────────┐
│ Muse Raw EEG Data  │
│ 256 Hz, 4 channels │
└──────────┬─────────┘
           │
           ▼
┌────────────────────┐
│ Circular Buffer    │
│ 10s window (2560)  │
└──────────┬─────────┘
           │
           ▼
┌────────────────────┐
│ Bandpass Filter    │
│ 0.5 - 50 Hz        │
│ 4th order Butter   │
└──────────┬─────────┘
           │
           ▼
┌────────────────────┐
│ Notch Filter       │
│ 60 Hz ± 5 Hz       │
└──────────┬─────────┘
           │
           ▼
┌────────────────────┐
│ Welch PSD          │
│ Window: 4s         │
│ Overlap: 50%       │
│ NFFT: 1024         │
└──────────┬─────────┘
           │
           ▼
┌────────────────────┐
│ Extract Bands      │
│ δ: 0.5-4 Hz       │
│ θ: 4-8 Hz         │
│ α: 8-13 Hz        │
│ β: 13-30 Hz       │
│ γ: 30-50 Hz       │
└──────────┬─────────┘
           │
           ├────────────┐
           │            │
           ▼            ▼
┌──────────────┐  ┌─────────────────┐
│ Relative     │  │ Absolute Power  │
│ Alpha Power  │  │ All Bands       │
│ α/(δ+θ+α+β+γ)│  │                 │
└──────┬───────┘  └────────┬────────┘
       │                   │
       └────────┬──────────┘
                │
                ▼
     ┌──────────────────────┐
     │ 4 Normalizations:    │
     │ 1. Min-Max (60s)     │
     │ 2. Z-Score+Sigmoid   │
     │ 3. Baseline calib    │
     │ 4. Percentile rank   │
     └──────────┬───────────┘
                │
                ├────────────┬──────────────┐
                │            │              │
                ▼            ▼              ▼
         ┌──────────┐  ┌─────────┐  ┌──────────┐
         │LSL Stream│  │WebSocket│  │CSV Logger│
         │@ 10 Hz   │  │@ 30 Hz  │  │          │
         └──────────┘  └─────────┘  └──────────┘
```

---

## 7. Spécifications Techniques

### 7.1 Paramètres Système

| Paramètre | Valeur |
|-----------|--------|
| **Muse Sampling Rate** | 256 Hz (standard Muse S) |
| **Channels** | TP9, AF7, AF8, TP10 (4 channels) |
| **Circular Buffer Duration** | 10 secondes (2560 samples @ 256 Hz) |
| **Bandpass Filter** | 0.5 - 50 Hz, 4th order Butterworth |
| **Notch Filter** | 60 Hz ± 5 Hz (secteur nord-américain) |
| **PSD Window** | 4 secondes (1024 samples) |
| **PSD Overlap** | 50% (512 samples) |
| **NFFT** | 1024 points |
| **Frequency Bands** | Delta: 0.5-4 Hz \| Theta: 4-8 Hz \| Alpha: 8-13 Hz \| Beta: 13-30 Hz \| Gamma: 30-50 Hz |
| **LSL Update Rate** | 10 Hz (vers Unity) |
| **WebSocket Update Rate** | 30 Hz (vers UI) |
| **Normalization Methods** | 4 méthodes: Min-Max, Z-Score+Sigmoid, Baseline Calibration, Percentile Ranking |
| **Data Export Format** | XDF (raw EEG) + CSV (métriques) - BIDS-compliant |

### 7.2 Méthodes de Normalisation Alpha (Détails Implémentation)

| Méthode | Formule | Cas d'usage |
|---------|---------|-------------|
| **1. Min-Max** | `(x - min) / (max - min)` sur fenêtre glissante 60s | Sessions courtes, range dynamique connu |
| **2. Z-Score + Sigmoid** | `sigmoid((x - μ) / σ)` où μ, σ calculés sur 60s | Distribution normale, outliers gérés |
| **3. Baseline Calibration** | `(x - baseline_mean) × scaling_factor`, clipped [0,1] | Phase calibration initiale (yeux fermés/ouverts) |
| **4. Percentile Ranking** | Rang percentile dans fenêtre 120s, lissage exponentiel | Sessions longues, adaptation progressive |

**Implémentation:**

```python
# Méthode 1: Min-Max
def normalize_minmax(alpha_power, window_duration=60):
    window_data = get_last_n_seconds(alpha_power, window_duration)
    min_val = np.min(window_data)
    max_val = np.max(window_data)
    return (alpha_power - min_val) / (max_val - min_val + 1e-8)

# Méthode 2: Z-Score + Sigmoid
def normalize_zscore_sigmoid(alpha_power, window_duration=60, temperature=1.0):
    window_data = get_last_n_seconds(alpha_power, window_duration)
    mean = np.mean(window_data)
    std = np.std(window_data)
    z_score = (alpha_power - mean) / (std + 1e-8)
    return 1 / (1 + np.exp(-z_score / temperature))

# Méthode 3: Baseline Calibration
def normalize_baseline(alpha_power, baseline_mean, scaling_factor=2.0):
    normalized = (alpha_power - baseline_mean) * scaling_factor
    return np.clip(normalized, 0, 1)

# Méthode 4: Percentile Ranking
def normalize_percentile(alpha_power, window_duration=120, smoothing=0.1):
    window_data = get_last_n_seconds(alpha_power, window_duration)
    percentile = scipy.stats.percentileofscore(window_data, alpha_power) / 100
    # Lissage exponentiel
    return smoothing * percentile + (1 - smoothing) * previous_percentile
```

---

## 8. Dependencies & Installation

### 8.1 Requirements

```txt
# Neuropalite - Requirements
# Python 3.8+

# Muse & EEG
muse-lsl>=2.0.2
pylsl>=1.16.0
numpy>=1.21.0
scipy>=1.7.0

# Signal processing
mne>=1.0.0

# Flask & WebSocket
Flask>=2.3.0
Flask-SocketIO>=5.3.0
python-socketio>=5.9.0
eventlet>=0.33.0

# Configuration
PyYAML>=6.0

# Data handling
pandas>=1.3.0
pyxdf>=1.16.5  # Pour export XDF BIDS-compliant

# Logging
coloredlogs>=15.0

# Utilities
python-dateutil>=2.8.0
```

### 8.2 Installation Steps

1. **Cloner le repository:**
   ```bash
   git clone <repo_url>
   cd neuropalite
   ```

2. **Créer virtualenv:**
   ```bash
   python -m venv venv
   ```

3. **Activer:**
   ```bash
   # Linux/Mac
   source venv/bin/activate
   
   # Windows
   venv\Scripts\activate
   ```

4. **Installer dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configurer adresses Bluetooth:**
   - Éditer `config/muse_config.yaml`
   - Remplacer les adresses `00:55:DA:B0:XX:XX` par les adresses réelles de vos Muse

6. **Lancer l'application:**
   ```bash
   python run.py
   ```

7. **Ouvrir navigateur:**
   ```
   http://localhost:5000
   ```

### 8.3 Configuration Muse (Exemple)

```yaml
# config/muse_config.yaml
muse_devices:
  muse_1:
    name: "Participant A"
    bluetooth_address: "00:55:DA:B0:12:34"  # Remplacer
    enabled: true
    color: "#FF6B9D"
    
  muse_2:
    name: "Participant B"
    bluetooth_address: "00:55:DA:B0:56:78"  # Remplacer
    enabled: true
    color: "#FF8C42"

acquisition:
  sampling_rate: 256
  channels: ["TP9", "AF7", "AF8", "TP10"]
  buffer_duration: 10
  auto_reconnect: true
  reconnect_delay: 5
  max_reconnect_attempts: 10
```

---

## 9. Conclusion

Ce plan de développement Neuropalite assure une approche **structurée et itérative** pour la création d'une interface de neurofeedback dyadique robuste, esthétiquement distinctive, et production-ready.

### Points clés:

- ✅ **Architecture modulaire** avec séparation claire des responsabilités
- ✅ **4 méthodes de normalisation alpha** configurables via UI
- ✅ **Streaming LSL performant** @ 10 Hz vers Unity
- ✅ **Interface Opalite immersive** avec feedback temps réel @ 30 Hz
- ✅ **Gestion robuste** des connexions Bluetooth (auto-reconnect)
- ✅ **Export BIDS-compliant** (XDF + CSV)

---

**✨ Ready to sparkle with synchronized brains ✨**

---

**Document version:** 1.0  
**Dernière mise à jour:** 17 Mars 2026  
**Auteur:** Claude + Rémy  
**PPSP Lab - CHU Sainte-Justine**
