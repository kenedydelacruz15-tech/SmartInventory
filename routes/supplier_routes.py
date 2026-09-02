from flask import Blueprint, jsonify, request
from database import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity

supplier_bp = Blueprint("supplier_bp", __name__)


@supplier_bp.route("/suppliers", methods=["GET"])
@jwt_required()
def get_suppliers():
    """
    Fetches only the suppliers belonging to the logged-in store owner.
    """
    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM suppliers WHERE store_id = %s", (current_store_id,))
    suppliers = cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify(suppliers)


@supplier_bp.route("/suppliers", methods=["POST"])
@jwt_required()
def add_supplier():
    """
    Creates a new supplier account mapped to the active store account.
    """
    current_store_id = get_jwt_identity()
    data = request.get_json()

    db = get_db_connection()
    cursor = db.cursor()

    sql = """
        INSERT INTO suppliers
        (supplier_name, contact_number, email, address, store_id)
        VALUES (%s, %s, %s, %s, %s)
    """

    cursor.execute(
        sql,
        (
            data["supplier_name"],
            data.get("contact_number"),
            data.get("email"),
            data.get("address"),
            current_store_id
        )
    )

    db.commit()

    cursor.close()
    db.close()

    return jsonify({
        "message": "Supplier added successfully!"
    })


@supplier_bp.route("/suppliers/<int:id>", methods=["PUT"])
@jwt_required()
def update_supplier(id):
    """
    Updates a specific supplier, ensuring it belongs to the logged-in store.
    """
    current_store_id = get_jwt_identity()
    data = request.get_json()

    db = get_db_connection()
    cursor = db.cursor()

    sql = """
        UPDATE suppliers
        SET
            supplier_name = %s,
            contact_number = %s,
            email = %s,
            address = %s
        WHERE supplier_id = %s AND store_id = %s
    """

    cursor.execute(
        sql,
        (
            data["supplier_name"],
            data.get("contact_number"),
            data.get("email"),
            data.get("address"),
            id,
            current_store_id
        )
    )

    db.commit()

    cursor.close()
    db.close()

    return jsonify({
        "message": "Supplier updated successfully!"
    })


@supplier_bp.route("/suppliers/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_supplier(id):
    """
    Deletes a specific supplier, preventing cross-tenant data operations.
    """
    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM suppliers WHERE supplier_id = %s AND store_id = %s",
        (id, current_store_id)
    )

    db.commit()

    cursor.close()
    db.close()

    return jsonify({
        "message": "Supplier deleted successfully!"
    })
