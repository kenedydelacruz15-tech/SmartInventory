from database import get_db_connection


def get_reorder_recommendations(store_id):
    """
    Generates inventory replenishment suggestions isolated by store ownership.
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

    recommendations = []

    for product in products:

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

        # Target stock for the next 7 days
        target_stock = average_daily_demand * 7

        # Calculate recommended reorder quantity
        reorder_quantity = target_stock - current_stock

        if reorder_quantity < 0:
            reorder_quantity = 0

        # Determine recommendation status
        if current_stock <= 0:
            status = "REORDER_NOW"

        elif reorder_quantity > 0:
            status = "REORDER_RECOMMENDED"

        else:
            status = "STOCK_SUFFICIENT"

        recommendations.append({
            "product_id": product["product_id"],
            "product_name": product["product_name"],
            "current_stock": current_stock,
            "average_daily_demand": round(
                average_daily_demand,
                2
            ),
            "target_stock_7_days": round(
                target_stock,
                2
            ),
            "recommended_reorder_quantity": round(
                reorder_quantity
            ),
            "status": status
        })

    return recommendations
