from flask import Blueprint, jsonify, request
from database import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity
import json


audit_bp = Blueprint("audit_bp", __name__)

# GET ALL AUDIT LOGS FOR THE LOGGED-IN STORE

@audit_bp.route("/audit-logs", methods=["GET"])
@jwt_required()
def get_audit_logs():

    current_store_id = get_jwt_identity()

    
    # GET FILTER PARAMETERS
    

    action = request.args.get("action")
    entity_type = request.args.get("entity_type")
    entity_id = request.args.get("entity_id")
    user_id = request.args.get("user_id")

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    
    # PAGINATION
    

    try:

        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))

        if page < 1:
            page = 1

        if per_page < 1:
            per_page = 20

        # Prevent extremely large requests.
        if per_page > 100:
            per_page = 100

    except ValueError:

        return jsonify({
            "error": "Page and per_page must be valid numbers."
        }), 400

    offset = (page - 1) * per_page

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        
        # BASE QUERY
        

        where_conditions = [
            "store_id = %s"
        ]

        values = [
            current_store_id
        ]

        
        # FILTER BY ACTION
        

        if action:

            where_conditions.append(
                "action = %s"
            )

            values.append(action)

        
        # FILTER BY ENTITY TYPE
        

        if entity_type:

            where_conditions.append(
                "entity_type = %s"
            )

            values.append(
                entity_type.upper()
            )

        
        # FILTER BY ENTITY ID
        

        if entity_id:

            try:

                entity_id = int(entity_id)

                where_conditions.append(
                    "entity_id = %s"
                )

                values.append(entity_id)

            except ValueError:

                return jsonify({
                    "error": "entity_id must be a valid number."
                }), 400

        
        # FILTER BY USER ID
        

        if user_id:

            try:

                user_id = int(user_id)

                where_conditions.append(
                    "user_id = %s"
                )

                values.append(user_id)

            except ValueError:

                return jsonify({
                    "error": "user_id must be a valid number."
                }), 400

        
        # FILTER BY START DATE
        

        if start_date:

            where_conditions.append(
                "created_at >= %s"
            )

            values.append(start_date)

        
        # FILTER BY END DATE
        

        if end_date:

            # Includes the entire end date.
            where_conditions.append(
                "created_at < DATE_ADD(%s, INTERVAL 1 DAY)"
            )

            values.append(end_date)

        
        # BUILD WHERE CLAUSE
        

        where_sql = " AND ".join(
            where_conditions
        )

        
        # GET TOTAL COUNT
        

        count_sql = f"""
            SELECT COUNT(*) AS total_logs
            FROM audit_logs
            WHERE {where_sql}
        """

        cursor.execute(
            count_sql,
            tuple(values)
        )

        total_result = cursor.fetchone()

        total_logs = total_result["total_logs"]

        
        # GET AUDIT LOGS
        

        logs_sql = f"""
            SELECT
                audit_log_id,
                store_id,
                user_id,
                action,
                entity_type,
                entity_id,
                description,
                old_data,
                new_data,
                created_at

            FROM audit_logs

            WHERE {where_sql}

            ORDER BY created_at DESC

            LIMIT %s OFFSET %s
        """

        log_values = values.copy()

        log_values.append(per_page)
        log_values.append(offset)

        cursor.execute(
            logs_sql,
            tuple(log_values)
        )

        logs = cursor.fetchall()

        
        # CONVERT JSON DATA
        

        for log in logs:

            if log["old_data"]:

                if isinstance(
                    log["old_data"],
                    str
                ):

                    try:

                        log["old_data"] = json.loads(
                            log["old_data"]
                        )

                    except json.JSONDecodeError:

                        pass

            if log["new_data"]:

                if isinstance(
                    log["new_data"],
                    str
                ):

                    try:

                        log["new_data"] = json.loads(
                            log["new_data"]
                        )

                    except json.JSONDecodeError:

                        pass

        
        # CALCULATE PAGINATION
        

        total_pages = (
            (total_logs + per_page - 1)
            // per_page
        )

        return jsonify({

            "total_logs": total_logs,

            "page": page,

            "per_page": per_page,

            "total_pages": total_pages,

            "logs": logs

        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()



# GET ONE AUDIT LOG

@audit_bp.route(
    "/audit-logs/<int:id>",
    methods=["GET"]
)
@jwt_required()
def get_audit_log(id):

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                audit_log_id,
                store_id,
                user_id,
                action,
                entity_type,
                entity_id,
                description,
                old_data,
                new_data,
                created_at

            FROM audit_logs

            WHERE
                audit_log_id = %s
                AND store_id = %s
            """,
            (
                id,
                current_store_id
            )
        )

        audit_log = cursor.fetchone()

        if not audit_log:

            return jsonify({
                "error": "Audit log not found."
            }), 404

        
        # CONVERT OLD DATA JSON
        

        if audit_log["old_data"]:

            if isinstance(
                audit_log["old_data"],
                str
            ):

                try:

                    audit_log["old_data"] = json.loads(
                        audit_log["old_data"]
                    )

                except json.JSONDecodeError:

                    pass

        
        # CONVERT NEW DATA JSON
        

        if audit_log["new_data"]:

            if isinstance(
                audit_log["new_data"],
                str
            ):

                try:

                    audit_log["new_data"] = json.loads(
                        audit_log["new_data"]
                    )

                except json.JSONDecodeError:

                    pass

        return jsonify(
            audit_log
        ), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()