from flask import Blueprint, jsonify
from services.alert_service import get_smart_alerts
from flask_jwt_extended import jwt_required, get_jwt_identity

alert_bp = Blueprint("alert_bp", __name__)


@alert_bp.route("/alerts", methods=["GET"])
@jwt_required()
def smart_alerts():
    """
    Fetches low-stock and expiration alerts for the logged-in store owner.
    """
    # Get active store id from token
    current_store_id = get_jwt_identity()

    # Pass store id to the alert service to filter calculations
    alerts = get_smart_alerts(current_store_id)

    return jsonify({
        "total_alerts": len(alerts),
        "alerts": alerts
    })
