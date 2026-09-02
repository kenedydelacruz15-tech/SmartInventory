from database import get_db_connection

def get_best_selling_products(store_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    sql = """
        SELECT
            products.product_id,
            products.product_name,
            categories.category_name,

            COALESCE(
                SUM(sale_items.quantity),
                0
            ) AS total_quantity_sold,

            COALESCE(
                SUM(sale_items.subtotal),
                0
            ) AS total_sales

        FROM products

        LEFT JOIN categories
            ON products.category_id = categories.category_id

        LEFT JOIN sale_items
            ON products.product_id = sale_items.product_id

        WHERE products.store_id = %s

        GROUP BY
            products.product_id,
            products.product_name,
            categories.category_name

        ORDER BY
            total_quantity_sold DESC,
            total_sales DESC
    """

    cursor.execute(sql, (store_id,))
    products = cursor.fetchall()

    cursor.close()
    db.close()

    return products

def get_slow_moving_products(store_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    sql = """
        SELECT
            products.product_id,
            products.product_name,
            categories.category_name,

            COALESCE(
                SUM(sale_items.quantity),
                0
            ) AS total_quantity_sold,

            COALESCE(
                SUM(sale_items.subtotal),
                0
            ) AS total_sales,

            COUNT(
                DISTINCT DATE(sales.sale_date)
            ) AS sales_days

        FROM products

        LEFT JOIN categories
            ON products.category_id = categories.category_id

        LEFT JOIN sale_items
            ON products.product_id = sale_items.product_id

        LEFT JOIN sales
            ON sale_items.sale_id = sales.sale_id

        WHERE products.store_id = %s

        GROUP BY
            products.product_id,
            products.product_name,
            categories.category_name

        HAVING total_quantity_sold <= 10

        ORDER BY
            total_quantity_sold ASC,
            total_sales ASC
    """

    cursor.execute(sql, (store_id,))
    products = cursor.fetchall()

    cursor.close()
    db.close()

    return products

def get_daily_sales_trends(store_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    sql = """
        SELECT
            DATE(sales.sale_date) AS sale_date,

            COALESCE(
                SUM(sale_items.quantity),
                0
            ) AS total_quantity_sold,

            COALESCE(
                SUM(sale_items.subtotal),
                0
            ) AS total_sales

        FROM sales

        JOIN sale_items
            ON sales.sale_id = sale_items.sale_id

        WHERE sales.store_id = %s

        GROUP BY
            DATE(sales.sale_date)

        ORDER BY
            sale_date ASC
    """

    cursor.execute(sql, (store_id,))
    trends = cursor.fetchall()

    cursor.close()
    db.close()

    return trends

def get_weekly_sales(store_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    sql = """
        SELECT
            YEAR(sales.sale_date) AS sales_year,
            WEEK(sales.sale_date, 1) AS sales_week,

            COALESCE(
                SUM(sale_items.quantity),
                0
            ) AS total_quantity_sold,

            COALESCE(
                SUM(sale_items.subtotal),
                0
            ) AS total_sales

        FROM sales

        JOIN sale_items
            ON sales.sale_id = sale_items.sale_id

        WHERE sales.store_id = %s

        GROUP BY
            YEAR(sales.sale_date),
            WEEK(sales.sale_date, 1)

        ORDER BY
            sales_year ASC,
            sales_week ASC
    """

    cursor.execute(sql, (store_id,))
    weekly_sales = cursor.fetchall()

    cursor.close()
    db.close()

    return weekly_sales

def get_monthly_sales(store_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    sql = """
        SELECT
            YEAR(sales.sale_date) AS sales_year,
            MONTH(sales.sale_date) AS sales_month,

            COALESCE(
                SUM(sale_items.quantity),
                0
            ) AS total_quantity_sold,

            COALESCE(
                SUM(sale_items.subtotal),
                0
            ) AS total_sales

        FROM sales

        JOIN sale_items
            ON sales.sale_id = sale_items.sale_id

        WHERE sales.store_id = %s

        GROUP BY
            YEAR(sales.sale_date),
            MONTH(sales.sale_date)

        ORDER BY
            sales_year ASC,
            sales_month ASC
    """

    cursor.execute(sql, (store_id,))
    monthly_sales = cursor.fetchall()

    cursor.close()
    db.close()

    return monthly_sales

def get_product_performance(store_id):
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

            COALESCE(
                SUM(sale_items.subtotal),
                0
            ) AS total_sales,

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
            total_sales DESC
    """

    cursor.execute(sql, (store_id,))
    products = cursor.fetchall()

    cursor.close()
    db.close()

    performance = []

    for product in products:

        current_stock = product["current_stock"] or 0
        total_quantity_sold = product["total_quantity_sold"] or 0
        total_sales = product["total_sales"] or 0
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

        # 7-day target stock
        target_stock = average_daily_demand * 7

        # Recommended reorder quantity
        reorder_quantity = target_stock - current_stock

        if reorder_quantity < 0:
            reorder_quantity = 0

        # Performance status
        if current_stock <= 0:
            status = "OUT_OF_STOCK"

        elif (
            days_until_stockout is not None
            and days_until_stockout <= 3
        ):
            status = "CRITICAL"

        elif (
            days_until_stockout is not None
            and days_until_stockout <= 7
        ):
            status = "LOW_STOCK"

        elif total_quantity_sold == 0:
            status = "NO_SALES"

        elif reorder_quantity > 0:
            status = "REORDER_RECOMMENDED"

        else:
            status = "GOOD"

        performance.append({
            "product_id": product["product_id"],
            "product_name": product["product_name"],
            "category_name": product["category_name"],
            "current_stock": current_stock,
            "total_quantity_sold": total_quantity_sold,
            "total_sales": float(total_sales),
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
            "target_stock_7_days": round(
                target_stock,
                2
            ),
            "recommended_reorder_quantity": round(
                reorder_quantity
            ),
            "status": status
        })

    return performance
