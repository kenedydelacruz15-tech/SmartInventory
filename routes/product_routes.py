from flask import Blueprint, jsonify, request
from database import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity 

product_bp = Blueprint("product_bp", __name__)


@product_bp.route("/products", methods=["GET"])
@jwt_required() # 🔒 Blocks unauthenticated users
def get_products():
    # 🔑 Get the logged-in owner's store_id from the token
    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    sql = """
        SELECT
            products.product_id,
            products.product_name,
            products.price,
            products.category_id,
            categories.category_name,
            inventory.stock_quantity
        FROM products
        LEFT JOIN categories
            ON products.category_id = categories.category_id
        LEFT JOIN inventory
            ON products.product_id = inventory.product_id
        WHERE products.store_id = %s
        ORDER BY products.product_id
    """

    cursor.execute(sql, (current_store_id,))
    products = cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify(products)


@product_bp.route("/products", methods=["POST"])
@jwt_required() # 🔒 Blocks unauthenticated users
def add_product():
    # 🔑 Get the logged-in owner's store_id from the token
    current_store_id = get_jwt_identity()
    
    data = request.get_json()
    product_name = data["product_name"]
    category_id = data["category_id"]
    price = data["price"]

    db = get_db_connection()
    cursor = db.cursor()

    try:
        sql = """
            INSERT INTO products
            (product_name, category_id, price, store_id)
            VALUES (%s, %s, %s, %s)
        """

        cursor.execute(
            sql,
            (product_name, category_id, price, current_store_id)
        )

        product_id = cursor.lastrowid

        inventory_sql = """
            INSERT INTO inventory
            (product_id, stock_quantity)
            VALUES (%s, %s)
        """

        cursor.execute(
            inventory_sql,
            (product_id, 0)
        )

        db.commit()

        return jsonify({
            "message": "Product added successfully!",
            "product_id": product_id
        })

    except Exception as e:
        db.rollback()
        return jsonify({
            "error": str(e)
        }), 500
    finally:
        cursor.close()
        db.close()


@product_bp.route("/products/<int:id>", methods=["PUT"])
@jwt_required() # 🔒 Blocks unauthenticated users
def update_product(id):

    current_store_id = get_jwt_identity()

    data = request.get_json()
    product_name = data["product_name"]
    category_id = data["category_id"]
    price = data["price"]

    db = get_db_connection()
    cursor = db.cursor()

    sql = """
        UPDATE products
        SET
            product_name = %s,
            category_id = %s,
            price = %s
        WHERE product_id = %s AND store_id = %s
    """

    cursor.execute(
        sql,
        (product_name, category_id, price, id, current_store_id)
    )

    db.commit()
    cursor.close()
    db.close()

    return jsonify({
        "message": "Product updated successfully!"
    })


@product_bp.route("/products/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_product(id):
    
    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor()


    cursor.execute(
        "DELETE FROM products WHERE product_id = %s AND store_id = %s",
        (id, current_store_id)
    )

    db.commit()
    cursor.close()
    db.close()

    return jsonify({
        "message": "Product deleted successfully!"
    })
