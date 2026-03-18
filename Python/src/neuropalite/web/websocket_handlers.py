"""WebSocket event handlers for real-time communication.

Handles SocketIO events between the Flask backend and the Opalite
frontend, including Muse status updates, alpha metrics, frequency
band data, and user control actions (baseline, stop, normalization).
"""

import logging

from flask import current_app

from neuropalite.web.app import socketio

logger = logging.getLogger(__name__)


def _get_orchestrator():
    """Retrieve the StreamingOrchestrator from the Flask app config."""
    return current_app.config.get("ORCHESTRATOR")


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
    orch = _get_orchestrator()
    if orch:
        socketio.emit("muse_status", {"devices": orch._muse.get_all_info()})
        socketio.emit("orchestrator_status", orch.get_status())
    else:
        socketio.emit("muse_status", {"devices": {}})


@socketio.on("set_normalization")
def handle_set_normalization(data):
    """Client changes the normalization method.

    Expected payload: ``{"method": "minmax" | "zscore" | "baseline" | "percentile"}``
    """
    method = data.get("method", "minmax")
    orch = _get_orchestrator()
    if orch:
        orch.set_normalization(method)
        logger.info("Normalization method set to: %s", method)
        socketio.emit("normalization_changed", {"method": method})


@socketio.on("start_baseline")
def handle_start_baseline(data=None):
    """Client requests baseline calibration.

    Optional payload: ``{"duration": 30}`` (seconds).
    """
    duration = 30.0
    if data and "duration" in data:
        duration = float(data["duration"])

    orch = _get_orchestrator()
    if orch:
        orch.start_baseline_calibration(duration)
        logger.info("Baseline calibration started (%.0fs)", duration)


@socketio.on("stop_recording")
def handle_stop_recording():
    """Client requests to stop recording."""
    orch = _get_orchestrator()
    if orch:
        orch.stop()
        logger.info("Recording stopped via WebSocket")
        socketio.emit("recording_stopped", {})


@socketio.on("export_data")
def handle_export_data(data=None):
    """Client requests data export.

    Optional payload: ``{"format": "xdf" | "csv" | "both"}``.
    """
    fmt = "both"
    if data and "format" in data:
        fmt = data["format"]

    data_logger = current_app.config.get("DATA_LOGGER")
    if data_logger:
        output_path = data_logger.export(fmt)
        socketio.emit("export_complete", {"path": str(output_path), "format": fmt})
        logger.info("Data exported: %s (%s)", output_path, fmt)
    else:
        socketio.emit("export_error", {"error": "Data logger not available"})
