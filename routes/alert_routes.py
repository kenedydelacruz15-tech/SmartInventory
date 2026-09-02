from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from services.alert_service import (
    get_all_smart_alerts,
    get_expiring_alerts,
    get_expired_alerts,
    get_low_stock_alerts,
    get_out_of_stock_alerts
)


alert_bp = Blueprint("alert_bp", __name__)


# Get all current smart alerts
@alert_bp.route("/alerts", methods=["GET"])
@jwt_required()
def get_alerts():
    store_id = get_jwt_identity()

    try:
        alerts = get_all_smart_alerts(store_id)

        return jsonify({
            "alert_count": len(alerts),
            "alerts": alerts
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


# Get expiring products
@alert_bp.route("/alerts/expiring", methods=["GET"])
@jwt_required()
def expiring_alerts():
    store_id = get_jwt_identity()

    try:
        products = get_expiring_alerts(store_id)

        return jsonify({
            "alert_count": len(products),
            "expiring_products": products
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


# Get expired products
@alert_bp.route("/alerts/expired", methods=["GET"])
@jwt_required()
def expired_alerts():
    store_id = get_jwt_identity()

    try:
        products = get_expired_alerts(store_id)

        return jsonify({
            "alert_count": len(products),
            "expired_products": products
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


# Get low-stock products
@alert_bp.route("/alerts/low-stock", methods=["GET"])
@jwt_required()
def low_stock_alerts():
    store_id = get_jwt_identity()

    try:
        products = get_low_stock_alerts(store_id)

        return jsonify({
            "alert_count": len(products),
            "low_stock_products": products
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


# Get out-of-stock products
@alert_bp.route("/alerts/out-of-stock", methods=["GET"])
@jwt_required()
def out_of_stock_alerts():
    store_id = get_jwt_identity()

    try:
        products = get_out_of_stock_alerts(store_id)

        return jsonify({
            "alert_count": len(products),
            "out_of_stock_products": products
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500