from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from services.analytics_service import (
    get_best_selling_products,
    get_slow_moving_products,
    get_daily_sales_trends,
    get_weekly_sales,
    get_monthly_sales,
    get_product_performance
)


analytics_bp = Blueprint("analytics_bp", __name__)


# Get and validate date filters
def get_date_filters():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    try:
        if start_date:
            datetime.strptime(start_date, "%Y-%m-%d")

        if end_date:
            datetime.strptime(end_date, "%Y-%m-%d")

    except ValueError:
        return None, None, (
            jsonify({
                "error": "Dates must use YYYY-MM-DD format"
            }),
            400
        )

    if start_date and end_date and start_date > end_date:
        return None, None, (
            jsonify({
                "error": "start_date cannot be after end_date"
            }),
            400
        )

    return start_date, end_date, None


# Best-selling products
@analytics_bp.route("/analytics/best-selling", methods=["GET"])
@jwt_required()
def best_selling_products():
    current_store_id = get_jwt_identity()

    start_date, end_date, error = get_date_filters()

    if error:
        return error

    try:
        products = get_best_selling_products(
            current_store_id,
            start_date,
            end_date
        )

        return jsonify({
            "start_date": start_date,
            "end_date": end_date,
            "total_products": len(products),
            "products": products
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Slow-moving products
@analytics_bp.route("/analytics/slow-moving", methods=["GET"])
@jwt_required()
def slow_moving_products():
    current_store_id = get_jwt_identity()

    start_date, end_date, error = get_date_filters()

    if error:
        return error

    try:
        products = get_slow_moving_products(
            current_store_id,
            start_date,
            end_date
        )

        return jsonify({
            "start_date": start_date,
            "end_date": end_date,
            "total_products": len(products),
            "products": products
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Daily sales
@analytics_bp.route("/analytics/daily-sales", methods=["GET"])
@jwt_required()
def daily_sales_trends():
    current_store_id = get_jwt_identity()

    start_date, end_date, error = get_date_filters()

    if error:
        return error

    try:
        trends = get_daily_sales_trends(
            current_store_id,
            start_date,
            end_date
        )

        return jsonify({
            "start_date": start_date,
            "end_date": end_date,
            "total_days": len(trends),
            "trends": trends
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Weekly sales
@analytics_bp.route("/analytics/weekly-sales", methods=["GET"])
@jwt_required()
def weekly_sales():
    current_store_id = get_jwt_identity()

    start_date, end_date, error = get_date_filters()

    if error:
        return error

    try:
        sales = get_weekly_sales(
            current_store_id,
            start_date,
            end_date
        )

        return jsonify({
            "start_date": start_date,
            "end_date": end_date,
            "total_weeks": len(sales),
            "sales": sales
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Monthly sales
@analytics_bp.route("/analytics/monthly-sales", methods=["GET"])
@jwt_required()
def monthly_sales():
    current_store_id = get_jwt_identity()

    start_date, end_date, error = get_date_filters()

    if error:
        return error

    try:
        sales = get_monthly_sales(
            current_store_id,
            start_date,
            end_date
        )

        return jsonify({
            "start_date": start_date,
            "end_date": end_date,
            "total_months": len(sales),
            "sales": sales
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Product performance
@analytics_bp.route("/analytics/product-performance", methods=["GET"])
@jwt_required()
def product_performance():
    current_store_id = get_jwt_identity()

    start_date, end_date, error = get_date_filters()

    if error:
        return error

    try:
        products = get_product_performance(
            current_store_id,
            start_date,
            end_date
        )

        return jsonify({
            "start_date": start_date,
            "end_date": end_date,
            "total_products": len(products),
            "products": products
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500