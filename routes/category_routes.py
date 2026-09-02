from flask import Blueprint, jsonify, request
from database import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity

category_bp = Blueprint("category_bp", __name__)


@category_bp.route("/categories", methods=["GET"])
@jwt_required()
def get_categories():
    """
    Fetches only the categories belonging to the logged-in store owner.
    """
    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Filter categories table by store_id constraint
    cursor.execute("SELECT * FROM categories WHERE store_id = %s", (current_store_id,))
    categories = cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify(categories)


@category_bp.route("/categories", methods=["POST"])
@jwt_required()
def add_category():
    """
    Creates a new product category mapped to the active store account.
    """
    current_store_id = get_jwt_identity()
    data = request.get_json()

    db = get_db_connection()
    cursor = db.cursor()

    sql = "INSERT INTO categories (category_name, store_id) VALUES (%s, %s)"

    cursor.execute(
        sql,
        (data["category_name"], current_store_id)
    )

    db.commit()

    cursor.close()
    db.close()

    return jsonify({
        "message": "Category added successfully!"
    })


@category_bp.route("/categories/<int:id>", methods=["PUT"])
@jwt_required()
def update_category(id):
    """
    Updates a specific category, ensuring it belongs to the logged-in store.
    """
    current_store_id = get_jwt_identity()
    data = request.get_json()

    db = get_db_connection()
    cursor = db.cursor()

    sql = """
        UPDATE categories
        SET category_name = %s
        WHERE category_id = %s AND store_id = %s
    """

    cursor.execute(
        sql,
        (data["category_name"], id, current_store_id)
    )

    db.commit()

    cursor.close()
    db.close()

    return jsonify({
        "message": "Category updated successfully!"
    })


@category_bp.route("/categories/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_category(id):
    """
    Deletes a specific category, preventing cross-tenant data operations.
    """
    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM categories WHERE category_id = %s AND store_id = %s",
        (id, current_store_id)
    )

    db.commit()

    cursor.close()
    db.close()

    return jsonify({
        "message": "Category deleted successfully!"
    })
