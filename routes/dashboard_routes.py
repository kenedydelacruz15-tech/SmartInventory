from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import get_db_connection


dashboard_bp = Blueprint("dashboard_bp", __name__)


# Return daily sales data for the selected number of days.
@dashboard_bp.route("/dashboard/charts/sales", methods=["GET"])
@jwt_required()
def get_sales_chart():

    current_store_id = get_jwt_identity()

    days = request.args.get("days", default=7, type=int)

    if days <= 0:
        return jsonify({
            "error": "Days must be greater than 0."
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                DATE(sale_date) AS sale_day,
                COUNT(sale_id) AS sale_count,
                COALESCE(SUM(total_sales), 0) AS total_sales

            FROM sales

            WHERE
                store_id = %s
                AND DATE(sale_date) >= DATE_SUB(
                    CURDATE(),
                    INTERVAL %s DAY
                )

            GROUP BY DATE(sale_date)

            ORDER BY sale_day ASC
            """,
            (
                current_store_id,
                days
            )
        )

        sales_data = cursor.fetchall()

        return jsonify({
            "chart": "sales_trend",
            "period_days": days,
            "data": sales_data
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()


# Return the total available stock grouped by category.
@dashboard_bp.route("/dashboard/charts/category-stock", methods=["GET"])
@jwt_required()
def get_category_stock_chart():

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                COALESCE(
                    c.category_name,
                    'Uncategorized'
                ) AS category_name,

                COALESCE(
                    SUM(i.stock_quantity),
                    0
                ) AS total_stock

            FROM products p

            LEFT JOIN categories c
                ON p.category_id = c.category_id
                AND c.store_id = p.store_id

            LEFT JOIN inventory i
                ON p.product_id = i.product_id

            WHERE p.store_id = %s

            GROUP BY
                c.category_id,
                c.category_name

            ORDER BY total_stock DESC
            """,
            (current_store_id,)
        )

        category_data = cursor.fetchall()

        return jsonify({
            "chart": "stock_by_category",
            "data": category_data
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()


# Return the number of products in each inventory status.
@dashboard_bp.route("/dashboard/charts/inventory-status", methods=["GET"])
@jwt_required()
def get_inventory_status_chart():

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                CASE

                    WHEN COALESCE(i.stock_quantity, 0) <= 0
                        THEN 'OUT_OF_STOCK'

                    WHEN COALESCE(i.stock_quantity, 0) <= p.reorder_level
                        THEN 'LOW_STOCK'

                    ELSE 'IN_STOCK'

                END AS stock_status,

                COUNT(p.product_id) AS product_count

            FROM products p

            LEFT JOIN inventory i
                ON p.product_id = i.product_id

            WHERE p.store_id = %s

            GROUP BY stock_status
            """,
            (current_store_id,)
        )

        status_data = cursor.fetchall()

        return jsonify({
            "chart": "inventory_status",
            "data": status_data
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()


# Return stock movement totals for the selected number of days.
@dashboard_bp.route("/dashboard/charts/stock-movements", methods=["GET"])
@jwt_required()
def get_stock_movement_chart():

    current_store_id = get_jwt_identity()

    days = request.args.get("days", default=7, type=int)

    if days <= 0:
        return jsonify({
            "error": "Days must be greater than 0."
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                sm.movement_type,
                COALESCE(SUM(sm.quantity), 0) AS total_quantity

            FROM stock_movements sm

            JOIN products p
                ON sm.product_id = p.product_id

            WHERE
                p.store_id = %s
                AND DATE(sm.movement_date) >= DATE_SUB(
                    CURDATE(),
                    INTERVAL %s DAY
                )

            GROUP BY sm.movement_type

            ORDER BY sm.movement_type ASC
            """,
            (
                current_store_id,
                days
            )
        )

        movement_data = cursor.fetchall()

        return jsonify({
            "chart": "stock_movements",
            "period_days": days,
            "data": movement_data
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()