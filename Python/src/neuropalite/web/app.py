"""Flask application factory for Neuropalite.

Creates the Flask app with SocketIO support and registers routes.
The app serves the Opalite dashboard and provides real-time WebSocket
communication for Muse status, alpha metrics, and frequency band data.
"""

import logging

from flask import Flask
from flask_socketio import SocketIO

logger = logging.getLogger(__name__)

socketio = SocketIO()


def create_app() -> Flask:
    """Create and configure the Flask application.

    Returns
    -------
    Flask
        Configured Flask app with SocketIO and routes registered.
    """
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
    )
    app.config["SECRET_KEY"] = "neuropalite-dev-key"

    # Initialize SocketIO with eventlet async mode
    socketio.init_app(app, async_mode="threading", cors_allowed_origins="*")

    # Register routes
    from neuropalite.web.routes import bp

    app.register_blueprint(bp)

    # Register WebSocket handlers
    from neuropalite.web import websocket_handlers  # noqa: F401

    logger.info("Flask app created")
    return app
