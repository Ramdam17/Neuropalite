"""HTTP routes for the Neuropalite web interface.

Provides the main dashboard view and API endpoints for device status.
"""

import logging

from flask import Blueprint, jsonify, render_template

logger = logging.getLogger(__name__)

bp = Blueprint("main", __name__)


@bp.route("/")
def dashboard():
    """Render the main Neuropalite dashboard."""
    return render_template("dashboard.html")


@bp.route("/api/status")
def api_status():
    """Return JSON status of all Muse devices.

    This endpoint is used for initial page load; real-time updates
    go through WebSocket events.
    """
    # Will be connected to MuseManager in Sprint 5
    return jsonify({"status": "ok", "devices": {}})
