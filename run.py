"""Neuropalite — Entry point.

Usage::

    python run.py
    # or
    uv run python run.py

Opens the Opalite dashboard at http://localhost:5000
"""

import logging

from neuropalite.core.alpha_metrics import AlphaMetricsCalculator
from neuropalite.core.data_logger import DataLogger
from neuropalite.core.lsl_streamer import LSLStreamer
from neuropalite.core.muse_manager import MuseManager
from neuropalite.core.signal_processor import SignalProcessor
from neuropalite.core.streaming_orchestrator import StreamingOrchestrator
from neuropalite.utils.logger import setup_logging
from neuropalite.utils.validators import (
    load_yaml,
    validate_muse_config,
    validate_processing_config,
)
from neuropalite.web.app import create_app, socketio

logger = logging.getLogger(__name__)


def main() -> None:
    """Initialize configs, create all modules, and start the server."""
    setup_logging(level="DEBUG")

    # Load & validate configs
    muse_cfg = load_yaml("muse_config.yaml")
    validate_muse_config(muse_cfg)

    proc_cfg = load_yaml("processing_config.yaml")
    validate_processing_config(proc_cfg)

    logger.info("All configs validated — initializing Neuropalite")

    # --- Core modules ---
    muse_manager = MuseManager(muse_cfg)
    signal_processor = SignalProcessor(proc_cfg)

    device_ids = list(muse_manager.devices.keys())
    alpha_calculator = AlphaMetricsCalculator(proc_cfg, device_ids)

    lsl_streamer = LSLStreamer(muse_cfg, proc_cfg)
    lsl_streamer.setup(device_ids)

    data_logger = DataLogger(muse_cfg, proc_cfg)

    # --- Orchestrator ---
    orchestrator = StreamingOrchestrator(
        muse_manager=muse_manager,
        signal_processor=signal_processor,
        alpha_calculator=alpha_calculator,
        lsl_streamer=lsl_streamer,
        processing_config=proc_cfg,
    )
    orchestrator.set_socketio(socketio)

    # --- Flask app ---
    app = create_app()

    # Store references for access by routes/handlers
    app.config["MUSE_CONFIG"] = muse_cfg
    app.config["PROCESSING_CONFIG"] = proc_cfg
    app.config["MUSE_MANAGER"] = muse_manager
    app.config["ORCHESTRATOR"] = orchestrator
    app.config["DATA_LOGGER"] = data_logger

    # Connect Muse devices and start processing
    logger.info("Connecting Muse devices...")
    muse_manager.connect_all()
    orchestrator.start()

    logger.info("Starting Neuropalite server at http://localhost:5000")

    # Run with SocketIO (eventlet)
    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=False,  # reloader conflicts with Muse threads
    )


if __name__ == "__main__":
    main()
