from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from database import get_db_connection

inventory_bp = Blueprint("inventory_bp", __name__)

# =========================
# CURRENT INVENTORY
# =========================

@inventory_bp.route("/inventory", methods=["GET"])
@jwt_required()
def get_inventory():
    """Return the current inventory for the logged-in store."""

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        sql = """
            SELECT
                p.product_id,
                p.product_name,
                c.category_name,
                p.price,
                COALESCE(i.stock_quantity, 0) AS stock_quantity
            FROM products p
            LEFT JOIN categories c
                ON p.category_id = c.category_id
            LEFT JOIN inventory i
                ON p.product_id = i.product_id
            WHERE p.store_id = %s
            ORDER BY p.product_name ASC
        """

        cursor.execute(sql, (current_store_id,))
        inventory = cursor.fetchall()

        return jsonify(inventory), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        db.close()


# =========================
# PRODUCT BATCHES
# =========================

@inventory_bp.route("/inventory/batches", methods=["GET"])
@jwt_required()
def get_batches():
    """Return all batches with expiry information."""

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        sql = """
            SELECT
                b.batch_id,
                p.product_name,
                b.quantity,
                b.purchase_price,
                b.expiry_date
            FROM batches b
            JOIN products p
                ON b.product_id = p.product_id
            WHERE b.store_id = %s
            ORDER BY b.expiry_date ASC
        """

        cursor.execute(sql, (current_store_id,))
        batches = cursor.fetchall()

        return jsonify(batches), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        db.close()


# =========================
# EXPIRING BATCHES (Next 7 Days)
# =========================

@inventory_bp.route("/inventory/alerts/expiring", methods=["GET"])
@jwt_required()
def get_expiring_batches():

    current_store_id = get_jwt_identity()

    today = datetime.now().date()
    seven_days_later = today + timedelta(days=7)

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        sql = """
            SELECT
                b.batch_id,
                p.product_name,
                b.quantity,
                b.purchase_price,
                b.expiry_date
            FROM batches b
            JOIN products p
                ON b.product_id = p.product_id
            WHERE
                b.store_id = %s
                AND b.quantity > 0
                AND b.expiry_date BETWEEN %s AND %s
            ORDER BY b.expiry_date ASC
        """

        cursor.execute(
            sql,
            (current_store_id, today, seven_days_later)
        )

        expiring_items = cursor.fetchall()

        return jsonify({
            "alert_count": len(expiring_items),
            "expiring_batches": expiring_items
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        db.close()


# =========================
# EXPIRED PRODUCTS
# =========================

@inventory_bp.route("/inventory/alerts/expired", methods=["GET"])
@jwt_required()
def get_expired_batches():

    current_store_id = get_jwt_identity()

    today = datetime.now().date()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        sql = """
            SELECT
                b.batch_id,
                p.product_name,
                b.quantity,
                b.purchase_price,
                b.expiry_date
            FROM batches b
            JOIN products p
                ON b.product_id = p.product_id
            WHERE
                b.store_id = %s
                AND b.quantity > 0
                AND b.expiry_date < %s
            ORDER BY b.expiry_date ASC
        """

        cursor.execute(sql, (current_store_id, today))

        expired_items = cursor.fetchall()

        return jsonify({
            "expired_count": len(expired_items),
            "expired_batches": expired_items
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        db.close()