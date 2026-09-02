from database import get_db_connection
from datetime import date, timedelta


def get_all_smart_alerts(store_id):
    alerts = []

    alerts.extend(get_out_of_stock_alerts(store_id))
    alerts.extend(get_expired_alerts(store_id))
    alerts.extend(get_expiring_alerts(store_id))
    alerts.extend(get_low_stock_alerts(store_id))

    return alerts


def get_expiring_alerts(store_id):
    today = date.today()
    seven_days_later = today + timedelta(days=7)

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                p.product_id,
                p.product_name,
                b.batch_id,
                b.quantity,
                b.expiry_date,
                'EXPIRING_SOON' AS alert_type
            FROM batches b
            JOIN products p
                ON b.product_id = p.product_id
            WHERE p.store_id = %s
              AND b.quantity > 0
              AND b.expiry_date BETWEEN %s AND %s
            ORDER BY b.expiry_date ASC
            """,
            (store_id, today, seven_days_later)
        )

        products = cursor.fetchall()

        for product in products:
            product["message"] = (
                f"{product['product_name']} expires on "
                f"{product['expiry_date']}."
            )

        return products

    finally:
        cursor.close()
        db.close()


def get_expired_alerts(store_id):
    today = date.today()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                p.product_id,
                p.product_name,
                b.batch_id,
                b.quantity,
                b.expiry_date,
                'EXPIRED' AS alert_type
            FROM batches b
            JOIN products p
                ON b.product_id = p.product_id
            WHERE p.store_id = %s
              AND b.quantity > 0
              AND b.expiry_date < %s
            ORDER BY b.expiry_date ASC
            """,
            (store_id, today)
        )

        products = cursor.fetchall()

        for product in products:
            product["message"] = (
                f"{product['product_name']} expired on "
                f"{product['expiry_date']}."
            )

        return products

    finally:
        cursor.close()
        db.close()


def get_low_stock_alerts(store_id):
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
                'LOW_STOCK' AS alert_type
            FROM inventory i
            JOIN products p
                ON i.product_id = p.product_id
            WHERE p.store_id = %s
              AND i.stock_quantity > 0
              AND i.stock_quantity <= p.reorder_level
            ORDER BY i.stock_quantity ASC
            """,
            (store_id,)
        )

        products = cursor.fetchall()

        for product in products:
            product["message"] = (
                f"{product['product_name']} is running low. "
                f"Current stock: {product['stock_quantity']}."
            )

        return products

    finally:
        cursor.close()
        db.close()


def get_out_of_stock_alerts(store_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                p.product_id,
                p.product_name,
                i.stock_quantity,
                'OUT_OF_STOCK' AS alert_type
            FROM inventory i
            JOIN products p
                ON i.product_id = p.product_id
            WHERE p.store_id = %s
              AND i.stock_quantity = 0
            ORDER BY p.product_name ASC
            """,
            (store_id,)
        )

        products = cursor.fetchall()

        for product in products:
            product["message"] = (
                f"{product['product_name']} is out of stock."
            )

        return products

    finally:
        cursor.close()
        db.close()