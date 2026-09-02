from flask import Blueprint, jsonify, request
from database import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity

stock_out_bp = Blueprint("stock_out_bp", __name__)


@stock_out_bp.route("/stock-out", methods=["GET"])
@jwt_required()
def get_stock_out():
    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                stock_out.stock_out_id,
                products.product_name,
                stock_out.quantity,
                stock_out.reason,
                stock_out.stock_out_date
            FROM stock_out
            JOIN products
                ON stock_out.product_id = products.product_id
            WHERE products.store_id = %s
            ORDER BY stock_out.stock_out_id DESC
            """,
            (current_store_id,)
        )

        records = cursor.fetchall()

        return jsonify(records), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

    finally:
        cursor.close()
        db.close()


@stock_out_bp.route("/stock-out", methods=["POST"])
@jwt_required()
def add_stock_out():
    current_store_id = get_jwt_identity()
    data = request.get_json()

    product_id = data.get("product_id")
    quantity = data.get("quantity")
    reason = data.get("reason", "Stock Out")

    if not product_id or not quantity:
        return jsonify({
            "error": "Product and quantity are required."
        }), 400

    if quantity <= 0:
        return jsonify({
            "error": "Quantity must be greater than 0."
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # Check product ownership and lock inventory
        cursor.execute(
            """
            SELECT
                inventory.product_id,
                inventory.stock_quantity
            FROM inventory
            JOIN products
                ON inventory.product_id = products.product_id
            WHERE inventory.product_id = %s
              AND products.store_id = %s
            FOR UPDATE
            """,
            (product_id, current_store_id)
        )

        inventory = cursor.fetchone()

        if not inventory:
            return jsonify({
                "error": "Product inventory not found."
            }), 404

        current_stock = inventory["stock_quantity"]

        if quantity > current_stock:
            return jsonify({
                "error": "Not enough stock available.",
                "current_stock": current_stock
            }), 400

        # Get batches using FEFO
        cursor.execute(
            """
            SELECT
                batch_id,
                quantity,
                expiry_date
            FROM batches
            WHERE product_id = %s
              AND store_id = %s
              AND quantity > 0
            ORDER BY expiry_date ASC, batch_id ASC
            FOR UPDATE
            """,
            (product_id, current_store_id)
        )

        batches = cursor.fetchall()

        batch_stock = sum(batch["quantity"] for batch in batches)

        if quantity > batch_stock:
            return jsonify({
                "error": "Not enough batch stock available.",
                "batch_stock": batch_stock
            }), 400

        # Record stock-out
        cursor.execute(
            """
            INSERT INTO stock_out
            (
                product_id,
                quantity,
                reason
            )
            VALUES (%s, %s, %s)
            """,
            (
                product_id,
                quantity,
                reason
            )
        )

        stock_out_id = cursor.lastrowid

        remaining = quantity

        for batch in batches:
            if remaining <= 0:
                break

            batch_quantity = batch["quantity"]
            deducted = min(remaining, batch_quantity)

            cursor.execute(
                """
                UPDATE batches
                SET quantity = quantity - %s
                WHERE batch_id = %s
                """,
                (
                    deducted,
                    batch["batch_id"]
                )
            )

            remaining -= deducted

        # Update current inventory
        cursor.execute(
            """
            UPDATE inventory
            SET stock_quantity = stock_quantity - %s
            WHERE product_id = %s
            """,
            (
                quantity,
                product_id
            )
        )

        # Record movement
        cursor.execute(
            """
            INSERT INTO stock_movements
            (
                product_id,
                movement_type,
                quantity,
                reference_id
            )
            VALUES (%s, 'STOCK_OUT', %s, %s)
            """,
            (
                product_id,
                quantity,
                stock_out_id
            )
        )

        db.commit()

        return jsonify({
            "message": "Stock removed successfully.",
            "stock_out_id": stock_out_id,
            "quantity_removed": quantity
        }), 201

    except Exception as e:
        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:
        cursor.close()
        db.close()