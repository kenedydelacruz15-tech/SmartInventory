from flask import Blueprint, jsonify, request
from database import get_db_connection
from flask_jwt_extended import jwt_required


supplier_bp = Blueprint("supplier_bp", __name__)


@supplier_bp.route("/suppliers", methods=["GET"])
@jwt_required()
def get_suppliers():
    # Get all shared suppliers available to every logged-in user.

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                supplier_id,
                supplier_name,
                contact_number,
                email,
                address
            FROM suppliers
            ORDER BY supplier_name ASC
        """)

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


@supplier_bp.route("/suppliers/<int:id>", methods=["GET"])
@jwt_required()
def get_supplier(id):
    # Get one shared supplier using its supplier ID.

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                supplier_id,
                supplier_name,
                contact_number,
                email,
                address
            FROM suppliers
            WHERE supplier_id = %s
        """, (id,))

        supplier = cursor.fetchone()

        if not supplier:
            return jsonify({
                "error": "Supplier not found"
            }), 404

        return jsonify(supplier), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

    finally:
        cursor.close()
        db.close()


@supplier_bp.route("/suppliers", methods=["POST"])
@jwt_required()
def add_supplier():
    # Create a new shared supplier that can be used by all users.

    data = request.get_json() or {}

    supplier_name = data.get("supplier_name", "").strip()
    contact_number = data.get("contact_number")
    email = data.get("email")
    address = data.get("address")

    if not supplier_name:
        return jsonify({
            "error": "Supplier name is required"
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # Check whether a supplier with the same name already exists.

        cursor.execute("""
            SELECT supplier_id
            FROM suppliers
            WHERE supplier_name = %s
        """, (supplier_name,))

        existing_supplier = cursor.fetchone()

        if existing_supplier:
            return jsonify({
                "error": "Supplier already exists"
            }), 409

        # Insert the new shared supplier.

        cursor.execute("""
            INSERT INTO suppliers
            (
                supplier_name,
                contact_number,
                email,
                address
            )
            VALUES (%s, %s, %s, %s)
        """, (
            supplier_name,
            contact_number,
            email,
            address
        ))

        supplier_id = cursor.lastrowid

        db.commit()

        # Fetch the newly created supplier for the response.

        cursor.execute("""
            SELECT
                supplier_id,
                supplier_name,
                contact_number,
                email,
                address
            FROM suppliers
            WHERE supplier_id = %s
        """, (supplier_id,))

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


@supplier_bp.route("/suppliers/<int:id>", methods=["PUT"])
@jwt_required()
def update_supplier(id):
    # Update all supplier details using the supplier ID.

    data = request.get_json() or {}

    supplier_name = data.get("supplier_name", "").strip()
    contact_number = data.get("contact_number")
    email = data.get("email")
    address = data.get("address")

    if not supplier_name:
        return jsonify({
            "error": "Supplier name is required"
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # Check whether the supplier exists.

        cursor.execute("""
            SELECT supplier_id
            FROM suppliers
            WHERE supplier_id = %s
        """, (id,))

        supplier = cursor.fetchone()

        if not supplier:
            return jsonify({
                "error": "Supplier not found"
            }), 404

        # Prevent duplicate supplier names.

        cursor.execute("""
            SELECT supplier_id
            FROM suppliers
            WHERE supplier_name = %s
              AND supplier_id != %s
        """, (
            supplier_name,
            id
        ))

        duplicate_supplier = cursor.fetchone()

        if duplicate_supplier:
            return jsonify({
                "error": "Another supplier with this name already exists"
            }), 409

        # Update the supplier information.

        cursor.execute("""
            UPDATE suppliers
            SET
                supplier_name = %s,
                contact_number = %s,
                email = %s,
                address = %s
            WHERE supplier_id = %s
        """, (
            supplier_name,
            contact_number,
            email,
            address,
            id
        ))

        db.commit()

        # Fetch the updated supplier for the response.

        cursor.execute("""
            SELECT
                supplier_id,
                supplier_name,
                contact_number,
                email,
                address
            FROM suppliers
            WHERE supplier_id = %s
        """, (id,))

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


@supplier_bp.route("/suppliers/<int:id>", methods=["PATCH"])
@jwt_required()
def partial_update_supplier(id):
    # Update only the supplier fields included in the request.

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
            "error": "No valid fields provided for update"
        }), 400

    if "supplier_name" in fields_to_update:
        fields_to_update["supplier_name"] = (
            fields_to_update["supplier_name"].strip()
        )

        if not fields_to_update["supplier_name"]:
            return jsonify({
                "error": "Supplier name cannot be empty"
            }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # Check whether the supplier exists.

        cursor.execute("""
            SELECT supplier_id
            FROM suppliers
            WHERE supplier_id = %s
        """, (id,))

        supplier = cursor.fetchone()

        if not supplier:
            return jsonify({
                "error": "Supplier not found"
            }), 404

        # Check for duplicate names when changing the supplier name.

        if "supplier_name" in fields_to_update:
            cursor.execute("""
                SELECT supplier_id
                FROM suppliers
                WHERE supplier_name = %s
                  AND supplier_id != %s
            """, (
                fields_to_update["supplier_name"],
                id
            ))

            duplicate_supplier = cursor.fetchone()

            if duplicate_supplier:
                return jsonify({
                    "error": "Another supplier with this name already exists"
                }), 409

        # Build the SQL query using only the provided fields.

        update_parts = []
        values = []

        for field, value in fields_to_update.items():
            update_parts.append(f"{field} = %s")
            values.append(value)

        values.append(id)

        sql = f"""
            UPDATE suppliers
            SET {", ".join(update_parts)}
            WHERE supplier_id = %s
        """

        cursor.execute(sql, tuple(values))

        db.commit()

        # Fetch the complete supplier after the update.

        cursor.execute("""
            SELECT
                supplier_id,
                supplier_name,
                contact_number,
                email,
                address
            FROM suppliers
            WHERE supplier_id = %s
        """, (id,))

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


@supplier_bp.route("/suppliers/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_supplier(id):
    # Delete a shared supplier only when it exists.

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # Check whether the supplier exists.

        cursor.execute("""
            SELECT supplier_id
            FROM suppliers
            WHERE supplier_id = %s
        """, (id,))

        supplier = cursor.fetchone()

        if not supplier:
            return jsonify({
                "error": "Supplier not found"
            }), 404

        # Check whether stock-in records are using this supplier.

        cursor.execute("""
            SELECT COUNT(*) AS stock_in_count
            FROM stock_in
            WHERE supplier_id = %s
        """, (id,))

        result = cursor.fetchone()

        if result["stock_in_count"] > 0:
            return jsonify({
                "error": "Cannot delete supplier because stock-in records are using it",
                "stock_in_count": result["stock_in_count"]
            }), 400

        # Delete the supplier.

        cursor.execute("""
            DELETE FROM suppliers
            WHERE supplier_id = %s
        """, (id,))

        db.commit()

        return jsonify({
            "message": "Supplier deleted successfully!",
            "deleted_supplier_id": id
        }), 200

    except Exception as e:
        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:
        cursor.close()
        db.close()