from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import get_db_connection


reorder_bp = Blueprint("reorder_bp", __name__)


# Return products that need to be reordered for the logged-in store.
@reorder_bp.route("/reorder-recommendations", methods=["GET"])
@jwt_required()
def get_reorder_recommendations():

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Get products whose stock has reached or fallen below the reorder level.
        cursor.execute(
            """
            SELECT
                p.product_id,
                p.product_name,
                p.barcode,
                c.category_name,

                COALESCE(i.stock_quantity, 0) AS current_stock,

                p.reorder_level,

                CASE
                    WHEN COALESCE(i.stock_quantity, 0) <= 0
                        THEN 'OUT_OF_STOCK'

                    WHEN COALESCE(i.stock_quantity, 0) <= p.reorder_level
                        THEN 'REORDER_NOW'

                    ELSE 'STOCK_OK'
                END AS reorder_status,

                CASE
                    WHEN COALESCE(i.stock_quantity, 0) <= 0
                        THEN p.reorder_level

                    ELSE
                        p.reorder_level - COALESCE(i.stock_quantity, 0)
                END AS minimum_reorder_quantity

            FROM products p

            LEFT JOIN inventory i
                ON p.product_id = i.product_id

            LEFT JOIN categories c
                ON p.category_id = c.category_id
                AND c.store_id = p.store_id

            WHERE
                p.store_id = %s
                AND COALESCE(i.stock_quantity, 0) <= p.reorder_level

            ORDER BY
                COALESCE(i.stock_quantity, 0) ASC,
                p.product_name ASC
            """,
            (current_store_id,)
        )

        products = cursor.fetchall()

        # Count products by reorder priority.
        out_of_stock_count = 0
        reorder_now_count = 0

        for product in products:

            if product["reorder_status"] == "OUT_OF_STOCK":
                out_of_stock_count += 1

            elif product["reorder_status"] == "REORDER_NOW":
                reorder_now_count += 1

        return jsonify({
            "recommendation_count": len(products),

            "summary": {
                "out_of_stock": out_of_stock_count,
                "reorder_now": reorder_now_count
            },

            "recommendations": products
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()