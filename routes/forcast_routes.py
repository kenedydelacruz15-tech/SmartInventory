from flask import Blueprint, jsonify
from services.forecast_service import (
    get_demand_forecast,
    get_stockout_predictions,
    get_forecast_results
)
from flask_jwt_extended import jwt_required, get_jwt_identity

forecast_bp = Blueprint("forecast_bp", __name__)


@forecast_bp.route("/forecast/demand", methods=["GET"])
@jwt_required()
def demand_forecast():
    """
    Fetches machine learning demand forecasts for the active store owner.
    """
    current_store_id = get_jwt_identity()
    forecasts = get_demand_forecast(current_store_id)

    return jsonify(forecasts)


@forecast_bp.route("/forecast/stockout", methods=["GET"])
@jwt_required()
def stockout_prediction():
    """
    Fetches running depletion timeline estimations for the active store owner.
    """
    current_store_id = get_jwt_identity()
    predictions = get_stockout_predictions(current_store_id)

    return jsonify(predictions)


@forecast_bp.route(
    "/forecast/results",
    methods=["GET"]
)
@jwt_required()
def forecast_results():
    """
    Fetches aggregated summary trends of prediction metrics for the active store owner.
    """
    current_store_id = get_jwt_identity()
    results = get_forecast_results(current_store_id)

    return jsonify({
        "total_products": len(results),
        "results": results
    })
