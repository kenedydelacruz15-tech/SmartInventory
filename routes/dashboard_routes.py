from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from services.dashboard_service import get_dashboard_summary


dashboard_bp = Blueprint("dashboard_bp", __name__)


# Dashboard summary
@dashboard_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def get_dashboard():
    current_store_id = get_jwt_identity()

    try:
        summary = get_dashboard_summary(current_store_id)

        return jsonify(summary), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500