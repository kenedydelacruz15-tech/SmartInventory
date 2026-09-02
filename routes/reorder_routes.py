from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from services.reorder_service import get_reorder_recommendations


reorder_bp = Blueprint("reorder_bp", __name__)


@reorder_bp.route("/reorder-recommendations", methods=["GET"])
@jwt_required()
def reorder_recommendations():
    store_id = get_jwt_identity()

    try:
        recommendations = get_reorder_recommendations(store_id)

        return jsonify({
            "recommendation_count": len(recommendations),
            "recommendations": recommendations
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500