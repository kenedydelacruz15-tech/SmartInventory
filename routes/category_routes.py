from flask import Blueprint, jsonify, request
from database import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity


category_bp = Blueprint("category_bp", __name__)

# GET ALL ACTIVE CATEGORIES

@category_bp.route("/categories", methods=["GET"])
@jwt_required()
def get_categories():

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
            WHERE
                store_id = %s
                AND deleted_at IS NULL
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


# GET CATEGORY TRASH

@category_bp.route("/categories/trash", methods=["GET"])
@jwt_required()
def get_deleted_categories():

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                category_id,
                category_name,
                store_id,
                deleted_at
            FROM categories
            WHERE
                store_id = %s
                AND deleted_at IS NOT NULL
            ORDER BY deleted_at DESC
            """,
            (current_store_id,)
        )

        categories = cursor.fetchall()

        return jsonify({
            "trash_count": len(categories),
            "deleted_categories": categories
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()

# GET ONE ACTIVE CATEGORY
@category_bp.route("/categories/<int:id>", methods=["GET"])
@jwt_required()
def get_category(id):

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
            WHERE
                category_id = %s
                AND store_id = %s
                AND deleted_at IS NULL
            """,
            (
                id,
                current_store_id
            )
        )

        category = cursor.fetchone()

        if not category:

            return jsonify({
                "error": "Category not found."
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

    current_store_id = get_jwt_identity()

    data = request.get_json() or {}

    category_name = data.get(
        "category_name",
        ""
    ).strip()

    if not category_name:

        return jsonify({
            "error": "Category name is required."
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Check if an ACTIVE category with the same name exists.
        cursor.execute(
            """
            SELECT
                category_id
            FROM categories
            WHERE
                category_name = %s
                AND store_id = %s
                AND deleted_at IS NULL
            """,
            (
                category_name,
                current_store_id
            )
        )

        existing_category = cursor.fetchone()

        if existing_category:

            return jsonify({
                "error": "Category already exists."
            }), 409

        # Check if the category exists in trash.
        cursor.execute(
            """
            SELECT
                category_id,
                deleted_at
            FROM categories
            WHERE
                category_name = %s
                AND store_id = %s
                AND deleted_at IS NOT NULL
            """,
            (
                category_name,
                current_store_id
            )
        )

        deleted_category = cursor.fetchone()

        if deleted_category:

            return jsonify({
                "error": "This category exists in trash. Restore it instead.",
                "category_id": deleted_category["category_id"]
            }), 409

        # Create category.
        cursor.execute(
            """
            INSERT INTO categories
            (
                category_name,
                store_id
            )
            VALUES (%s, %s)
            """,
            (
                category_name,
                current_store_id
            )
        )

        category_id = cursor.lastrowid

        db.commit()

        cursor.execute(
            """
            SELECT
                category_id,
                category_name,
                store_id
            FROM categories
            WHERE category_id = %s
            """,
            (category_id,)
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

    current_store_id = get_jwt_identity()

    data = request.get_json() or {}

    category_name = data.get(
        "category_name",
        ""
    ).strip()

    if not category_name:

        return jsonify({
            "error": "Category name is required."
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Check category ownership and ensure it is active.
        cursor.execute(
            """
            SELECT
                category_id
            FROM categories
            WHERE
                category_id = %s
                AND store_id = %s
                AND deleted_at IS NULL
            """,
            (
                id,
                current_store_id
            )
        )

        category = cursor.fetchone()

        if not category:

            return jsonify({
                "error": "Category not found or is in trash."
            }), 404

        # Check duplicate name among active categories.
        cursor.execute(
            """
            SELECT
                category_id
            FROM categories
            WHERE
                category_name = %s
                AND store_id = %s
                AND category_id != %s
                AND deleted_at IS NULL
            """,
            (
                category_name,
                current_store_id,
                id
            )
        )

        duplicate_category = cursor.fetchone()

        if duplicate_category:

            return jsonify({
                "error": "Another active category with this name already exists."
            }), 409

        # Update category.
        cursor.execute(
            """
            UPDATE categories
            SET category_name = %s
            WHERE
                category_id = %s
                AND store_id = %s
                AND deleted_at IS NULL
            """,
            (
                category_name,
                id,
                current_store_id
            )
        )

        db.commit()

        cursor.execute(
            """
            SELECT
                category_id,
                category_name,
                store_id
            FROM categories
            WHERE
                category_id = %s
                AND store_id = %s
            """,
            (
                id,
                current_store_id
            )
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

# SOFT DELETE CATEGORY
@category_bp.route("/categories/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_category(id):

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Check if category exists and is active.
        cursor.execute(
            """
            SELECT
                category_id,
                category_name
            FROM categories
            WHERE
                category_id = %s
                AND store_id = %s
                AND deleted_at IS NULL
            """,
            (
                id,
                current_store_id
            )
        )

        category = cursor.fetchone()

        if not category:

            return jsonify({
                "error": "Category not found or already deleted."
            }), 404

        # Check products using this category.
        #
        # We allow soft deletion because products remain intact.
        cursor.execute(
            """
            SELECT
                COUNT(*) AS product_count
            FROM products
            WHERE
                category_id = %s
                AND store_id = %s
            """,
            (
                id,
                current_store_id
            )
        )

        result = cursor.fetchone()

        product_count = result["product_count"]

        # Soft delete.
        cursor.execute(
            """
            UPDATE categories
            SET deleted_at = NOW()
            WHERE
                category_id = %s
                AND store_id = %s
                AND deleted_at IS NULL
            """,
            (
                id,
                current_store_id
            )
        )

        db.commit()

        return jsonify({
            "message": "Category moved to trash successfully.",
            "deleted_category_id": id,
            "category_name": category["category_name"],
            "products_using_category": product_count
        }), 200

    except Exception as e:

        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()

# RESTORE CATEGORY FROM TRASH

@category_bp.route("/categories/<int:id>/restore", methods=["PUT"])
@jwt_required()
def restore_category(id):

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Find the deleted category.
        cursor.execute(
            """
            SELECT
                category_id,
                category_name
            FROM categories
            WHERE
                category_id = %s
                AND store_id = %s
                AND deleted_at IS NOT NULL
            """,
            (
                id,
                current_store_id
            )
        )

        deleted_category = cursor.fetchone()

        if not deleted_category:

            return jsonify({
                "error": "Deleted category not found in trash."
            }), 404

        # Check if another active category has the same name.
        cursor.execute(
            """
            SELECT
                category_id
            FROM categories
            WHERE
                category_name = %s
                AND store_id = %s
                AND deleted_at IS NULL
            """,
            (
                deleted_category["category_name"],
                current_store_id
            )
        )

        duplicate_category = cursor.fetchone()

        if duplicate_category:

            return jsonify({
                "error": (
                    "Cannot restore category because an active "
                    "category with the same name already exists."
                )
            }), 409

        # Restore category.
        cursor.execute(
            """
            UPDATE categories
            SET deleted_at = NULL
            WHERE
                category_id = %s
                AND store_id = %s
                AND deleted_at IS NOT NULL
            """,
            (
                id,
                current_store_id
            )
        )

        db.commit()

        return jsonify({
            "message": "Category restored successfully!",
            "restored_category_id": id
        }), 200

    except Exception as e:

        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()

# PERMANENTLY DELETE CATEGORY

@category_bp.route(
    "/categories/<int:id>/permanent",
    methods=["DELETE"]
)
@jwt_required()
def permanently_delete_category(id):

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Only categories already in trash can be permanently deleted.
        cursor.execute(
            """
            SELECT
                category_id,
                category_name
            FROM categories
            WHERE
                category_id = %s
                AND store_id = %s
                AND deleted_at IS NOT NULL
            """,
            (
                id,
                current_store_id
            )
        )

        category = cursor.fetchone()

        if not category:

            return jsonify({
                "error": (
                    "Category not found in trash. "
                    "Only soft-deleted categories can be permanently deleted."
                )
            }), 404

        # Safety check:
        # Do not permanently delete if products still reference this category.
        cursor.execute(
            """
            SELECT
                COUNT(*) AS product_count
            FROM products
            WHERE
                category_id = %s
                AND store_id = %s
            """,
            (
                id,
                current_store_id
            )
        )

        result = cursor.fetchone()

        if result["product_count"] > 0:

            return jsonify({
                "error": (
                    "Cannot permanently delete this category because "
                    "products are still using it."
                ),
                "product_count": result["product_count"]
            }), 400

        # Permanently delete.
        cursor.execute(
            """
            DELETE FROM categories
            WHERE
                category_id = %s
                AND store_id = %s
                AND deleted_at IS NOT NULL
            """,
            (
                id,
                current_store_id
            )
        )

        db.commit()

        return jsonify({
            "message": "Category permanently deleted successfully.",
            "permanently_deleted_category_id": id,
            "category_name": category["category_name"]
        }), 200

    except Exception as e:

        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()