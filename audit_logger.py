import json
from database import get_db_connection


def create_audit_log(
    store_id,
    action,
    entity_type,
    entity_id=None,
    description=None,
    user_id=None,
    old_data=None,
    new_data=None
):

    db = get_db_connection()
    cursor = db.cursor()

    try:

        # Convert Python dictionaries to JSON strings.
        if old_data is not None:
            old_data = json.dumps(old_data, default=str)

        if new_data is not None:
            new_data = json.dumps(new_data, default=str)

        cursor.execute(
            """
            INSERT INTO audit_logs
            (
                store_id,
                user_id,
                action,
                entity_type,
                entity_id,
                description,
                old_data,
                new_data
            )
            VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                store_id,
                user_id,
                action,
                entity_type,
                entity_id,
                description,
                old_data,
                new_data
            )
        )

        db.commit()

    except Exception as e:

        db.rollback()

        # Important: don't crash the main API
        print(f"Audit log error: {str(e)}")

    finally:

        cursor.close()
        db.close()