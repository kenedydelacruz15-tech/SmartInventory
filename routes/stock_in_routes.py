from flask import Blueprint, jsonify, request
from database import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity

stock_in_bp = Blueprint("stock_in_bp", __name__)


@stock_in_bp.route("/stock-in", methods=["GET"])
@jwt_required()
def get_stock_in():
    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                stock_in.stock_in_id,
                products.product_name,
                suppliers.supplier_name,
                stock_in.quantity,
                stock_in.purchase_price,
                stock_in.stock_in_date
            FROM stock_in
            JOIN products
                ON stock_in.product_id = products.product_id
            JOIN suppliers
                ON stock_in.supplier_id = suppliers.supplier_id
            WHERE products.store_id = %s
            ORDER BY stock_in.stock_in_id DESC
            """,
            (current_store_id,)
        )

        stock_in_records = cursor.fetchall()

        return jsonify(stock_in_records), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

    finally:
        cursor.close()
        db.close()


@stock_in_bp.route("/stock-in", methods=["POST"])
@jwt_required()
def add_stock_in():
    current_store_id = get_jwt_identity()
    data = request.get_json()

    product_id = data.get("product_id")
    supplier_id = data.get("supplier_id")
    quantity = data.get("quantity")
    purchase_price = data.get("purchase_price")
    expiry_date = data.get("expiry_date")

    if not product_id or not supplier_id or not quantity or not expiry_date:
        return jsonify({
            "error": "Product, supplier, quantity, and expiry date are required."
        }), 400

    if quantity <= 0:
        return jsonify({
            "error": "Quantity must be greater than 0."
        }), 400

    if purchase_price is None or purchase_price < 0:
        return jsonify({
            "error": "Purchase price must be 0 or greater."
        }), 400

    db = get_db_connection()
    cursor = db.cursor()

    try:
        # Check product ownership
        cursor.execute(
            """
            SELECT product_id
            FROM products
            WHERE product_id = %s
              AND store_id = %s
            """,
            (product_id, current_store_id)
        )

        if not cursor.fetchone():
            return jsonify({
                "error": "Product not found."
            }), 404

        # Check shared supplier
        cursor.execute(
            """
            SELECT supplier_id
            FROM suppliers
            WHERE supplier_id = %s
            """,
            (supplier_id,)
        )

        if not cursor.fetchone():
            return jsonify({
                "error": "Supplier not found."
            }), 404

        # Record stock-in
        cursor.execute(
            """
            INSERT INTO stock_in
            (
                product_id,
                supplier_id,
                quantity,
                purchase_price
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                product_id,
                supplier_id,
                quantity,
                purchase_price
            )
        )

        stock_in_id = cursor.lastrowid

        # Create batch
        cursor.execute(
            """
            INSERT INTO batches
            (
                product_id,
                quantity,
                purchase_price,
                expiry_date,
                store_id
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                product_id,
                quantity,
                purchase_price,
                expiry_date,
                current_store_id
            )
        )

        batch_id = cursor.lastrowid

        # Update inventory
        cursor.execute(
            """
            UPDATE inventory
            SET stock_quantity = stock_quantity + %s
            WHERE product_id = %s
            """,
            (
                quantity,
                product_id
            )
        )

        if cursor.rowcount == 0:
            return jsonify({
                "error": "Inventory record not found."
            }), 404

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
            VALUES (%s, 'STOCK_IN', %s, %s)
            """,
            (
                product_id,
                quantity,
                stock_in_id
            )
        )

        db.commit()

        return jsonify({
            "message": "Stock added successfully.",
            "stock_in_id": stock_in_id,
            "batch_id": batch_id
        }), 201

    except Exception as e:
        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:
        cursor.close()
        db.close()