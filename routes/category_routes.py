from flask import Blueprint, jsonify, request
from database import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity


category_bp = Blueprint("category_bp", __name__)

# GET ALL CATEGORIES FOR THE LOGGED-IN STORE

@category_bp.route("/categories", methods=["GET"])
@jwt_required()
def get_categories():
    """
    Fetches only categories belonging to the logged-in store.
    """

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                category_id,
                category_name,
                store_id
            FROM categories
            WHERE store_id = %s
            ORDER BY category_name ASC
            """,
            (current_store_id,)
        )

        categories = cursor.fetchall()

        return jsonify({
            "category_count": len(categories),
            "categories": categories
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

    finally:
        cursor.close()
        db.close()

# GET ONE CATEGORY

@category_bp.route("/categories/<int:id>", methods=["GET"])
@jwt_required()
def get_category(id):
    """
    Fetches one category only if it belongs to the logged-in store.
    """

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                category_id,
                category_name,
                store_id
            FROM categories
            WHERE category_id = %s
              AND store_id = %s
            """,
            (id, current_store_id)
        )

        category = cursor.fetchone()

        if not category:
            return jsonify({
                "error": "Category not found"
            }), 404

        return jsonify(category), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

    finally:
        cursor.close()
        db.close()

# ADD CATEGORY

@category_bp.route("/categories", methods=["POST"])
@jwt_required()
def add_category():
    """
    Creates a new category for the logged-in store.
    """

    current_store_id = get_jwt_identity()
    data = request.get_json() or {}

    category_name = data.get("category_name", "").strip()

    if not category_name:
        return jsonify({
            "error": "Category name is required"
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # Check if the category already exists for this store
        cursor.execute(
            """
            SELECT category_id
            FROM categories
            WHERE category_name = %s
              AND store_id = %s
            """,
            (category_name, current_store_id)
        )

        existing_category = cursor.fetchone()

        if existing_category:
            return jsonify({
                "error": "Category already exists"
            }), 409

        # Insert new category
        cursor.execute(
            """
            INSERT INTO categories
            (category_name, store_id)
            VALUES (%s, %s)
            """,
            (category_name, current_store_id)
        )

        category_id = cursor.lastrowid

        db.commit()

        # Return the newly created category
        cursor.execute(
            """
            SELECT
                category_id,
                category_name,
                store_id
            FROM categories
            WHERE category_id = %s
              AND store_id = %s
            """,
            (category_id, current_store_id)
        )

        new_category = cursor.fetchone()

        return jsonify({
            "message": "Category added successfully!",
            "category": new_category
        }), 201

    except Exception as e:
        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:
        cursor.close()
        db.close()

# UPDATE CATEGORY

@category_bp.route("/categories/<int:id>", methods=["PUT"])
@jwt_required()
def update_category(id):
    """
    Updates a category only if it belongs to the logged-in store.
    """

    current_store_id = get_jwt_identity()
    data = request.get_json() or {}

    category_name = data.get("category_name", "").strip()

    if not category_name:
        return jsonify({
            "error": "Category name is required"
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # Check category ownership
        cursor.execute(
            """
            SELECT category_id
            FROM categories
            WHERE category_id = %s
              AND store_id = %s
            """,
            (id, current_store_id)
        )

        category = cursor.fetchone()

        if not category:
            return jsonify({
                "error": "Category not found or unauthorized"
            }), 404

        # Prevent duplicate category names in the same store
        cursor.execute(
            """
            SELECT category_id
            FROM categories
            WHERE category_name = %s
              AND store_id = %s
              AND category_id != %s
            """,
            (category_name, current_store_id, id)
        )

        duplicate_category = cursor.fetchone()

        if duplicate_category:
            return jsonify({
                "error": "Another category with this name already exists"
            }), 409

        # Update category
        cursor.execute(
            """
            UPDATE categories
            SET category_name = %s
            WHERE category_id = %s
              AND store_id = %s
            """,
            (category_name, id, current_store_id)
        )

        db.commit()

        # Get updated category
        cursor.execute(
            """
            SELECT
                category_id,
                category_name,
                store_id
            FROM categories
            WHERE category_id = %s
              AND store_id = %s
            """,
            (id, current_store_id)
        )

        updated_category = cursor.fetchone()

        return jsonify({
            "message": "Category updated successfully!",
            "updated_category": updated_category
        }), 200

    except Exception as e:
        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:
        cursor.close()
        db.close()

# DELETE CATEGORY

@category_bp.route("/categories/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_category(id):
    """
    Deletes a category only if it belongs to the logged-in store.
    """

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # Check category ownership first
        cursor.execute(
            """
            SELECT category_id
            FROM categories
            WHERE category_id = %s
              AND store_id = %s
            """,
            (id, current_store_id)
        )

        category = cursor.fetchone()

        if not category:
            return jsonify({
                "error": "Category not found or unauthorized"
            }), 404

        # Check whether products are using this category
        cursor.execute(
            """
            SELECT COUNT(*) AS product_count
            FROM products
            WHERE category_id = %s
              AND store_id = %s
            """,
            (id, current_store_id)
        )

        result = cursor.fetchone()

        if result["product_count"] > 0:
            return jsonify({
                "error": "Cannot delete category because products are still using it",
                "product_count": result["product_count"]
            }), 400

        # Delete category
        cursor.execute(
            """
            DELETE FROM categories
            WHERE category_id = %s
              AND store_id = %s
            """,
            (id, current_store_id)
        )

        db.commit()

        return jsonify({
            "message": "Category deleted successfully!",
            "deleted_category_id": id
        }), 200

    except Exception as e:
        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:
        cursor.close()
        db.close()