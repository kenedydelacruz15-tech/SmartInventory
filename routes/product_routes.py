from flask import Blueprint, jsonify, request
from database import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity


product_bp = Blueprint("product_bp", __name__)

# GET ALL PRODUCTS FOR THE LOGGED-IN STORE

@product_bp.route("/products", methods=["GET"])
@jwt_required()
def get_products():
    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        sql = """
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

            LEFT JOIN inventory i
                ON p.product_id = i.product_id

            WHERE p.store_id = %s

            ORDER BY p.product_id
        """

        cursor.execute(sql, (current_store_id,))
        products = cursor.fetchall()

        return jsonify(products), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        db.close()

# GET PRODUCT BY BARCODE

@product_bp.route("/products/barcode/<barcode>", methods=["GET"])
@jwt_required()
def get_product_by_barcode(barcode):
    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        sql = """
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

            LEFT JOIN inventory i
                ON p.product_id = i.product_id

            WHERE p.barcode = %s
              AND p.store_id = %s
        """

        cursor.execute(sql, (barcode, current_store_id))

        product = cursor.fetchone()

        if not product:
            return jsonify({
                "error": "Product not found"
            }), 404

        return jsonify(product), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        db.close()

# ADD NEW PRODUCT

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
            "error": "Product name, category and price are required"
        }), 400

    try:
        reorder_level = int(reorder_level)

        if reorder_level < 0:
            return jsonify({
                "error": "Reorder level cannot be negative"
            }), 400

    except (ValueError, TypeError):
        return jsonify({
            "error": "Reorder level must be a valid number"
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # Check category belongs to current store
        cursor.execute(
            """
            SELECT category_id
            FROM categories
            WHERE category_id = %s
              AND store_id = %s
            """,
            (category_id, current_store_id)
        )

        if not cursor.fetchone():
            return jsonify({
                "error": "Category not found or unauthorized"
            }), 404

        # Check barcode uniqueness
        if barcode:
            cursor.execute(
                """
                SELECT product_id
                FROM products
                WHERE barcode = %s
                """,
                (barcode,)
            )

            if cursor.fetchone():
                return jsonify({
                    "error": "Barcode already exists"
                }), 409

        # Insert product
        cursor.execute(
            """
            INSERT INTO products
            (
                product_name,
                category_id,
                price,
                store_id,
                barcode,
                reorder_level
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                product_name,
                category_id,
                price,
                current_store_id,
                barcode,
                reorder_level
            )
        )

        product_id = cursor.lastrowid

        # Create inventory automatically
        cursor.execute(
            """
            INSERT INTO inventory
            (product_id, stock_quantity)
            VALUES (%s, %s)
            """,
            (product_id, 0)
        )

        db.commit()

        # Get newly created product
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
            LEFT JOIN inventory i
                ON p.product_id = i.product_id
            WHERE p.product_id = %s
              AND p.store_id = %s
            """,
            (product_id, current_store_id)
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

# FULL PRODUCT UPDATE

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
            "error": "Product name, category and price are required"
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # Check product ownership
        cursor.execute(
            """
            SELECT product_id, reorder_level
            FROM products
            WHERE product_id = %s
              AND store_id = %s
            """,
            (id, current_store_id)
        )

        product = cursor.fetchone()

        if not product:
            return jsonify({
                "error": "Product not found or unauthorized"
            }), 404

        # Keep old reorder level if not provided
        if reorder_level is None:
            reorder_level = product["reorder_level"]

        try:
            reorder_level = int(reorder_level)

            if reorder_level < 0:
                return jsonify({
                    "error": "Reorder level cannot be negative"
                }), 400

        except (ValueError, TypeError):
            return jsonify({
                "error": "Reorder level must be a valid number"
            }), 400

        # Check category ownership
        cursor.execute(
            """
            SELECT category_id
            FROM categories
            WHERE category_id = %s
              AND store_id = %s
            """,
            (category_id, current_store_id)
        )

        if not cursor.fetchone():
            return jsonify({
                "error": "Category not found or unauthorized"
            }), 404

        # Check barcode uniqueness
        if barcode:
            cursor.execute(
                """
                SELECT product_id
                FROM products
                WHERE barcode = %s
                  AND product_id != %s
                """,
                (barcode, id)
            )

            if cursor.fetchone():
                return jsonify({
                    "error": "Barcode already exists"
                }), 409

        # Update product
        cursor.execute(
            """
            UPDATE products
            SET
                product_name = %s,
                category_id = %s,
                price = %s,
                barcode = %s,
                reorder_level = %s
            WHERE product_id = %s
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

        # Get updated product
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
            LEFT JOIN inventory i
                ON p.product_id = i.product_id
            WHERE p.product_id = %s
              AND p.store_id = %s
            """,
            (id, current_store_id)
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

# PARTIAL / SPECIFIC PRODUCT UPDATE (PATCH)

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

    # Check that at least one valid field was provided
    fields_to_update = {
        field: data[field]
        for field in allowed_fields
        if field in data
    }

    if not fields_to_update:
        return jsonify({
            "error": "No valid fields provided for update"
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # Check product belongs to logged-in store
        cursor.execute(
            """
            SELECT product_id
            FROM products
            WHERE product_id = %s
              AND store_id = %s
            """,
            (id, current_store_id)
        )

        product = cursor.fetchone()

        if not product:
            return jsonify({
                "error": "Product not found or unauthorized"
            }), 404

        # Validate reorder level
        if "reorder_level" in fields_to_update:
            try:
                reorder_level = int(
                    fields_to_update["reorder_level"]
                )

                if reorder_level < 0:
                    return jsonify({
                        "error": "Reorder level cannot be negative"
                    }), 400

                fields_to_update["reorder_level"] = reorder_level

            except (ValueError, TypeError):
                return jsonify({
                    "error": "Reorder level must be a valid number"
                }), 400

        # Validate category ownership
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

            category = cursor.fetchone()

            if not category:
                return jsonify({
                    "error": "Category not found or unauthorized"
                }), 404

        # Check barcode uniqueness
        if (
            "barcode" in fields_to_update
            and fields_to_update["barcode"]
        ):
            cursor.execute(
                """
                SELECT product_id
                FROM products
                WHERE barcode = %s
                  AND product_id != %s
                """,
                (
                    fields_to_update["barcode"],
                    id
                )
            )

            if cursor.fetchone():
                return jsonify({
                    "error": "Barcode already exists"
                }), 409

        # Build dynamic UPDATE query safely
        update_parts = []
        values = []

        for field, value in fields_to_update.items():
            update_parts.append(f"{field} = %s")
            values.append(value)

        sql = f"""
            UPDATE products
            SET {", ".join(update_parts)}
            WHERE product_id = %s
              AND store_id = %s
        """

        values.append(id)
        values.append(current_store_id)

        cursor.execute(sql, tuple(values))

        db.commit()

        # Get complete updated product
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
            LEFT JOIN inventory i
                ON p.product_id = i.product_id
            WHERE p.product_id = %s
              AND p.store_id = %s
            """,
            (id, current_store_id)
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

# DELETE PRODUCT

@product_bp.route("/products/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_product(id):
    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute(
            """
            DELETE FROM products
            WHERE product_id = %s
              AND store_id = %s
            """,
            (id, current_store_id)
        )

        if cursor.rowcount == 0:
            return jsonify({
                "error": "Product not found or unauthorized"
            }), 404

        db.commit()

        return jsonify({
            "message": "Product deleted successfully!"
        }), 200

    except Exception as e:
        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:
        cursor.close()
        db.close()

# SEARCH PRODUCTS

@product_bp.route("/products/search", methods=["GET"])
@jwt_required()
def search_products():
    current_store_id = get_jwt_identity()

    search_query = request.args.get("q", "").strip()

    if not search_query:
        return jsonify({
            "error": "Search query is required"
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        sql = """
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

            LEFT JOIN inventory i
                ON p.product_id = i.product_id

            WHERE p.store_id = %s
              AND p.product_name LIKE %s

            ORDER BY p.product_name ASC
        """

        cursor.execute(
            sql,
            (
                current_store_id,
                f"%{search_query}%"
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