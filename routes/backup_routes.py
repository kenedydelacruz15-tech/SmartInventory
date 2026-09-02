import json
import decimal
from datetime import datetime, date
from flask import Blueprint, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import get_db_connection 

# Define a distinct blueprint for backups
backup_bp = Blueprint("backup", __name__, url_prefix="/backup")

@backup_bp.route("/export", methods=["GET"])
@jwt_required()
def export_tenant_data():
    current_store_id = get_jwt_identity()
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    backup_payload = {
        "export_metadata": {
            "store_id": current_store_id,
            "exported_at": str(datetime.now())
        },
        "batches": [],
        "products": []
    }
    
    try:
        # 1. Fetch Tenant Batches
        cursor.execute("SELECT * FROM batches WHERE store_id = %s", (current_store_id,))
        backup_payload["batches"] = cursor.fetchall()
        
        # 2. Fetch Tenant Products
        cursor.execute("SELECT * FROM products WHERE store_id = %s", (current_store_id,))
        backup_payload["products"] = cursor.fetchall()

        # Clean types so they don't break the JSON serializer
        for section in ["batches", "products"]:
            for row in backup_payload[section]:
                for key, val in row.items():
                    if isinstance(val, (datetime, date)):
                        row[key] = str(val)
                    elif isinstance(val, decimal.Decimal):
                        row[key] = float(val)

        # Build download file package string
        json_output = json.dumps(backup_payload, indent=4)
        filename = f"store_{current_store_id}_backup_{datetime.now().strftime('%Y%m%d')}.json"
        
        return Response(
            json_output,
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        db.close()
