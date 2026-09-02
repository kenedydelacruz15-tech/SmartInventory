from flask import Blueprint, jsonify
from database import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity

stock_movement_bp = Blueprint("stock_movement_bp", __name__)


@stock_movement_bp.route("/stock-movements", methods=["GET"])
@jwt_required()
def get_stock_movements():
    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                sm.movement_id,
                p.product_name,
                sm.movement_type,
                sm.quantity,
                sm.reference_id,
                sm.movement_date
            FROM stock_movements sm
            JOIN products p
                ON sm.product_id = p.product_id
            WHERE p.store_id = %s
            ORDER BY sm.movement_id DESC
            """,
            (current_store_id,)
        )

        movements = cursor.fetchall()

        return jsonify(movements), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

    finally:
        cursor.close()
        db.close()