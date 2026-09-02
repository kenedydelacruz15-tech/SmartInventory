from flask import Blueprint, jsonify, request
from database import get_db_connection
# Import JWT extensions to extract the logged-in user identity context
from flask_jwt_extended import jwt_required, get_jwt_identity

sales_bp = Blueprint("sales_bp", __name__)


@sales_bp.route("/sales", methods=["GET"])
@jwt_required()
def get_sales():
    """
    Fetches only the sales history invoices belonging to the logged-in store owner.
    """
    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    sql = """
        SELECT *
        FROM sales
        WHERE store_id = %s
        ORDER BY sale_id DESC
    """

    cursor.execute(sql, (current_store_id,))
    sales = cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify(sales)


@sales_bp.route("/sales", methods=["POST"])
@jwt_required()
def add_sale():
    """
    Records a new transaction invoice and subtracts stock quantity values.
    Validates ownership of products and saves the record under the current store_id.
    """
    current_store_id = get_jwt_identity()
    data = request.get_json()

    items = data["items"]

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            "INSERT INTO sales (total_sales, store_id) VALUES (%s, %s)",
            (0, current_store_id)
        )

        sale_id = cursor.lastrowid
        total_sales = 0

        for item in items:
            product_id = item["product_id"]
            quantity = item["quantity"]

            cursor.execute(
                """
                SELECT
                    products.price,
                    inventory.stock_quantity
                FROM products
                JOIN inventory
                    ON products.product_id = inventory.product_id
                WHERE products.product_id = %s AND products.store_id = %s
                """,
                (product_id, current_store_id)
            )

            product = cursor.fetchone()

            if not product:
                raise Exception(f"Product ID {product_id} not found or unauthorized.")

            price = float(product["price"])
            current_stock = product["stock_quantity"]

            # if inventory values are insufficient
            if quantity > current_stock:
                raise Exception(
                    f"Not enough stock for product ID {product_id}. "
                    f"Available: {current_stock}"
                )

            # Calculate transactional subtotal currency values
            subtotal = price * quantity

            # Record line item data rows
            cursor.execute(
                """
                INSERT INTO sale_items
                (sale_id, product_id, quantity, price, subtotal)
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

            # Adjust physical inventory figures downwards
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

            # Record detailed chronological log rows for subsequent smart inventory analytics
            cursor.execute(
                """
                INSERT INTO stock_movements
                (product_id, movement_type, quantity, reference_id)
                VALUES (%s, 'SALE', %s, %s)
                """,
                (
                    product_id,
                    quantity,
                    sale_item_id
                )
            )

            total_sales += subtotal

        # Save cumulative invoice revenue totals to the root transaction document row
        cursor.execute(
            """
            UPDATE sales
            SET total_sales = %s
            WHERE sale_id = %s AND store_id = %s
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
            "total_sales": total_sales
        })

    except Exception as e:
        db.rollback()

        return jsonify({
            "error": str(e)
        }), 400

    finally:
        cursor.close()
        db.close()
