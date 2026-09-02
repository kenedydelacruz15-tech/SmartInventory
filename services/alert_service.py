from database import get_db_connection

def get_smart_alerts(store_id):
    """
    Generates inventory low-stock alerts isolated by store ownership.
    """
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    sql = """
        SELECT
            products.product_id,
            products.product_name,
            inventory.stock_quantity,

            COALESCE(
                SUM(sale_items.quantity),
                0
            ) AS total_quantity_sold,

            COUNT(
                DISTINCT DATE(sales.sale_date)
            ) AS sales_days

        FROM products

        LEFT JOIN inventory
            ON products.product_id = inventory.product_id

        LEFT JOIN sale_items
            ON products.product_id = sale_items.product_id

        LEFT JOIN sales
            ON sale_items.sale_id = sales.sale_id

        WHERE products.store_id = %s

        GROUP BY
            products.product_id,
            products.product_name,
            inventory.stock_quantity

        ORDER BY products.product_name
    """

    cursor.execute(sql, (store_id,))
    products = cursor.fetchall()

    cursor.close()
    db.close()

    alerts = []

    for product in products:

        product_id = product["product_id"]
        product_name = product["product_name"]

        current_stock = product["stock_quantity"] or 0
        total_quantity_sold = product["total_quantity_sold"] or 0
        sales_days = product["sales_days"] or 0

        # Calculate average daily demand
        if sales_days > 0:
            average_daily_demand = (
                total_quantity_sold / sales_days
            )
        else:
            average_daily_demand = 0

        # Calculate days until stock-out
        if average_daily_demand > 0:
            days_until_stockout = (
                current_stock / average_daily_demand
            )
        else:
            days_until_stockout = None

        # Calculate 7-day target stock
        target_stock = average_daily_demand * 7

        # Calculate reorder quantity
        reorder_quantity = target_stock - current_stock

        if reorder_quantity < 0:
            reorder_quantity = 0

        # ALERT PRIORITY

        if current_stock <= 0:

            alerts.append({
                "product_id": product_id,
                "product_name": product_name,
                "alert_type": "OUT_OF_STOCK",
                "priority": "HIGH",
                "message": (
                    f"{product_name} is out of stock."
                ),
                "current_stock": current_stock,
                "days_until_stockout": 0,
                "recommended_reorder_quantity": round(
                    reorder_quantity
                )
            })

        elif (
            days_until_stockout is not None
            and days_until_stockout <= 3
        ):

            alerts.append({
                "product_id": product_id,
                "product_name": product_name,
                "alert_type": "CRITICAL_STOCK",
                "priority": "HIGH",
                "message": (
                    f"{product_name} may run out of stock "
                    f"in approximately "
                    f"{round(days_until_stockout, 1)} days."
                ),
                "current_stock": current_stock,
                "days_until_stockout": round(
                    days_until_stockout,
                    2
                ),
                "recommended_reorder_quantity": round(
                    reorder_quantity
                )
            })

        elif (
            days_until_stockout is not None
            and days_until_stockout <= 7
        ):

            alerts.append({
                "product_id": product_id,
                "product_name": product_name,
                "alert_type": "LOW_STOCK",
                "priority": "MEDIUM",
                "message": (
                    f"{product_name} has low stock "
                    f"and may run out in approximately "
                    f"{round(days_until_stockout, 1)} days."
                ),
                "current_stock": current_stock,
                "days_until_stockout": round(
                    days_until_stockout,
                    2
                ),
                "recommended_reorder_quantity": round(
                    reorder_quantity
                )
            })

        elif reorder_quantity > 0:

            alerts.append({
                "product_id": product_id,
                "product_name": product_name,
                "alert_type": "REORDER_RECOMMENDED",
                "priority": "MEDIUM",
                "message": (
                    f"{product_name} should be reordered."
                ),
                "current_stock": current_stock,
                "days_until_stockout": (
                    round(days_until_stockout, 2)
                    if days_until_stockout is not None
                    else None
                ),
                "recommended_reorder_quantity": round(
                    reorder_quantity
                )
            })

    return alerts
