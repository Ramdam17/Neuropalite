"""WebSocket event handlers for real-time communication.

Handles SocketIO events between the Flask backend and the Opalite
frontend, including Muse status updates, alpha metrics, and frequency
band data.

These handlers will be fully wired in Sprint 5 (real-time integration).
"""

import logging

from neuropalite.web.app import socketio

logger = logging.getLogger(__name__)


@socketio.on("connect")
def handle_connect():
    """Client connected to WebSocket."""
    logger.info("WebSocket client connected")


@socketio.on("disconnect")
def handle_disconnect():
    """Client disconnected from WebSocket."""
    logger.info("WebSocket client disconnected")


@socketio.on("request_status")
def handle_request_status():
    """Client requests current device status."""
    # Will emit full device status in Sprint 5
    socketio.emit("muse_status", {"devices": {}})
