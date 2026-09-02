from database import get_db_connection


def get_demand_forecast(store_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Restrict computation rows using products.store_id before grouping
    sql = """
        SELECT
            products.product_id,
            products.product_name,

            COALESCE(
                SUM(sale_items.quantity),
                0
            ) AS total_quantity_sold,

            COUNT(
                DISTINCT DATE(sales.sale_date)
            ) AS sales_days

        FROM products

        LEFT JOIN sale_items
            ON products.product_id = sale_items.product_id

        LEFT JOIN sales
            ON sale_items.sale_id = sales.sale_id

        WHERE products.store_id = %s

        GROUP BY
            products.product_id,
            products.product_name

        ORDER BY
            total_quantity_sold DESC
    """

    cursor.execute(sql, (store_id,))
    products = cursor.fetchall()

    cursor.close()
    db.close()

    forecasts = []

    for product in products:

        total_quantity = product["total_quantity_sold"]
        sales_days = product["sales_days"]

        if sales_days > 0:
            average_daily_demand = total_quantity / sales_days
        else:
            average_daily_demand = 0

        forecasts.append({
            "product_id": product["product_id"],
            "product_name": product["product_name"],
            "total_quantity_sold": total_quantity,
            "sales_days": sales_days,
            "average_daily_demand": round(
                average_daily_demand,
                2
            )
        })

    return forecasts

def get_stockout_predictions(store_id):
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

    predictions = []

    for product in products:

        current_stock = product["stock_quantity"] or 0
        total_quantity_sold = product["total_quantity_sold"] or 0
        sales_days = product["sales_days"] or 0

        # Calculate Average Daily Demand
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

        # Determine status
        if current_stock <= 0:
            status = "OUT_OF_STOCK"

        elif days_until_stockout is not None and days_until_stockout <= 3:
            status = "CRITICAL"

        elif days_until_stockout is not None and days_until_stockout <= 7:
            status = "WARNING"

        else:
            status = "SAFE"

        predictions.append({
            "product_id": product["product_id"],
            "product_name": product["product_name"],
            "current_stock": current_stock,
            "total_quantity_sold": total_quantity_sold,
            "sales_days": sales_days,
            "average_daily_demand": round(
                average_daily_demand,
                2
            ),
            "days_until_stockout": (
                round(days_until_stockout, 2)
                if days_until_stockout is not None
                else None
            ),
            "status": status
        })

    return predictions

def get_forecast_results(store_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    sql = """
        SELECT
            products.product_id,
            products.product_name,
            categories.category_name,

            COALESCE(
                inventory.stock_quantity,
                0
            ) AS current_stock,

            COALESCE(
                SUM(sale_items.quantity),
                0
            ) AS total_quantity_sold,

            COUNT(
                DISTINCT DATE(sales.sale_date)
            ) AS sales_days

        FROM products

        LEFT JOIN categories
            ON products.category_id = categories.category_id

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
            categories.category_name,
            inventory.stock_quantity

        ORDER BY
            products.product_name
    """

    cursor.execute(sql, (store_id,))
    products = cursor.fetchall()

    cursor.close()
    db.close()

    results = []

    for product in products:

        current_stock = product["current_stock"] or 0
        total_quantity_sold = (
            product["total_quantity_sold"] or 0
        )
        sales_days = product["sales_days"] or 0

        # Average Daily Demand
        if sales_days > 0:
            average_daily_demand = (
                total_quantity_sold / sales_days
            )
        else:
            average_daily_demand = 0

        # Days Until Stock-out
        if average_daily_demand > 0:
            days_until_stockout = (
                current_stock / average_daily_demand
            )
        else:
            days_until_stockout = None

        # Forecast status
        if current_stock <= 0:
            forecast_status = "OUT_OF_STOCK"

        elif (
            days_until_stockout is not None
            and days_until_stockout <= 3
        ):
            forecast_status = "CRITICAL"

        elif (
            days_until_stockout is not None
            and days_until_stockout <= 7
        ):
            forecast_status = "WARNING"

        elif average_daily_demand == 0:
            forecast_status = "NO_DEMAND_DATA"

        else:
            forecast_status = "SAFE"

        results.append({
            "product_id": product["product_id"],
            "product_name": product["product_name"],
            "category_name": product["category_name"],
            "current_stock": current_stock,
            "total_quantity_sold": total_quantity_sold,
            "sales_days": sales_days,
            "average_daily_demand": round(
                average_daily_demand,
                2
            ),
            "days_until_stockout": (
                round(days_until_stockout, 2)
                if days_until_stockout is not None
                else None
            ),
            "forecast_status": forecast_status
        })

    return results
