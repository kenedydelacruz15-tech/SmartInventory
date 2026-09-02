from database import get_db_connection


def get_dashboard_summary(store_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # Total products
        cursor.execute(
            """
            SELECT COUNT(*) AS total_products
            FROM products
            WHERE store_id = %s
            """,
            (store_id,)
        )

        total_products = cursor.fetchone()["total_products"]


        # Total inventory
        cursor.execute(
            """
            SELECT COALESCE(SUM(i.stock_quantity), 0) AS total_stock
            FROM inventory i
            JOIN products p
                ON i.product_id = p.product_id
            WHERE p.store_id = %s
            """,
            (store_id,)
        )

        total_stock = cursor.fetchone()["total_stock"]


        # Low stock
        cursor.execute(
            """
            SELECT COUNT(*) AS low_stock_count
            FROM inventory i
            JOIN products p
                ON i.product_id = p.product_id
            WHERE p.store_id = %s
            AND i.stock_quantity > 0
            AND i.stock_quantity <= 10
            """,
            (store_id,)
        )

        low_stock_count = cursor.fetchone()["low_stock_count"]


        # Out of stock
        cursor.execute(
            """
            SELECT COUNT(*) AS out_of_stock_count
            FROM inventory i
            JOIN products p
                ON i.product_id = p.product_id
            WHERE p.store_id = %s
            AND i.stock_quantity <= 0
            """,
            (store_id,)
        )

        out_of_stock_count = cursor.fetchone()["out_of_stock_count"]


        # Today's sales
        cursor.execute(
            """
            SELECT
                COUNT(*) AS today_sale_count,
                COALESCE(SUM(total_sales), 0) AS today_sales
            FROM sales
            WHERE store_id = %s
            AND DATE(sale_date) = CURDATE()
            """,
            (store_id,)
        )

        today_data = cursor.fetchone()


        # Total sales
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_sale_count,
                COALESCE(SUM(total_sales), 0) AS total_revenue
            FROM sales
            WHERE store_id = %s
            """,
            (store_id,)
        )

        sales_data = cursor.fetchone()


        # Unread alerts
        cursor.execute(
            """
            SELECT COUNT(*) AS unread_alerts
            FROM alerts a
            JOIN products p
                ON a.product_id = p.product_id
            WHERE p.store_id = %s
            AND a.status = 'UNREAD'
            """,
            (store_id,)
        )

        unread_alerts = cursor.fetchone()["unread_alerts"]


        # Expiring within 7 days
        cursor.execute(
            """
            SELECT COUNT(DISTINCT product_id) AS expiring_soon_count
            FROM batches
            WHERE store_id = %s
            AND quantity > 0
            AND expiry_date >= CURDATE()
            AND expiry_date <= DATE_ADD(CURDATE(), INTERVAL 7 DAY)
            """,
            (store_id,)
        )

        expiring_soon_count = cursor.fetchone()["expiring_soon_count"]


        # Already expired
        cursor.execute(
            """
            SELECT COUNT(DISTINCT product_id) AS expired_count
            FROM batches
            WHERE store_id = %s
            AND quantity > 0
            AND expiry_date < CURDATE()
            """,
            (store_id,)
        )

        expired_count = cursor.fetchone()["expired_count"]


        return {
            "total_products": total_products,
            "total_stock": int(total_stock),

            "inventory": {
                "low_stock": low_stock_count,
                "out_of_stock": out_of_stock_count
            },

            "expiration": {
                "expiring_soon": expiring_soon_count,
                "expired": expired_count
            },

            "sales": {
                "today_sale_count": today_data["today_sale_count"],
                "today_sales": float(today_data["today_sales"]),

                "total_sale_count": sales_data["total_sale_count"],
                "total_revenue": float(sales_data["total_revenue"])
            },

            "unread_alerts": unread_alerts
        }

    finally:
        cursor.close()
        db.close()