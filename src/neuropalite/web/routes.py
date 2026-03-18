"""HTTP routes for the Neuropalite web interface.

Provides the main dashboard view and API endpoints for device
and orchestrator status.
"""

import logging

from flask import Blueprint, current_app, jsonify, render_template

logger = logging.getLogger(__name__)

bp = Blueprint("main", __name__)


@bp.route("/")
def dashboard():
    """Render the main Neuropalite dashboard."""
    return render_template("dashboard.html")


@bp.route("/api/status")
def api_status():
    """Return JSON status of orchestrator + all Muse devices."""
    orch = current_app.config.get("ORCHESTRATOR")
    if orch:
        return jsonify(orch.get_status())
    return jsonify({"status": "ok", "devices": {}})
