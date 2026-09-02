from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from database import get_db_connection


inventory_bp = Blueprint("inventory_bp", __name__)


@inventory_bp.route("/inventory", methods=["GET"])
@jwt_required()
def get_inventory():
    # Get current inventory only for products owned by the logged-in store.

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                p.product_id,
                p.product_name,
                p.barcode,
                c.category_name,
                p.price,
                p.reorder_level,
                COALESCE(i.stock_quantity, 0) AS stock_quantity,

                CASE
                    WHEN COALESCE(i.stock_quantity, 0) <= 0
                        THEN 'OUT_OF_STOCK'

                    WHEN COALESCE(i.stock_quantity, 0) <= p.reorder_level
                        THEN 'LOW_STOCK'

                    ELSE 'IN_STOCK'
                END AS stock_status

            FROM products p

            LEFT JOIN categories c
                ON p.category_id = c.category_id
                AND c.store_id = p.store_id

            LEFT JOIN inventory i
                ON p.product_id = i.product_id

            WHERE p.store_id = %s

            ORDER BY p.product_name ASC
            """,
            (current_store_id,)
        )

        inventory = cursor.fetchall()

        return jsonify({
            "inventory_count": len(inventory),
            "inventory": inventory
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

    finally:
        cursor.close()
        db.close()


@inventory_bp.route("/inventory/batches", methods=["GET"])
@jwt_required()
def get_batches():
    # Get all batches belonging to the logged-in store.

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                b.batch_id,
                b.product_id,
                p.product_name,
                b.quantity,
                b.purchase_price,
                b.expiry_date,
                b.created_at

            FROM batches b

            JOIN products p
                ON b.product_id = p.product_id
                AND p.store_id = b.store_id

            WHERE b.store_id = %s

            ORDER BY b.expiry_date ASC, b.batch_id ASC
            """,
            (current_store_id,)
        )

        batches = cursor.fetchall()

        return jsonify({
            "batch_count": len(batches),
            "batches": batches
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

    finally:
        cursor.close()
        db.close()


@inventory_bp.route("/inventory/batches/<int:id>", methods=["GET"])
@jwt_required()
def get_batch(id):
    # Get one batch only if it belongs to the logged-in store.

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                b.batch_id,
                b.product_id,
                p.product_name,
                b.quantity,
                b.purchase_price,
                b.expiry_date,
                b.created_at

            FROM batches b

            JOIN products p
                ON b.product_id = p.product_id
                AND p.store_id = b.store_id

            WHERE b.batch_id = %s
              AND b.store_id = %s
            """,
            (id, current_store_id)
        )

        batch = cursor.fetchone()

        if not batch:
            return jsonify({
                "error": "Batch not found"
            }), 404

        return jsonify(batch), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

    finally:
        cursor.close()
        db.close()

# Return batches that are expired or will expire within the selected number of days.
@inventory_bp.route("/inventory/alerts/expiring", methods=["GET"])
@jwt_required()
def get_expiring_batches():

    current_store_id = get_jwt_identity()

    # Get the number of days from the URL and default to 7 days.
    days = request.args.get("days", default=7, type=int)

    if days < 0:
        return jsonify({
            "error": "Days must be 0 or greater."
        }), 400

    today = datetime.now().date()
    end_date = today + timedelta(days=days)

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Get all batches with stock that expire within the selected period.
        cursor.execute(
            """
            SELECT
                b.batch_id,
                b.product_id,
                p.product_name,
                p.barcode,
                b.quantity,
                b.purchase_price,
                b.expiry_date,

                DATEDIFF(
                    b.expiry_date,
                    CURDATE()
                ) AS days_until_expiry,

                CASE

                    WHEN b.expiry_date < CURDATE()
                        THEN 'EXPIRED'

                    WHEN b.expiry_date = CURDATE()
                        THEN 'EXPIRES_TODAY'

                    WHEN DATEDIFF(
                        b.expiry_date,
                        CURDATE()
                    ) BETWEEN 1 AND 3
                        THEN 'CRITICAL'

                    WHEN DATEDIFF(
                        b.expiry_date,
                        CURDATE()
                    ) BETWEEN 4 AND 7
                        THEN 'WARNING'

                    ELSE 'UPCOMING'

                END AS expiry_status

            FROM batches b

            JOIN products p
                ON b.product_id = p.product_id
                AND p.store_id = b.store_id

            WHERE
                b.store_id = %s
                AND b.quantity > 0
                AND b.expiry_date <= %s

            ORDER BY
                b.expiry_date ASC,
                b.batch_id ASC
            """,
            (
                current_store_id,
                end_date
            )
        )

        batches = cursor.fetchall()

        # Create counters for each expiry status.
        summary = {
            "expired": 0,
            "expires_today": 0,
            "critical": 0,
            "warning": 0,
            "upcoming": 0
        }

        # Count the batches in each expiry category.
        for batch in batches:

            status = batch["expiry_status"]

            if status == "EXPIRED":
                summary["expired"] += 1

            elif status == "EXPIRES_TODAY":
                summary["expires_today"] += 1

            elif status == "CRITICAL":
                summary["critical"] += 1

            elif status == "WARNING":
                summary["warning"] += 1

            elif status == "UPCOMING":
                summary["upcoming"] += 1

        return jsonify({
            "alert_period_days": days,
            "start_date": today,
            "end_date": end_date,
            "total_alerts": len(batches),
            "summary": summary,
            "batches": batches
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()

# Return all expired batches that still contain remaining stock.
@inventory_bp.route("/inventory/alerts/expired", methods=["GET"])
@jwt_required()
def get_expired_batches():

    current_store_id = get_jwt_identity()

    today = datetime.now().date()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Get expired batches with remaining quantity.
        cursor.execute(
            """
            SELECT
                b.batch_id,
                b.product_id,
                p.product_name,
                p.barcode,
                b.quantity,
                b.purchase_price,
                b.expiry_date,

                DATEDIFF(
                    CURDATE(),
                    b.expiry_date
                ) AS days_expired

            FROM batches b

            JOIN products p
                ON b.product_id = p.product_id
                AND p.store_id = b.store_id

            WHERE
                b.store_id = %s
                AND b.quantity > 0
                AND b.expiry_date < %s

            ORDER BY
                b.expiry_date ASC,
                b.batch_id ASC
            """,
            (
                current_store_id,
                today
            )
        )

        expired_batches = cursor.fetchall()

        return jsonify({
            "expired_count": len(expired_batches),
            "expired_batches": expired_batches
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()

# Return products that have reached or fallen below their reorder level.
@inventory_bp.route("/inventory/alerts/low-stock", methods=["GET"])
@jwt_required()
def get_low_stock_alerts():

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                p.product_id,
                p.product_name,
                c.category_name,
                COALESCE(i.stock_quantity, 0) AS stock_quantity,
                p.reorder_level,

                CASE
                    WHEN COALESCE(i.stock_quantity, 0) <= 0
                        THEN 'OUT_OF_STOCK'

                    WHEN COALESCE(i.stock_quantity, 0) <= p.reorder_level
                        THEN 'LOW_STOCK'

                    ELSE 'GOOD'
                END AS stock_status

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

        return jsonify({
            "alert_count": len(products),
            "low_stock_products": products
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()