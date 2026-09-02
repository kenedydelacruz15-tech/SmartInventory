from flask import Blueprint, jsonify, request
from database import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity


stock_out_bp = Blueprint("stock_out_bp", __name__)


# Get all stock-out records for the logged-in store.
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
                so.stock_out_id,
                so.product_id,
                p.product_name,
                so.quantity,
                so.reason,
                so.stock_out_date
            FROM stock_out so
            JOIN products p
                ON so.product_id = p.product_id
            WHERE p.store_id = %s
            ORDER BY so.stock_out_date DESC, so.stock_out_id DESC
            """,
            (current_store_id,)
        )

        records = cursor.fetchall()

        return jsonify({
            "stock_out_count": len(records),
            "stock_out_records": records
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

    finally:
        cursor.close()
        db.close()


# Get one stock-out record with its permanently recorded batch allocations.
@stock_out_bp.route("/stock-out/<int:stock_out_id>", methods=["GET"])
@jwt_required()
def get_stock_out_details(stock_out_id):

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # Verify the stock-out record belongs to the logged-in store.
        cursor.execute(
            """
            SELECT
                so.stock_out_id,
                so.product_id,
                p.product_name,
                so.quantity,
                so.reason,
                so.stock_out_date
            FROM stock_out so
            JOIN products p
                ON so.product_id = p.product_id
            WHERE so.stock_out_id = %s
              AND p.store_id = %s
            """,
            (stock_out_id, current_store_id)
        )

        record = cursor.fetchone()

        if not record:
            return jsonify({
                "error": "Stock-out record not found or unauthorized."
            }), 404

        # Get the batches used for this stock-out.
        cursor.execute(
            """
            SELECT
                sob.stock_out_batch_id,
                sob.batch_id,
                sob.quantity_removed,
                b.expiry_date
            FROM stock_out_batches sob
            JOIN batches b
                ON sob.batch_id = b.batch_id
            WHERE sob.stock_out_id = %s
            ORDER BY b.expiry_date ASC, b.batch_id ASC
            """,
            (stock_out_id,)
        )

        record["batch_allocations"] = cursor.fetchall()

        return jsonify(record), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

    finally:
        cursor.close()
        db.close()


# Remove stock using FEFO and permanently record every batch deduction.
@stock_out_bp.route("/stock-out", methods=["POST"])
@jwt_required()
def add_stock_out():

    current_store_id = get_jwt_identity()
    data = request.get_json() or {}

    product_id = data.get("product_id")
    quantity = data.get("quantity")
    reason = data.get("reason", "Stock Out")

    # Validate required request data.
    if product_id is None or quantity is None:
        return jsonify({
            "error": "product_id and quantity are required."
        }), 400

    try:
        product_id = int(product_id)
        quantity = int(quantity)

    except (ValueError, TypeError):
        return jsonify({
            "error": "product_id and quantity must be valid numbers."
        }), 400

    if quantity <= 0:
        return jsonify({
            "error": "Quantity must be greater than 0."
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # Lock the product inventory and verify store ownership.
        cursor.execute(
            """
            SELECT
                p.product_id,
                p.product_name,
                i.stock_quantity
            FROM products p
            JOIN inventory i
                ON p.product_id = i.product_id
            WHERE p.product_id = %s
              AND p.store_id = %s
            FOR UPDATE
            """,
            (product_id, current_store_id)
        )

        product = cursor.fetchone()

        if not product:
            return jsonify({
                "error": "Product not found or unauthorized."
            }), 404

        product_name = product["product_name"]
        current_stock = product["stock_quantity"]

        # Prevent removing more than the available inventory.
        if quantity > current_stock:
            return jsonify({
                "error": "Not enough stock available.",
                "current_stock": current_stock,
                "requested_quantity": quantity
            }), 400

        # Lock available batches and use FEFO ordering.
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

        batch_stock = sum(
            batch["quantity"]
            for batch in batches
        )

        if quantity > batch_stock:
            return jsonify({
                "error": "Not enough batch stock available.",
                "inventory_stock": current_stock,
                "batch_stock": batch_stock
            }), 400

        # Create the main stock-out record.
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

        remaining_quantity = quantity
        batch_allocations = []

        # Deduct from batches and permanently save each allocation.
        for batch in batches:

            if remaining_quantity <= 0:
                break

            batch_id = batch["batch_id"]
            available_quantity = batch["quantity"]

            quantity_removed = min(
                remaining_quantity,
                available_quantity
            )

            # Deduct the quantity from the batch.
            cursor.execute(
                """
                UPDATE batches
                SET quantity = quantity - %s
                WHERE batch_id = %s
                  AND store_id = %s
                  AND quantity >= %s
                """,
                (
                    quantity_removed,
                    batch_id,
                    current_store_id,
                    quantity_removed
                )
            )

            if cursor.rowcount == 0:
                raise Exception(
                    f"Failed to update batch {batch_id}."
                )

            # Permanently record which batch was used.
            cursor.execute(
                """
                INSERT INTO stock_out_batches
                (
                    stock_out_id,
                    batch_id,
                    quantity_removed
                )
                VALUES (%s, %s, %s)
                """,
                (
                    stock_out_id,
                    batch_id,
                    quantity_removed
                )
            )

            batch_allocations.append({
                "batch_id": batch_id,
                "quantity_removed": quantity_removed,
                "expiry_date": batch["expiry_date"]
            })

            remaining_quantity -= quantity_removed

        # Reduce the total inventory.
        cursor.execute(
            """
            UPDATE inventory
            SET stock_quantity = stock_quantity - %s
            WHERE product_id = %s
              AND stock_quantity >= %s
            """,
            (
                quantity,
                product_id,
                quantity
            )
        )

        if cursor.rowcount == 0:
            raise Exception(
                "Failed to update inventory."
            )

        updated_stock = current_stock - quantity

        # Record the transaction in stock movement history.
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
            "product_id": product_id,
            "product_name": product_name,
            "reason": reason,
            "previous_stock": current_stock,
            "quantity_removed": quantity,
            "updated_stock": updated_stock,
            "batch_allocations": batch_allocations
        }), 201

    except Exception as e:

        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()