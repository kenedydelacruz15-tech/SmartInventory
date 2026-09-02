from flask import Blueprint, jsonify, request
from database import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime


stock_in_bp = Blueprint("stock_in_bp", __name__)


@stock_in_bp.route("/stock-in", methods=["GET"])
@jwt_required()
def get_stock_in():
    # Get stock-in records only for products owned by the logged-in store.

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                stock_in.stock_in_id,
                stock_in.product_id,
                products.product_name,

                stock_in.supplier_id,
                suppliers.supplier_name,

                stock_in.quantity,
                stock_in.purchase_price,
                stock_in.stock_in_date,

                batches.batch_id,
                batches.expiry_date

            FROM stock_in

            JOIN products
                ON stock_in.product_id = products.product_id

            JOIN suppliers
                ON stock_in.supplier_id = suppliers.supplier_id

            LEFT JOIN batches
                ON batches.product_id = stock_in.product_id
                AND batches.store_id = products.store_id
                AND batches.purchase_price = stock_in.purchase_price

            WHERE products.store_id = %s

            ORDER BY stock_in.stock_in_id DESC
            """,
            (current_store_id,)
        )

        stock_in_records = cursor.fetchall()

        return jsonify({
            "stock_in_count": len(stock_in_records),
            "stock_in_records": stock_in_records
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

    finally:
        cursor.close()
        db.close()


@stock_in_bp.route("/stock-in/<int:id>", methods=["GET"])
@jwt_required()
def get_stock_in_record(id):
    # Get one stock-in record only if its product belongs to the logged-in store.

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                stock_in.stock_in_id,
                stock_in.product_id,
                products.product_name,

                stock_in.supplier_id,
                suppliers.supplier_name,

                stock_in.quantity,
                stock_in.purchase_price,
                stock_in.stock_in_date

            FROM stock_in

            JOIN products
                ON stock_in.product_id = products.product_id

            JOIN suppliers
                ON stock_in.supplier_id = suppliers.supplier_id

            WHERE stock_in.stock_in_id = %s
              AND products.store_id = %s
            """,
            (id, current_store_id)
        )

        stock_in_record = cursor.fetchone()

        if not stock_in_record:
            return jsonify({
                "error": "Stock-in record not found"
            }), 404

        return jsonify(stock_in_record), 200

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
    # Add stock for a store-owned product using a shared supplier.

    current_store_id = get_jwt_identity()
    data = request.get_json() or {}

    product_id = data.get("product_id")
    supplier_id = data.get("supplier_id")
    quantity = data.get("quantity")
    purchase_price = data.get("purchase_price")
    expiry_date = data.get("expiry_date")

    if product_id is None:
        return jsonify({
            "error": "Product ID is required."
        }), 400

    if supplier_id is None:
        return jsonify({
            "error": "Supplier ID is required."
        }), 400

    if quantity is None:
        return jsonify({
            "error": "Quantity is required."
        }), 400

    if purchase_price is None:
        return jsonify({
            "error": "Purchase price is required."
        }), 400

    if not expiry_date:
        return jsonify({
            "error": "Expiry date is required."
        }), 400

    # Validate that quantity is a positive number.

    try:
        quantity = int(quantity)
    except (ValueError, TypeError):
        return jsonify({
            "error": "Quantity must be a valid number."
        }), 400

    if quantity <= 0:
        return jsonify({
            "error": "Quantity must be greater than 0."
        }), 400

    # Validate that purchase price is numeric and non-negative.

    try:
        purchase_price = float(purchase_price)
    except (ValueError, TypeError):
        return jsonify({
            "error": "Purchase price must be a valid number."
        }), 400

    if purchase_price < 0:
        return jsonify({
            "error": "Purchase price must be 0 or greater."
        }), 400

    # Validate the expiry date format.

    try:
        expiry_date_object = datetime.strptime(
            expiry_date,
            "%Y-%m-%d"
        ).date()
    except (ValueError, TypeError):
        return jsonify({
            "error": "Expiry date must use YYYY-MM-DD format."
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # Verify that the selected product belongs to the logged-in store.

        cursor.execute(
            """
            SELECT
                product_id,
                product_name
            FROM products
            WHERE product_id = %s
              AND store_id = %s
            """,
            (product_id, current_store_id)
        )

        product = cursor.fetchone()

        if not product:
            return jsonify({
                "error": "Product not found or unauthorized."
            }), 404

        # Verify that the selected supplier exists in the shared supplier list.

        cursor.execute(
            """
            SELECT
                supplier_id,
                supplier_name
            FROM suppliers
            WHERE supplier_id = %s
            """,
            (supplier_id,)
        )

        supplier = cursor.fetchone()

        if not supplier:
            return jsonify({
                "error": "Supplier not found."
            }), 404

        # Verify that the product has an inventory record.

        cursor.execute(
            """
            SELECT
                product_id,
                stock_quantity
            FROM inventory
            WHERE product_id = %s
            """,
            (product_id,)
        )

        inventory = cursor.fetchone()

        if not inventory:
            return jsonify({
                "error": "Inventory record not found for this product."
            }), 404

        # Create the stock-in transaction record.

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

        # Create a separate batch for expiry tracking.

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
                expiry_date_object,
                current_store_id
            )
        )

        batch_id = cursor.lastrowid

        # Increase the total inventory quantity.

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

        # Record the stock-in movement for inventory history.

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

            "stock_in": {
                "stock_in_id": stock_in_id,
                "product_id": product_id,
                "product_name": product["product_name"],
                "supplier_id": supplier_id,
                "supplier_name": supplier["supplier_name"],
                "quantity_added": quantity,
                "purchase_price": purchase_price
            },

            "batch": {
                "batch_id": batch_id,
                "expiry_date": str(expiry_date_object)
            }
        }), 201

    except Exception as e:
        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:
        cursor.close()
        db.close()