"""Neuropalite — Entry point.

Usage::

    python run.py
    # or
    uv run python run.py

Opens the Opalite dashboard at http://localhost:5000
"""

import logging

from neuropalite.utils.logger import setup_logging
from neuropalite.utils.validators import (
    load_yaml,
    validate_muse_config,
    validate_processing_config,
)
from neuropalite.web.app import create_app, socketio

logger = logging.getLogger(__name__)


def main() -> None:
    """Initialize configs, create app, and start the server."""
    setup_logging(level="DEBUG")

    # Load & validate configs
    muse_cfg = load_yaml("muse_config.yaml")
    validate_muse_config(muse_cfg)

    proc_cfg = load_yaml("processing_config.yaml")
    validate_processing_config(proc_cfg)

    logger.info("All configs validated — starting Neuropalite server")

    # Create Flask app
    app = create_app()

    # Store configs on app for access by routes/handlers
    app.config["MUSE_CONFIG"] = muse_cfg
    app.config["PROCESSING_CONFIG"] = proc_cfg

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
