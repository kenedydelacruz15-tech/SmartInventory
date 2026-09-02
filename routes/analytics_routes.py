from flask import Blueprint, jsonify
from services.analytics_service import (
    get_best_selling_products,
    get_slow_moving_products,
    get_daily_sales_trends,
    get_weekly_sales,
    get_monthly_sales,
    get_product_performance
)
#extract the logged-in user identity context
from flask_jwt_extended import jwt_required, get_jwt_identity

analytics_bp = Blueprint(
    "analytics_bp",
    __name__
)


@analytics_bp.route(
    "/analytics/best-selling",
    methods=["GET"]
)
@jwt_required()
def best_selling_products():
    """
    Fetches the highest revenue items for the active store.
    """
    current_store_id = get_jwt_identity()
    products = get_best_selling_products(current_store_id)

    return jsonify({
        "total_products": len(products),
        "products": products
    })

@analytics_bp.route(
    "/analytics/slow-moving",
    methods=["GET"]
)
@jwt_required()
def slow_moving_products():
    """
    Identifies low-turnover grocery stock for the active store.
    """
    current_store_id = get_jwt_identity()
    products = get_slow_moving_products(current_store_id)

    return jsonify({
        "total_products": len(products),
        "products": products
    })

@analytics_bp.route(
    "/analytics/daily-sales",
    methods=["GET"]
)
@jwt_required()
def daily_sales_trends():
    """
    Calculates day-by-day revenue trends for the active store.
    """
    current_store_id = get_jwt_identity()
    trends = get_daily_sales_trends(current_store_id)

    return jsonify({
        "total_days": len(trends),
        "trends": trends
    })


@analytics_bp.route(
    "/analytics/weekly-sales",
    methods=["GET"]
)
@jwt_required()
def weekly_sales():
    """
    Calculates weekly consolidated invoice metrics for the active store.
    """
    current_store_id = get_jwt_identity()
    sales = get_weekly_sales(current_store_id)

    return jsonify({
        "total_weeks": len(sales),
        "sales": sales
    }) 

@analytics_bp.route(
    "/analytics/monthly-sales",
    methods=["GET"]
)
@jwt_required()
def monthly_sales():
    """
    Calculates monthly store profit history for the active store.
    """
    current_store_id = get_jwt_identity()
    sales = get_monthly_sales(current_store_id)

    return jsonify({
        "total_months": len(sales),
        "sales": sales
    })

@analytics_bp.route(
    "/analytics/product-performance",
    methods=["GET"]
)
@jwt_required()
def product_performance():
    """
    Evaluates individual product margins and stock velocity for the active store.
    """
    current_store_id = get_jwt_identity()
    products = get_product_performance(current_store_id)

    return jsonify({
        "total_products": len(products),
        "products": products
    })
