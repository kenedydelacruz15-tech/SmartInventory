from flask import Blueprint, jsonify, request
from database import get_db_connection
from flask_jwt_extended import jwt_required


supplier_bp = Blueprint("supplier_bp", __name__)


# GET ALL ACTIVE SUPPLIERS

@supplier_bp.route("/suppliers", methods=["GET"])
@jwt_required()
def get_suppliers():

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                supplier_id,
                supplier_name,
                contact_number,
                email,
                address
            FROM suppliers
            WHERE deleted_at IS NULL
            ORDER BY supplier_name ASC
            """
        )

        suppliers = cursor.fetchall()

        return jsonify({
            "supplier_count": len(suppliers),
            "suppliers": suppliers
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()

# GET SUPPLIER TRASH

@supplier_bp.route("/suppliers/trash", methods=["GET"])
@jwt_required()
def get_supplier_trash():

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                supplier_id,
                supplier_name,
                contact_number,
                email,
                address,
                deleted_at
            FROM suppliers
            WHERE deleted_at IS NOT NULL
            ORDER BY deleted_at DESC
            """
        )

        suppliers = cursor.fetchall()

        return jsonify({
            "trash_count": len(suppliers),
            "deleted_suppliers": suppliers
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()


# GET ONE ACTIVE SUPPLIER

@supplier_bp.route("/suppliers/<int:id>", methods=["GET"])
@jwt_required()
def get_supplier(id):

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                supplier_id,
                supplier_name,
                contact_number,
                email,
                address
            FROM suppliers
            WHERE
                supplier_id = %s
                AND deleted_at IS NULL
            """,
            (id,)
        )

        supplier = cursor.fetchone()

        if not supplier:

            return jsonify({
                "error": "Supplier not found."
            }), 404

        return jsonify(supplier), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()

# ADD SUPPLIER

@supplier_bp.route("/suppliers", methods=["POST"])
@jwt_required()
def add_supplier():

    data = request.get_json() or {}

    supplier_name = data.get("supplier_name", "").strip()
    contact_number = data.get("contact_number")
    email = data.get("email")
    address = data.get("address")

    if not supplier_name:

        return jsonify({
            "error": "Supplier name is required."
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Check for an active supplier with the same name.
        cursor.execute(
            """
            SELECT supplier_id
            FROM suppliers
            WHERE
                supplier_name = %s
                AND deleted_at IS NULL
            """,
            (supplier_name,)
        )

        if cursor.fetchone():

            return jsonify({
                "error": "Supplier already exists."
            }), 409

        # Check whether the supplier exists in trash.
        cursor.execute(
            """
            SELECT supplier_id
            FROM suppliers
            WHERE
                supplier_name = %s
                AND deleted_at IS NOT NULL
            """,
            (supplier_name,)
        )

        deleted_supplier = cursor.fetchone()

        if deleted_supplier:

            return jsonify({
                "error": "This supplier exists in trash. Restore it instead.",
                "supplier_id": deleted_supplier["supplier_id"]
            }), 409

        # Create supplier.
        cursor.execute(
            """
            INSERT INTO suppliers
            (
                supplier_name,
                contact_number,
                email,
                address
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                supplier_name,
                contact_number,
                email,
                address
            )
        )

        supplier_id = cursor.lastrowid

        db.commit()

        cursor.execute(
            """
            SELECT
                supplier_id,
                supplier_name,
                contact_number,
                email,
                address
            FROM suppliers
            WHERE supplier_id = %s
            """,
            (supplier_id,)
        )

        new_supplier = cursor.fetchone()

        return jsonify({
            "message": "Supplier added successfully!",
            "supplier": new_supplier
        }), 201

    except Exception as e:

        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()


# FULL UPDATE SUPPLIER

@supplier_bp.route("/suppliers/<int:id>", methods=["PUT"])
@jwt_required()
def update_supplier(id):

    data = request.get_json() or {}

    supplier_name = data.get("supplier_name", "").strip()
    contact_number = data.get("contact_number")
    email = data.get("email")
    address = data.get("address")

    if not supplier_name:

        return jsonify({
            "error": "Supplier name is required."
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Ensure supplier exists and is active.
        cursor.execute(
            """
            SELECT supplier_id
            FROM suppliers
            WHERE
                supplier_id = %s
                AND deleted_at IS NULL
            """,
            (id,)
        )

        if not cursor.fetchone():

            return jsonify({
                "error": "Supplier not found or is in trash."
            }), 404

        # Prevent duplicate active supplier names.
        cursor.execute(
            """
            SELECT supplier_id
            FROM suppliers
            WHERE
                supplier_name = %s
                AND supplier_id != %s
                AND deleted_at IS NULL
            """,
            (
                supplier_name,
                id
            )
        )

        if cursor.fetchone():

            return jsonify({
                "error": "Another active supplier with this name already exists."
            }), 409

        cursor.execute(
            """
            UPDATE suppliers
            SET
                supplier_name = %s,
                contact_number = %s,
                email = %s,
                address = %s
            WHERE
                supplier_id = %s
                AND deleted_at IS NULL
            """,
            (
                supplier_name,
                contact_number,
                email,
                address,
                id
            )
        )

        db.commit()

        cursor.execute(
            """
            SELECT
                supplier_id,
                supplier_name,
                contact_number,
                email,
                address
            FROM suppliers
            WHERE supplier_id = %s
            """,
            (id,)
        )

        updated_supplier = cursor.fetchone()

        return jsonify({
            "message": "Supplier updated successfully!",
            "updated_supplier": updated_supplier
        }), 200

    except Exception as e:

        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()

# PARTIAL UPDATE SUPPLIER

@supplier_bp.route("/suppliers/<int:id>", methods=["PATCH"])
@jwt_required()
def partial_update_supplier(id):

    data = request.get_json() or {}

    allowed_fields = [
        "supplier_name",
        "contact_number",
        "email",
        "address"
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

    # Validate supplier name.
    if "supplier_name" in fields_to_update:

        supplier_name = str(
            fields_to_update["supplier_name"]
        ).strip()

        if not supplier_name:

            return jsonify({
                "error": "Supplier name cannot be empty."
            }), 400

        fields_to_update["supplier_name"] = supplier_name

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Ensure supplier is active.
        cursor.execute(
            """
            SELECT supplier_id
            FROM suppliers
            WHERE
                supplier_id = %s
                AND deleted_at IS NULL
            """,
            (id,)
        )

        if not cursor.fetchone():

            return jsonify({
                "error": "Supplier not found or is in trash."
            }), 404

        # Check duplicate supplier name.
        if "supplier_name" in fields_to_update:

            cursor.execute(
                """
                SELECT supplier_id
                FROM suppliers
                WHERE
                    supplier_name = %s
                    AND supplier_id != %s
                    AND deleted_at IS NULL
                """,
                (
                    fields_to_update["supplier_name"],
                    id
                )
            )

            if cursor.fetchone():

                return jsonify({
                    "error": "Another active supplier with this name already exists."
                }), 409

        # Build dynamic update query.
        update_parts = []
        values = []

        for field, value in fields_to_update.items():

            update_parts.append(f"{field} = %s")
            values.append(value)

        values.append(id)

        sql = f"""
            UPDATE suppliers
            SET {", ".join(update_parts)}
            WHERE
                supplier_id = %s
                AND deleted_at IS NULL
        """

        cursor.execute(
            sql,
            tuple(values)
        )

        db.commit()

        cursor.execute(
            """
            SELECT
                supplier_id,
                supplier_name,
                contact_number,
                email,
                address
            FROM suppliers
            WHERE supplier_id = %s
            """,
            (id,)
        )

        updated_supplier = cursor.fetchone()

        return jsonify({
            "message": "Supplier updated successfully!",
            "updated_fields": list(fields_to_update.keys()),
            "updated_supplier": updated_supplier
        }), 200

    except Exception as e:

        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()


# SOFT DELETE SUPPLIER

@supplier_bp.route("/suppliers/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_supplier(id):

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                supplier_id,
                supplier_name
            FROM suppliers
            WHERE
                supplier_id = %s
                AND deleted_at IS NULL
            """,
            (id,)
        )

        supplier = cursor.fetchone()

        if not supplier:

            return jsonify({
                "error": "Supplier not found or already deleted."
            }), 404

        # Soft delete supplier.
        cursor.execute(
            """
            UPDATE suppliers
            SET deleted_at = NOW()
            WHERE
                supplier_id = %s
                AND deleted_at IS NULL
            """,
            (id,)
        )

        db.commit()

        return jsonify({
            "message": "Supplier moved to trash successfully.",
            "deleted_supplier_id": id,
            "supplier_name": supplier["supplier_name"]
        }), 200

    except Exception as e:

        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()


# RESTORE SUPPLIER

@supplier_bp.route("/suppliers/<int:id>/restore", methods=["PUT"])
@jwt_required()
def restore_supplier(id):

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Find deleted supplier.
        cursor.execute(
            """
            SELECT
                supplier_id,
                supplier_name
            FROM suppliers
            WHERE
                supplier_id = %s
                AND deleted_at IS NOT NULL
            """,
            (id,)
        )

        deleted_supplier = cursor.fetchone()

        if not deleted_supplier:

            return jsonify({
                "error": "Deleted supplier not found in trash."
            }), 404

        # Check duplicate active supplier name.
        cursor.execute(
            """
            SELECT supplier_id
            FROM suppliers
            WHERE
                supplier_name = %s
                AND deleted_at IS NULL
            """,
            (deleted_supplier["supplier_name"],)
        )

        if cursor.fetchone():

            return jsonify({
                "error": (
                    "Cannot restore supplier because an active "
                    "supplier with the same name already exists."
                )
            }), 409

        # Restore supplier.
        cursor.execute(
            """
            UPDATE suppliers
            SET deleted_at = NULL
            WHERE
                supplier_id = %s
                AND deleted_at IS NOT NULL
            """,
            (id,)
        )

        db.commit()

        return jsonify({
            "message": "Supplier restored successfully!",
            "restored_supplier_id": id
        }), 200

    except Exception as e:

        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()

# SAFE PERMANENT DELETE SUPPLIER

@supplier_bp.route(
    "/suppliers/<int:id>/permanent",
    methods=["DELETE"]
)
@jwt_required()
def permanently_delete_supplier(id):

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Supplier must already be in trash.
        cursor.execute(
            """
            SELECT
                supplier_id,
                supplier_name
            FROM suppliers
            WHERE
                supplier_id = %s
                AND deleted_at IS NOT NULL
            """,
            (id,)
        )

        supplier = cursor.fetchone()

        if not supplier:

            return jsonify({
                "error": (
                    "Supplier not found in trash. "
                    "Only deleted suppliers can be permanently deleted."
                )
            }), 404

        # Safety check: stock_in history.
        cursor.execute(
            """
            SELECT COUNT(*) AS stock_in_count
            FROM stock_in
            WHERE supplier_id = %s
            """,
            (id,)
        )

        stock_in_result = cursor.fetchone()

        # Safety check: purchase orders.
        cursor.execute(
            """
            SELECT COUNT(*) AS purchase_order_count
            FROM purchase_orders
            WHERE supplier_id = %s
            """,
            (id,)
        )

        purchase_order_result = cursor.fetchone()

        stock_in_count = stock_in_result["stock_in_count"]
        purchase_order_count = purchase_order_result["purchase_order_count"]

        # Block permanent deletion if history exists.
        if stock_in_count > 0 or purchase_order_count > 0:

            return jsonify({
                "error": (
                    "Cannot permanently delete supplier because "
                    "transaction history is still using it."
                ),
                "stock_in_count": stock_in_count,
                "purchase_order_count": purchase_order_count
            }), 400

        # Permanently delete.
        cursor.execute(
            """
            DELETE FROM suppliers
            WHERE
                supplier_id = %s
                AND deleted_at IS NOT NULL
            """,
            (id,)
        )

        db.commit()

        return jsonify({
            "message": "Supplier permanently deleted successfully.",
            "permanently_deleted_supplier_id": id,
            "supplier_name": supplier["supplier_name"]
        }), 200

    except Exception as e:

        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()