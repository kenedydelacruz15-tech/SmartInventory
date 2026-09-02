from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import get_db_connection
from datetime import datetime


sales_bp = Blueprint("sales_bp", __name__)


# Get all sales belonging to the logged-in store.
@sales_bp.route("/sales", methods=["GET"])
@jwt_required()
def get_sales():

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                sale_id,
                total_sales,
                sale_date
            FROM sales
            WHERE store_id = %s
            ORDER BY sale_id DESC
            """,
            (current_store_id,)
        )

        sales = cursor.fetchall()

        return jsonify({
            "sale_count": len(sales),
            "sales": sales
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

    finally:
        cursor.close()
        db.close()


# Get one sale with its products and batch allocations.
@sales_bp.route("/sales/<int:sale_id>", methods=["GET"])
@jwt_required()
def get_sale_details(sale_id):

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # Check that the sale belongs to the logged-in store.
        cursor.execute(
            """
            SELECT
                sale_id,
                total_sales,
                sale_date
            FROM sales
            WHERE sale_id = %s
              AND store_id = %s
            """,
            (sale_id, current_store_id)
        )

        sale = cursor.fetchone()

        if not sale:
            return jsonify({
                "error": "Sale not found or unauthorized"
            }), 404

        # Get all items included in the sale.
        cursor.execute(
            """
            SELECT
                si.sale_item_id,
                si.product_id,
                p.product_name,
                si.quantity,
                si.price,
                si.subtotal
            FROM sale_items si

            JOIN products p
                ON si.product_id = p.product_id

            WHERE si.sale_id = %s
              AND p.store_id = %s

            ORDER BY si.sale_item_id ASC
            """,
            (sale_id, current_store_id)
        )

        sale_items = cursor.fetchall()

        # Get the batches used for every sale item.
        for item in sale_items:

            cursor.execute(
                """
                SELECT
                    sib.sale_item_batch_id,
                    sib.batch_id,
                    sib.quantity AS batch_quantity,
                    b.expiry_date,
                    b.purchase_price

                FROM sale_item_batches sib

                JOIN batches b
                    ON sib.batch_id = b.batch_id

                WHERE sib.sale_item_id = %s
                  AND b.store_id = %s

                ORDER BY b.expiry_date ASC
                """,
                (
                    item["sale_item_id"],
                    current_store_id
                )
            )

            item["batch_allocations"] = cursor.fetchall()

        sale["items"] = sale_items

        return jsonify(sale), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

    finally:
        cursor.close()
        db.close()


# Create a sale and allocate sold quantities to batches using FEFO.
@sales_bp.route("/sales", methods=["POST"])
@jwt_required()
def add_sale():

    current_store_id = get_jwt_identity()
    data = request.get_json() or {}

    items = data.get("items")

    if not items or not isinstance(items, list):
        return jsonify({
            "error": "Items are required and must be a list."
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # Create the main sale record before processing products.
        cursor.execute(
            """
            INSERT INTO sales
            (
                total_sales,
                store_id
            )
            VALUES (%s, %s)
            """,
            (
                0,
                current_store_id
            )
        )

        sale_id = cursor.lastrowid
        total_sales = 0

        today = datetime.now().date()

        for item in items:

            product_id = item.get("product_id")
            quantity = item.get("quantity")

            # Validate the required product and quantity.
            if product_id is None or quantity is None:
                raise Exception(
                    "Each item must have product_id and quantity."
                )

            try:
                product_id = int(product_id)
                quantity = int(quantity)

            except (ValueError, TypeError):
                raise Exception(
                    "Product ID and quantity must be valid numbers."
                )

            if quantity <= 0:
                raise Exception(
                    f"Quantity must be greater than zero for product ID {product_id}."
                )

            # Get the product and verify that it belongs to this store.
            cursor.execute(
                """
                SELECT
                    p.product_id,
                    p.product_name,
                    p.price,
                    COALESCE(i.stock_quantity, 0) AS stock_quantity

                FROM products p

                LEFT JOIN inventory i
                    ON p.product_id = i.product_id

                WHERE p.product_id = %s
                  AND p.store_id = %s
                """,
                (
                    product_id,
                    current_store_id
                )
            )

            product = cursor.fetchone()

            if not product:
                raise Exception(
                    f"Product ID {product_id} not found or unauthorized."
                )

            current_stock = product["stock_quantity"]

            # Check that total inventory has enough stock.
            if quantity > current_stock:
                raise Exception(
                    f"Not enough stock for {product['product_name']}. "
                    f"Available: {current_stock}"
                )

            # Get available batches using FEFO and exclude expired stock.
            cursor.execute(
                """
                SELECT
                    batch_id,
                    quantity,
                    purchase_price,
                    expiry_date

                FROM batches

                WHERE product_id = %s
                  AND store_id = %s
                  AND quantity > 0
                  AND expiry_date >= %s

                ORDER BY
                    expiry_date ASC,
                    batch_id ASC
                """,
                (
                    product_id,
                    current_store_id,
                    today
                )
            )

            batches = cursor.fetchall()

            # Calculate available stock from valid non-expired batches.
            available_batch_quantity = sum(
                batch["quantity"]
                for batch in batches
            )

            if quantity > available_batch_quantity:
                raise Exception(
                    f"Not enough non-expired batch stock for "
                    f"{product['product_name']}. "
                    f"Available: {available_batch_quantity}"
                )

            price = float(product["price"])
            subtotal = price * quantity

            # Save the product as a sale item.
            cursor.execute(
                """
                INSERT INTO sale_items
                (
                    sale_id,
                    product_id,
                    quantity,
                    price,
                    subtotal
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    sale_id,
                    product_id,
                    quantity,
                    price,
                    subtotal
                )
            )

            sale_item_id = cursor.lastrowid
            remaining_quantity = quantity

            # Deduct from the earliest-expiring batches first.
            for batch in batches:

                if remaining_quantity <= 0:
                    break

                batch_id = batch["batch_id"]
                batch_quantity = batch["quantity"]

                quantity_to_deduct = min(
                    remaining_quantity,
                    batch_quantity
                )

                # Reduce the quantity remaining in this batch.
                cursor.execute(
                    """
                    UPDATE batches
                    SET quantity = quantity - %s
                    WHERE batch_id = %s
                      AND store_id = %s
                      AND quantity >= %s
                    """,
                    (
                        quantity_to_deduct,
                        batch_id,
                        current_store_id,
                        quantity_to_deduct
                    )
                )

                if cursor.rowcount == 0:
                    raise Exception(
                        f"Batch {batch_id} could not be updated."
                    )

                # Record exactly how much was taken from this batch.
                cursor.execute(
                    """
                    INSERT INTO sale_item_batches
                    (
                        sale_item_id,
                        batch_id,
                        quantity
                    )
                    VALUES (%s, %s, %s)
                    """,
                    (
                        sale_item_id,
                        batch_id,
                        quantity_to_deduct
                    )
                )

                remaining_quantity -= quantity_to_deduct

            # Reduce the overall inventory quantity.
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
                    f"Inventory update failed for "
                    f"{product['product_name']}."
                )

            # Record the sale as a stock movement.
            cursor.execute(
                """
                INSERT INTO stock_movements
                (
                    product_id,
                    movement_type,
                    quantity,
                    reference_id
                )
                VALUES (%s, 'SALE', %s, %s)
                """,
                (
                    product_id,
                    quantity,
                    sale_item_id
                )
            )

            total_sales += subtotal

        # Save the final total for the complete sale.
        cursor.execute(
            """
            UPDATE sales
            SET total_sales = %s
            WHERE sale_id = %s
              AND store_id = %s
            """,
            (
                total_sales,
                sale_id,
                current_store_id
            )
        )

        db.commit()

        return jsonify({
            "message": "Sale recorded successfully!",
            "sale_id": sale_id,
            "total_sales": round(total_sales, 2)
        }), 201

    except Exception as e:

        db.rollback()

        return jsonify({
            "error": str(e)
        }), 400

    finally:
        cursor.close()
        db.close()