from database import get_db_connection


def get_reorder_recommendations(store_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                p.product_id,
                p.product_name,
                i.stock_quantity,
                p.reorder_level,

                CASE
                    WHEN i.stock_quantity = 0 THEN 'OUT_OF_STOCK'
                    WHEN i.stock_quantity <= p.reorder_level THEN 'REORDER'
                    ELSE 'STOCK_OK'
                END AS status,

                CASE
                    WHEN i.stock_quantity <= p.reorder_level
                    THEN (p.reorder_level * 2) - i.stock_quantity
                    ELSE 0
                END AS recommended_quantity

            FROM products p
            JOIN inventory i
                ON p.product_id = i.product_id

            WHERE p.store_id = %s
              AND i.stock_quantity <= p.reorder_level

            ORDER BY i.stock_quantity ASC, p.product_name ASC
            """,
            (store_id,)
        )

        return cursor.fetchall()

    finally:
        cursor.close()
        db.close()