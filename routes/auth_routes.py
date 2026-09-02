import bcrypt
from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token
from database import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity

# group authentication-related routes together
auth_bp = Blueprint("auth_bp", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Handles new account registration.
    Hashes the plain-text password using bcrypt and saves the store account into MySQL.
    """
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    db = get_db_connection()
    cursor = db.cursor()

    try:
        sql = "INSERT INTO users (username, password_hash) VALUES (%s, %s)"
        cursor.execute(sql, (username, hashed_password))
        db.commit()
        
        return jsonify({"message": "Store account registered successfully!"}), 201

    except Exception as e:
        db.rollback()
        if "Duplicate entry" in str(e) or "1062" in str(e):
            return jsonify({"error": "Username already exists"}), 409
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        db.close()


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Handles user login validation.
    Verifies user-submitted text against the database hash and issues a stateless JSON Web Token.
    """
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    db = get_db_connection()
    # referenced by name keys instead of index numbers
    cursor = db.cursor(dictionary=True)

    # Search for the user record by the provided username string
    cursor.execute("SELECT user_id, password_hash FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    cursor.close()
    db.close()

    # Deny access if the username does not exist in the database table
    if not user:
        return jsonify({"error": "Invalid username or password"}), 401

    stored_hash = user["password_hash"].encode('utf-8')

    if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
        # Generate an encrypted JSON Web Token containing the user_id integer transformed to a string.
        access_token = create_access_token(identity=str(user["user_id"]))
        
        return jsonify({
            "message": "Login successful!",
            "token": access_token
        }), 200

    return jsonify({"error": "Invalid username or password"}), 401

@auth_bp.route("/delete-account", methods=["DELETE"])
@jwt_required()
def delete_user_account():
    """
    Deletes the logged-in store owner account from the database.
    ON DELETE CASCADE automatically wipes all associated store data.
    """
    # Extract the user_id from the active validation token
    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor()

    try:
        sql = "DELETE FROM users WHERE user_id = %s"
        cursor.execute(sql, (current_store_id,))
        db.commit()

        return jsonify({
            "message": "Store account and all associated data deleted successfully!"
        }), 200

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
        
    finally:
        cursor.close()
        db.close()