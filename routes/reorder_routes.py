from flask import Blueprint, jsonify
from services.reorder_service import get_reorder_recommendations
from flask_jwt_extended import jwt_required, get_jwt_identity

reorder_bp = Blueprint("reorder_bp", __name__)


@reorder_bp.route("/forecast/reorder", methods=["GET"])
@jwt_required()
def reorder_recommendation():
    """
    Fetches replenishment and reorder recommendations for the active store owner.
    """
    current_store_id = get_jwt_identity()
    recommendations = get_reorder_recommendations(current_store_id)

    return jsonify(recommendations)
