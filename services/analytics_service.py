from database import get_db_connection


def get_best_selling_products(store_id, start_date=None, end_date=None):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    sql = """
        SELECT
            p.product_id,
            p.product_name,
            c.category_name,

            COALESCE(SUM(si.quantity), 0) AS total_quantity_sold,

            COALESCE(SUM(si.subtotal), 0) AS total_sales

        FROM products p

        LEFT JOIN categories c
            ON p.category_id = c.category_id

        LEFT JOIN sale_items si
            ON p.product_id = si.product_id

        LEFT JOIN sales s
            ON si.sale_id = s.sale_id
            AND s.store_id = %s
    """

    params = [store_id]

    conditions = ["p.store_id = %s"]
    params.append(store_id)

    if start_date:
        conditions.append("DATE(s.sale_date) >= %s")
        params.append(start_date)

    if end_date:
        conditions.append("DATE(s.sale_date) <= %s")
        params.append(end_date)

    sql += " WHERE " + " AND ".join(conditions)

    sql += """
        GROUP BY
            p.product_id,
            p.product_name,
            c.category_name

        ORDER BY
            total_quantity_sold DESC,
            total_sales DESC
    """

    cursor.execute(sql, tuple(params))
    products = cursor.fetchall()

    cursor.close()
    db.close()

    return products


def get_slow_moving_products(store_id, start_date=None, end_date=None):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    sql = """
        SELECT
            p.product_id,
            p.product_name,
            c.category_name,

            COALESCE(SUM(si.quantity), 0) AS total_quantity_sold,

            COALESCE(SUM(si.subtotal), 0) AS total_sales,

            COUNT(DISTINCT DATE(s.sale_date)) AS sales_days

        FROM products p

        LEFT JOIN categories c
            ON p.category_id = c.category_id

        LEFT JOIN sale_items si
            ON p.product_id = si.product_id

        LEFT JOIN sales s
            ON si.sale_id = s.sale_id
            AND s.store_id = %s
    """

    params = [store_id]

    conditions = ["p.store_id = %s"]
    params.append(store_id)

    if start_date:
        conditions.append("DATE(s.sale_date) >= %s")
        params.append(start_date)

    if end_date:
        conditions.append("DATE(s.sale_date) <= %s")
        params.append(end_date)

    sql += " WHERE " + " AND ".join(conditions)

    sql += """
        GROUP BY
            p.product_id,
            p.product_name,
            c.category_name

        HAVING total_quantity_sold <= 10

        ORDER BY
            total_quantity_sold ASC,
            total_sales ASC
    """

    cursor.execute(sql, tuple(params))
    products = cursor.fetchall()

    cursor.close()
    db.close()

    return products


def get_daily_sales_trends(store_id, start_date=None, end_date=None):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    sql = """
        SELECT
            DATE(s.sale_date) AS sale_date,

            COALESCE(SUM(si.quantity), 0) AS total_quantity_sold,

            COALESCE(SUM(si.subtotal), 0) AS total_sales

        FROM sales s

        JOIN sale_items si
            ON s.sale_id = si.sale_id

        WHERE s.store_id = %s
    """

    params = [store_id]

    if start_date:
        sql += " AND DATE(s.sale_date) >= %s"
        params.append(start_date)

    if end_date:
        sql += " AND DATE(s.sale_date) <= %s"
        params.append(end_date)

    sql += """
        GROUP BY DATE(s.sale_date)

        ORDER BY sale_date ASC
    """

    cursor.execute(sql, tuple(params))
    trends = cursor.fetchall()

    cursor.close()
    db.close()

    return trends


def get_weekly_sales(store_id, start_date=None, end_date=None):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    sql = """
        SELECT
            YEAR(s.sale_date) AS sales_year,
            WEEK(s.sale_date, 1) AS sales_week,

            COALESCE(SUM(si.quantity), 0) AS total_quantity_sold,

            COALESCE(SUM(si.subtotal), 0) AS total_sales

        FROM sales s

        JOIN sale_items si
            ON s.sale_id = si.sale_id

        WHERE s.store_id = %s
    """

    params = [store_id]

    if start_date:
        sql += " AND DATE(s.sale_date) >= %s"
        params.append(start_date)

    if end_date:
        sql += " AND DATE(s.sale_date) <= %s"
        params.append(end_date)

    sql += """
        GROUP BY
            YEAR(s.sale_date),
            WEEK(s.sale_date, 1)

        ORDER BY
            sales_year ASC,
            sales_week ASC
    """

    cursor.execute(sql, tuple(params))
    sales = cursor.fetchall()

    cursor.close()
    db.close()

    return sales


def get_monthly_sales(store_id, start_date=None, end_date=None):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    sql = """
        SELECT
            YEAR(s.sale_date) AS sales_year,
            MONTH(s.sale_date) AS sales_month,

            COALESCE(SUM(si.quantity), 0) AS total_quantity_sold,

            COALESCE(SUM(si.subtotal), 0) AS total_sales

        FROM sales s

        JOIN sale_items si
            ON s.sale_id = si.sale_id

        WHERE s.store_id = %s
    """

    params = [store_id]

    if start_date:
        sql += " AND DATE(s.sale_date) >= %s"
        params.append(start_date)

    if end_date:
        sql += " AND DATE(s.sale_date) <= %s"
        params.append(end_date)

    sql += """
        GROUP BY
            YEAR(s.sale_date),
            MONTH(s.sale_date)

        ORDER BY
            sales_year ASC,
            sales_month ASC
    """

    cursor.execute(sql, tuple(params))
    sales = cursor.fetchall()

    cursor.close()
    db.close()

    return sales


def get_product_performance(store_id, start_date=None, end_date=None):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    sql = """
        SELECT
            p.product_id,
            p.product_name,
            c.category_name,

            COALESCE(i.stock_quantity, 0) AS current_stock,

            COALESCE(SUM(si.quantity), 0) AS total_quantity_sold,

            COALESCE(SUM(si.subtotal), 0) AS total_sales,

            COUNT(DISTINCT DATE(s.sale_date)) AS sales_days

        FROM products p

        LEFT JOIN categories c
            ON p.category_id = c.category_id

        LEFT JOIN inventory i
            ON p.product_id = i.product_id

        LEFT JOIN sale_items si
            ON p.product_id = si.product_id

        LEFT JOIN sales s
            ON si.sale_id = s.sale_id
            AND s.store_id = %s
    """

    params = [store_id]

    conditions = ["p.store_id = %s"]
    params.append(store_id)

    if start_date:
        conditions.append("DATE(s.sale_date) >= %s")
        params.append(start_date)

    if end_date:
        conditions.append("DATE(s.sale_date) <= %s")
        params.append(end_date)

    sql += " WHERE " + " AND ".join(conditions)

    sql += """
        GROUP BY
            p.product_id,
            p.product_name,
            c.category_name,
            i.stock_quantity

        ORDER BY
            total_sales DESC
    """

    cursor.execute(sql, tuple(params))
    products = cursor.fetchall()

    cursor.close()
    db.close()

    performance = []

    for product in products:

        current_stock = product["current_stock"] or 0
        total_quantity_sold = product["total_quantity_sold"] or 0
        total_sales = product["total_sales"] or 0
        sales_days = product["sales_days"] or 0

        # Average daily demand
        if sales_days > 0:
            average_daily_demand = (
                total_quantity_sold / sales_days
            )
        else:
            average_daily_demand = 0

        # Days until stockout
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

        # Product status
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