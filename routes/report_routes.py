from flask import Blueprint, jsonify
from database import get_db_connection
from flask_jwt_extended import jwt_required, get_jwt_identity

report_bp = Blueprint("report_bp", __name__)

# CURRENT INVENTORY REPORT

@report_bp.route("/reports/current-inventory", methods=["GET"])
@jwt_required()
def current_inventory_report():
    """
    Generates a current inventory valuation report for the active store owner.
    """
    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    sql = """
        SELECT
            products.product_id,
            products.product_name,
            categories.category_name,
            products.price,
            inventory.stock_quantity,
            (products.price * inventory.stock_quantity) AS total_value
        FROM products
        LEFT JOIN categories
            ON products.category_id = categories.category_id
        LEFT JOIN inventory
            ON products.product_id = inventory.product_id
        WHERE products.store_id = %s
        ORDER BY products.product_name
    """

    cursor.execute(sql, (current_store_id,))
    inventory = cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify(inventory)

# SALES HISTORY REPORT

@report_bp.route("/reports/sales-history", methods=["GET"])
@jwt_required()
def sales_history_report():
    """
    Generates a detailed chronological sales breakdown report for the active store owner.
    """
    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    sql = """
        SELECT
            sales.sale_id,
            products.product_name,
            sale_items.quantity,
            sale_items.price,
            sale_items.subtotal,
            sales.sale_date,
            sales.total_sales
        FROM sales
        JOIN sale_items
            ON sales.sale_id = sale_items.sale_id
        JOIN products
            ON sale_items.product_id = products.product_id
        WHERE sales.store_id = %s
        ORDER BY sales.sale_date DESC,
                 sales.sale_id DESC
    """

    cursor.execute(sql, (current_store_id,))
    sales = cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify(sales)

# STOCK MOVEMENT REPORT

@report_bp.route("/reports/stock-movements", methods=["GET"])
@jwt_required()
def stock_movement_report():
    """
    Generates an inventory ledger audit trail report for the active store owner.
    """
    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    sql = """
        SELECT
            stock_movements.movement_id,
            products.product_id,
            products.product_name,
            stock_movements.movement_type,
            stock_movements.quantity,
            stock_movements.reference_id,
            stock_movements.movement_date
        FROM stock_movements
        JOIN products
            ON stock_movements.product_id = products.product_id
        WHERE products.store_id = %s
        ORDER BY stock_movements.movement_date DESC,
                 stock_movements.movement_id DESC
    """

    cursor.execute(sql, (current_store_id,))
    movements = cursor.fetchall()

    cursor.close()
    db.close()

    return jsonify(movements)
