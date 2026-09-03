from flask import Blueprint, jsonify, request
from database import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity


product_bp = Blueprint("product_bp", __name__)


# Get all products belonging to the logged-in store.
@product_bp.route("/products", methods=["GET"])
@jwt_required()
def get_products():

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                p.product_id,
                p.product_name,
                p.barcode,
                p.price,
                p.reorder_level,
                p.category_id,
                c.category_name,
                COALESCE(i.stock_quantity, 0) AS stock_quantity,

                CASE
                    WHEN COALESCE(i.stock_quantity, 0) <= 0
                        THEN 'OUT_OF_STOCK'

                    WHEN COALESCE(i.stock_quantity, 0) <= p.reorder_level
                        THEN 'LOW_STOCK'

                    ELSE 'IN_STOCK'
                END AS stock_status

            FROM products p

            LEFT JOIN categories c
                ON p.category_id = c.category_id
                AND c.store_id = p.store_id

            LEFT JOIN inventory i
                ON p.product_id = i.product_id

            WHERE p.store_id = %s
                AND p.deleted_at IS NULL

            ORDER BY p.product_id ASC
            """,
            (current_store_id,)
        )

        products = cursor.fetchall()

        return jsonify({
            "product_count": len(products),
            "products": products
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()


# Get one product using its barcode.
@product_bp.route("/products/barcode/<string:barcode>", methods=["GET"])
@jwt_required()
def get_product_by_barcode(barcode):

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                p.product_id,
                p.product_name,
                p.barcode,
                p.price,
                p.reorder_level,
                p.category_id,
                c.category_name,
                COALESCE(i.stock_quantity, 0) AS stock_quantity,

                CASE
                    WHEN COALESCE(i.stock_quantity, 0) <= 0
                        THEN 'OUT_OF_STOCK'

                    WHEN COALESCE(i.stock_quantity, 0) <= p.reorder_level
                        THEN 'LOW_STOCK'

                    ELSE 'IN_STOCK'
                END AS stock_status

            FROM products p

            LEFT JOIN categories c
                ON p.category_id = c.category_id
                AND c.store_id = p.store_id

            LEFT JOIN inventory i
                ON p.product_id = i.product_id

            WHERE
                p.barcode = %s
                AND p.store_id = %s
                AND p.deleted_at IS NULL
            """,
            (
                barcode,
                current_store_id
            )
        )

        product = cursor.fetchone()

        if not product:

            return jsonify({
                "error": "Product not found for this barcode."
            }), 404

        return jsonify(product), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()


# Get one specific product by ID.
@product_bp.route("/products/<int:id>", methods=["GET"])
@jwt_required()
def get_product(id):

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                p.product_id,
                p.product_name,
                p.barcode,
                p.price,
                p.reorder_level,
                p.category_id,
                c.category_name,
                COALESCE(i.stock_quantity, 0) AS stock_quantity,

                CASE
                    WHEN COALESCE(i.stock_quantity, 0) <= 0
                        THEN 'OUT_OF_STOCK'

                    WHEN COALESCE(i.stock_quantity, 0) <= p.reorder_level
                        THEN 'LOW_STOCK'

                    ELSE 'IN_STOCK'
                END AS stock_status

            FROM products p

            LEFT JOIN categories c
                ON p.category_id = c.category_id
                AND c.store_id = p.store_id

            LEFT JOIN inventory i
                ON p.product_id = i.product_id

            WHERE
                p.product_id = %s
                AND p.store_id = %s
                AND p.deleted_at IS NULL
            """,
            (
                id,
                current_store_id
            )
        )

        product = cursor.fetchone()

        if not product:

            return jsonify({
                "error": "Product not found."
            }), 404

        return jsonify(product), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()


# Add a new product and automatically create its inventory record.
@product_bp.route("/products", methods=["POST"])
@jwt_required()
def add_product():

    current_store_id = get_jwt_identity()

    data = request.get_json() or {}

    product_name = data.get("product_name")
    category_id = data.get("category_id")
    price = data.get("price")
    barcode = data.get("barcode")
    reorder_level = data.get("reorder_level", 10)

    if not product_name or category_id is None or price is None:

        return jsonify({
            "error": "Product name, category, and price are required."
        }), 400

    try:

        price = float(price)

        if price < 0:

            return jsonify({
                "error": "Price cannot be negative."
            }), 400

        reorder_level = int(reorder_level)

        if reorder_level < 0:

            return jsonify({
                "error": "Reorder level cannot be negative."
            }), 400

    except (ValueError, TypeError):

        return jsonify({
            "error": "Price and reorder level must be valid numbers."
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Check that the category belongs to the logged-in store.
        cursor.execute(
            """
            SELECT category_id
            FROM categories
            WHERE category_id = %s
              AND store_id = %s
            """,
            (
                category_id,
                current_store_id
            )
        )

        if not cursor.fetchone():

            return jsonify({
                "error": "Category not found or unauthorized."
            }), 404

        # Check whether the barcode already exists in this store.
        if barcode:

            cursor.execute(
                """
                SELECT product_id
                FROM products
                WHERE barcode = %s
                  AND store_id = %s
                """,
                (
                    barcode,
                    current_store_id
                )
            )

            if cursor.fetchone():

                return jsonify({
                    "error": "Barcode already exists."
                }), 409

        # Insert the new product.
        cursor.execute(
            """
            INSERT INTO products
            (
                product_name,
                category_id,
                price,
                barcode,
                reorder_level,
                store_id
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                product_name,
                category_id,
                price,
                barcode,
                reorder_level,
                current_store_id
            )
        )

        product_id = cursor.lastrowid

        # Automatically create the inventory record.
        cursor.execute(
            """
            INSERT INTO inventory
            (
                product_id,
                stock_quantity
            )
            VALUES (%s, %s)
            """,
            (
                product_id,
                0
            )
        )

        db.commit()

        # Get the newly created product.
        cursor.execute(
            """
            SELECT
                p.product_id,
                p.product_name,
                p.barcode,
                p.price,
                p.reorder_level,
                p.category_id,
                c.category_name,
                COALESCE(i.stock_quantity, 0) AS stock_quantity

            FROM products p

            LEFT JOIN categories c
                ON p.category_id = c.category_id
                AND c.store_id = p.store_id

            LEFT JOIN inventory i
                ON p.product_id = i.product_id

            WHERE
                p.product_id = %s
                AND p.store_id = %s
            """,
            (
                product_id,
                current_store_id
            )
        )

        new_product = cursor.fetchone()

        return jsonify({
            "message": "Product added successfully!",
            "product": new_product
        }), 201

    except Exception as e:

        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()


# Fully update a product.
@product_bp.route("/products/<int:id>", methods=["PUT"])
@jwt_required()
def update_product(id):

    current_store_id = get_jwt_identity()

    data = request.get_json() or {}

    product_name = data.get("product_name")
    category_id = data.get("category_id")
    price = data.get("price")
    barcode = data.get("barcode")
    reorder_level = data.get("reorder_level")

    if not product_name or category_id is None or price is None:

        return jsonify({
            "error": "Product name, category, and price are required."
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Check that the product belongs to the logged-in store.
        cursor.execute(
            """
            SELECT
                product_id,
                reorder_level
            FROM products
            WHERE product_id = %s
              AND store_id = %s
              AND deleted_at IS NULL
            """,
            (
                id,
                current_store_id
            )
        )

        existing_product = cursor.fetchone()

        if not existing_product:

            return jsonify({
                "error": "Product not found or unauthorized."
            }), 404

        try:

            price = float(price)

            if price < 0:

                return jsonify({
                    "error": "Price cannot be negative."
                }), 400

            if reorder_level is None:

                reorder_level = existing_product["reorder_level"]

            reorder_level = int(reorder_level)

            if reorder_level < 0:

                return jsonify({
                    "error": "Reorder level cannot be negative."
                }), 400

        except (ValueError, TypeError):

            return jsonify({
                "error": "Price and reorder level must be valid numbers."
            }), 400

        # Check that the category belongs to the logged-in store.
        cursor.execute(
            """
            SELECT category_id
            FROM categories
            WHERE category_id = %s
              AND store_id = %s
            """,
            (
                category_id,
                current_store_id
            )
        )

        if not cursor.fetchone():

            return jsonify({
                "error": "Category not found or unauthorized."
            }), 404

        # Check barcode uniqueness within the logged-in store.
        if barcode:

            cursor.execute(
                """
                SELECT product_id
                FROM products
                WHERE barcode = %s
                  AND store_id = %s
                  AND product_id != %s
                """,
                (
                    barcode,
                    current_store_id,
                    id
                )
            )

            if cursor.fetchone():

                return jsonify({
                    "error": "Barcode already exists."
                }), 409

        # Update the product.
        cursor.execute(
            """
            UPDATE products
            SET
                product_name = %s,
                category_id = %s,
                price = %s,
                barcode = %s,
                reorder_level = %s
            WHERE
                product_id = %s
                AND store_id = %s
            """,
            (
                product_name,
                category_id,
                price,
                barcode,
                reorder_level,
                id,
                current_store_id
            )
        )

        db.commit()

        # Get the updated product.
        cursor.execute(
            """
            SELECT
                p.product_id,
                p.product_name,
                p.barcode,
                p.price,
                p.reorder_level,
                p.category_id,
                c.category_name,
                COALESCE(i.stock_quantity, 0) AS stock_quantity

            FROM products p

            LEFT JOIN categories c
                ON p.category_id = c.category_id
                AND c.store_id = p.store_id

            LEFT JOIN inventory i
                ON p.product_id = i.product_id

            WHERE
                p.product_id = %s
                AND p.store_id = %s
            """,
            (
                id,
                current_store_id
            )
        )

        updated_product = cursor.fetchone()

        return jsonify({
            "message": "Product updated successfully!",
            "updated_product": updated_product
        }), 200

    except Exception as e:

        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()


# Partially update specific product fields.
@product_bp.route("/products/<int:id>", methods=["PATCH"])
@jwt_required()
def partial_update_product(id):

    current_store_id = get_jwt_identity()

    data = request.get_json() or {}

    allowed_fields = [
        "product_name",
        "category_id",
        "price",
        "barcode",
        "reorder_level"
    ]

    fields_to_update = {
        field: data[field]
        for field in allowed_fields
        if field in data
    }

    if not fields_to_update:

        return jsonify({
            "error": "No valid fields provided for update."
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Check that the product belongs to the logged-in store.
        cursor.execute(
            """
            SELECT product_id
            FROM products
            WHERE product_id = %s
              AND store_id = %s
              AND deleted_at IS NULL
            """,
            (
                id,
                current_store_id
            )
        )

        if not cursor.fetchone():

            return jsonify({
                "error": "Product not found or unauthorized."
            }), 404

        # Validate product name.
        if "product_name" in fields_to_update:

            product_name = str(
                fields_to_update["product_name"]
            ).strip()

            if not product_name:

                return jsonify({
                    "error": "Product name cannot be empty."
                }), 400

            fields_to_update["product_name"] = product_name

        # Validate price.
        if "price" in fields_to_update:

            try:

                price = float(fields_to_update["price"])

                if price < 0:

                    return jsonify({
                        "error": "Price cannot be negative."
                    }), 400

                fields_to_update["price"] = price

            except (ValueError, TypeError):

                return jsonify({
                    "error": "Price must be a valid number."
                }), 400

        # Validate reorder level.
        if "reorder_level" in fields_to_update:

            try:

                reorder_level = int(
                    fields_to_update["reorder_level"]
                )

                if reorder_level < 0:

                    return jsonify({
                        "error": "Reorder level cannot be negative."
                    }), 400

                fields_to_update["reorder_level"] = reorder_level

            except (ValueError, TypeError):

                return jsonify({
                    "error": "Reorder level must be a valid number."
                }), 400

        # Check category ownership.
        if "category_id" in fields_to_update:

            cursor.execute(
                """
                SELECT category_id
                FROM categories
                WHERE category_id = %s
                  AND store_id = %s
                """,
                (
                    fields_to_update["category_id"],
                    current_store_id
                )
            )

            if not cursor.fetchone():

                return jsonify({
                    "error": "Category not found or unauthorized."
                }), 404

        # Check barcode uniqueness within the store.
        if "barcode" in fields_to_update:

            barcode = fields_to_update["barcode"]

            if barcode:

                cursor.execute(
                    """
                    SELECT product_id
                    FROM products
                    WHERE barcode = %s
                      AND store_id = %s
                      AND product_id != %s
                    """,
                    (
                        barcode,
                        current_store_id,
                        id
                    )
                )

                if cursor.fetchone():

                    return jsonify({
                        "error": "Barcode already exists."
                    }), 409

        # Build the safe dynamic update query.
        update_parts = []
        values = []

        for field, value in fields_to_update.items():

            update_parts.append(f"{field} = %s")
            values.append(value)

        sql = f"""
            UPDATE products
            SET {", ".join(update_parts)}
            WHERE
                product_id = %s
                AND store_id = %s
        """

        values.append(id)
        values.append(current_store_id)

        cursor.execute(
            sql,
            tuple(values)
        )

        db.commit()

        # Get the complete updated product.
        cursor.execute(
            """
            SELECT
                p.product_id,
                p.product_name,
                p.barcode,
                p.price,
                p.reorder_level,
                p.category_id,
                c.category_name,
                COALESCE(i.stock_quantity, 0) AS stock_quantity,

                CASE
                    WHEN COALESCE(i.stock_quantity, 0) <= 0
                        THEN 'OUT_OF_STOCK'

                    WHEN COALESCE(i.stock_quantity, 0) <= p.reorder_level
                        THEN 'LOW_STOCK'

                    ELSE 'IN_STOCK'
                END AS stock_status

            FROM products p

            LEFT JOIN categories c
                ON p.category_id = c.category_id
                AND c.store_id = p.store_id

            LEFT JOIN inventory i
                ON p.product_id = i.product_id

            WHERE
                p.product_id = %s
                AND p.store_id = %s
            """,
            (
                id,
                current_store_id
            )
        )

        updated_product = cursor.fetchone()

        return jsonify({
            "message": "Product updated successfully!",
            "updated_fields": list(fields_to_update.keys()),
            "updated_product": updated_product
        }), 200

    except Exception as e:

        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()


# Soft delete a product.
@product_bp.route("/products/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_product(id):

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Check that the product exists and belongs to the store.
        cursor.execute(
            """
            SELECT
                product_id,
                product_name
            FROM products
            WHERE
                product_id = %s
                AND store_id = %s
                AND deleted_at IS NULL
            """,
            (
                id,
                current_store_id
            )
        )

        product = cursor.fetchone()

        if not product:

            return jsonify({
                "error": "Product not found or already deleted."
            }), 404

        # Soft delete instead of permanently deleting.
        cursor.execute(
            """
            UPDATE products
            SET
                deleted_at = NOW()
            WHERE
                product_id = %s
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
            "message": "Product moved to trash successfully.",
            "product_id": id,
            "product_name": product["product_name"]
        }), 200

    except Exception as e:

        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()

# Search products by product name or barcode.
@product_bp.route("/products/search", methods=["GET"])
@jwt_required()
def search_products():

    current_store_id = get_jwt_identity()

    search_query = request.args.get(
        "q",
        ""
    ).strip()

    if not search_query:

        return jsonify({
            "error": "Search query is required."
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        search_value = f"%{search_query}%"

        cursor.execute(
            """
            SELECT
                p.product_id,
                p.product_name,
                p.barcode,
                p.price,
                p.reorder_level,
                p.category_id,
                c.category_name,
                COALESCE(i.stock_quantity, 0) AS stock_quantity,

                CASE
                    WHEN COALESCE(i.stock_quantity, 0) <= 0
                        THEN 'OUT_OF_STOCK'

                    WHEN COALESCE(i.stock_quantity, 0) <= p.reorder_level
                        THEN 'LOW_STOCK'

                    ELSE 'IN_STOCK'
                END AS stock_status

            FROM products p

            LEFT JOIN categories c
                ON p.category_id = c.category_id
                AND c.store_id = p.store_id

            LEFT JOIN inventory i
                ON p.product_id = i.product_id

            WHERE
                p.store_id = %s
                AND p.deleted_at IS NULL
                AND (
                    p.product_name LIKE %s
                    OR p.barcode LIKE %s
                )

            ORDER BY p.product_name ASC
            """,
            (
                current_store_id,
                search_value,
                search_value
            )
        )

        products = cursor.fetchall()

        return jsonify({
            "product_count": len(products),
            "products": products
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()

# Get all deleted products belonging to the logged-in store.
@product_bp.route("/products/trash", methods=["GET"])
@jwt_required()
def get_deleted_products():

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                p.product_id,
                p.product_name,
                p.barcode,
                p.price,
                p.reorder_level,
                p.category_id,
                c.category_name,
                p.deleted_at,
                COALESCE(i.stock_quantity, 0) AS stock_quantity

            FROM products p

            LEFT JOIN categories c
                ON p.category_id = c.category_id
                AND c.store_id = p.store_id

            LEFT JOIN inventory i
                ON p.product_id = i.product_id

            WHERE
                p.store_id = %s
                AND p.deleted_at IS NOT NULL

            ORDER BY
                p.deleted_at DESC
            """,
            (current_store_id,)
        )

        products = cursor.fetchall()

        return jsonify({
            "trash_count": len(products),
            "deleted_products": products
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()

# Restore a soft-deleted product.
@product_bp.route("/products/<int:id>/restore", methods=["PUT"])
@jwt_required()
def restore_product(id):

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Check whether the deleted product exists.
        cursor.execute(
            """
            SELECT
                product_id,
                product_name
            FROM products
            WHERE
                product_id = %s
                AND store_id = %s
                AND deleted_at IS NOT NULL
            """,
            (
                id,
                current_store_id
            )
        )

        product = cursor.fetchone()

        if not product:

            return jsonify({
                "error": "Deleted product not found."
            }), 404

        # Restore the product.
        cursor.execute(
            """
            UPDATE products
            SET
                deleted_at = NULL
            WHERE
                product_id = %s
                AND store_id = %s
            """,
            (
                id,
                current_store_id
            )
        )

        db.commit()

        return jsonify({
            "message": "Product restored successfully.",
            "product_id": id,
            "product_name": product["product_name"]
        }), 200

    except Exception as e:

        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()

# Get one deleted product from trash.
@product_bp.route("/products/trash/<int:id>", methods=["GET"])
@jwt_required()
def get_deleted_product(id):

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                p.product_id,
                p.product_name,
                p.barcode,
                p.price,
                p.reorder_level,
                p.category_id,
                c.category_name,
                p.deleted_at,
                COALESCE(i.stock_quantity, 0) AS stock_quantity

            FROM products p

            LEFT JOIN categories c
                ON p.category_id = c.category_id
                AND c.store_id = p.store_id

            LEFT JOIN inventory i
                ON p.product_id = i.product_id

            WHERE
                p.product_id = %s
                AND p.store_id = %s
                AND p.deleted_at IS NOT NULL
            """,
            (
                id,
                current_store_id
            )
        )

        product = cursor.fetchone()

        if not product:

            return jsonify({
                "error": "Deleted product not found."
            }), 404

        return jsonify(product), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()

# Permanently delete a product from trash.
@product_bp.route("/products/trash/<int:id>", methods=["DELETE"])
@jwt_required()
def permanently_delete_product(id):

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Check that the product exists, belongs to the store,
        # and is already in the trash.
        cursor.execute(
            """
            SELECT
                product_id,
                product_name
            FROM products
            WHERE
                product_id = %s
                AND store_id = %s
                AND deleted_at IS NOT NULL
            """,
            (
                id,
                current_store_id
            )
        )

        product = cursor.fetchone()

        if not product:

            return jsonify({
                "error": "Deleted product not found."
            }), 404

        # Check for stock movement history.
        cursor.execute(
            """
            SELECT COUNT(*) AS movement_count
            FROM stock_movements
            WHERE product_id = %s
            """,
            (id,)
        )

        movement_count = cursor.fetchone()["movement_count"]

        # Check for sales history.
        cursor.execute(
            """
            SELECT COUNT(*) AS sale_count
            FROM sale_items
            WHERE product_id = %s
            """,
            (id,)
        )

        sale_count = cursor.fetchone()["sale_count"]

        # Check for stock-in history.
        cursor.execute(
            """
            SELECT COUNT(*) AS stock_in_count
            FROM stock_in
            WHERE product_id = %s
            """,
            (id,)
        )

        stock_in_count = cursor.fetchone()["stock_in_count"]

        # Check for stock-out history.
        cursor.execute(
            """
            SELECT COUNT(*) AS stock_out_count
            FROM stock_out
            WHERE product_id = %s
            """,
            (id,)
        )

        stock_out_count = cursor.fetchone()["stock_out_count"]

        # Check for purchase order history.
        cursor.execute(
            """
            SELECT COUNT(*) AS purchase_order_count
            FROM purchase_order_items
            WHERE product_id = %s
            """,
            (id,)
        )

        purchase_order_count = cursor.fetchone()["purchase_order_count"]

        # If transaction history exists, prevent permanent deletion.
        if (
            movement_count > 0
            or sale_count > 0
            or stock_in_count > 0
            or stock_out_count > 0
            or purchase_order_count > 0
        ):

            return jsonify({
                "error": (
                    "Product cannot be permanently deleted "
                    "because it has transaction history."
                ),
                "transaction_history": {
                    "stock_movements": movement_count,
                    "sales": sale_count,
                    "stock_in": stock_in_count,
                    "stock_out": stock_out_count,
                    "purchase_order_items": purchase_order_count
                },
                "suggestion": (
                    "Keep the product in trash instead "
                    "to preserve inventory history."
                )
            }), 400

        # Safe to permanently delete.
        # Inventory should be automatically deleted because
        # inventory.product_id has ON DELETE CASCADE.
        cursor.execute(
            """
            DELETE FROM products
            WHERE
                product_id = %s
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
            "message": "Product permanently deleted successfully.",
            "product_id": id,
            "product_name": product["product_name"]
        }), 200

    except Exception as e:

        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()