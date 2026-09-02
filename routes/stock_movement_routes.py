from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import get_db_connection


stock_movement_bp = Blueprint(
    "stock_movement_bp",
    __name__
)


# Get detailed transaction information based on movement type.
def get_transaction_details(
    cursor,
    movement_type,
    reference_id,
    current_store_id
):

    if reference_id is None:
        return {
            "transaction_type": movement_type,
            "message": "No reference record available."
        }

    # Get STOCK_IN transaction details.
    if movement_type == "STOCK_IN":

        cursor.execute(
            """
            SELECT
                si.stock_in_id,
                si.product_id,
                si.quantity,
                si.purchase_price,
                si.stock_in_date,
                sup.supplier_id,
                sup.supplier_name
            FROM stock_in si
            LEFT JOIN suppliers sup
                ON si.supplier_id = sup.supplier_id
            JOIN products p
                ON si.product_id = p.product_id
            WHERE si.stock_in_id = %s
              AND p.store_id = %s
            """,
            (
                reference_id,
                current_store_id
            )
        )

        stock_in = cursor.fetchone()

        if stock_in:
            return {
                "transaction_type": "STOCK_IN",
                "stock_in_id": stock_in["stock_in_id"],
                "supplier_id": stock_in["supplier_id"],
                "supplier_name": stock_in["supplier_name"],
                "purchase_price": (
                    float(stock_in["purchase_price"])
                    if stock_in["purchase_price"] is not None
                    else None
                ),
                "transaction_quantity": stock_in["quantity"],
                "stock_in_date": stock_in["stock_in_date"]
            }

        return {
            "transaction_type": "STOCK_IN",
            "message": "Referenced stock-in record not found."
        }

    # Get SALE transaction details.
    elif movement_type == "SALE":

        cursor.execute(
            """
            SELECT
                si.sale_item_id,
                si.sale_id,
                si.product_id,
                si.quantity,
                si.price,
                si.subtotal,
                s.total_sales,
                s.sale_date
            FROM sale_items si
            JOIN sales s
                ON si.sale_id = s.sale_id
            WHERE si.sale_item_id = %s
              AND s.store_id = %s
            """,
            (
                reference_id,
                current_store_id
            )
        )

        sale_item = cursor.fetchone()

        if sale_item:
            return {
                "transaction_type": "SALE",
                "sale_item_id": sale_item["sale_item_id"],
                "sale_id": sale_item["sale_id"],
                "price": (
                    float(sale_item["price"])
                    if sale_item["price"] is not None
                    else None
                ),
                "subtotal": (
                    float(sale_item["subtotal"])
                    if sale_item["subtotal"] is not None
                    else None
                ),
                "transaction_quantity": sale_item["quantity"],
                "invoice_total": (
                    float(sale_item["total_sales"])
                    if sale_item["total_sales"] is not None
                    else None
                ),
                "sale_date": sale_item["sale_date"]
            }

        return {
            "transaction_type": "SALE",
            "message": "Referenced sale item not found."
        }

    # Get STOCK_OUT transaction details.
    elif movement_type == "STOCK_OUT":

        cursor.execute(
            """
            SELECT
                so.stock_out_id,
                so.product_id,
                so.quantity,
                so.reason,
                so.stock_out_date
            FROM stock_out so
            JOIN products p
                ON so.product_id = p.product_id
            WHERE so.stock_out_id = %s
              AND p.store_id = %s
            """,
            (
                reference_id,
                current_store_id
            )
        )

        stock_out = cursor.fetchone()

        if stock_out:
            return {
                "transaction_type": "STOCK_OUT",
                "stock_out_id": stock_out["stock_out_id"],
                "reason": stock_out["reason"],
                "transaction_quantity": stock_out["quantity"],
                "stock_out_date": stock_out["stock_out_date"]
            }

        return {
            "transaction_type": "STOCK_OUT",
            "message": "Referenced stock-out record not found."
        }

    return {
        "transaction_type": movement_type,
        "message": "Unknown movement type."
    }


# Format one stock movement into a complete inventory audit record.
def format_movement(
    cursor,
    movement,
    current_store_id
):

    movement_type = movement["movement_type"]

    if movement_type == "STOCK_IN":
        stock_change = movement["quantity"]
    else:
        stock_change = -movement["quantity"]

    transaction_details = get_transaction_details(
        cursor,
        movement_type,
        movement["reference_id"],
        current_store_id
    )

    return {
        "movement_id": movement["movement_id"],
        "product_id": movement["product_id"],
        "product_name": movement["product_name"],
        "movement_type": movement_type,
        "quantity": movement["quantity"],
        "stock_change": stock_change,
        "reference_id": movement["reference_id"],
        "movement_date": movement["movement_date"],
        "transaction_details": transaction_details
    }


# Get stock movements with filters and pagination.
@stock_movement_bp.route(
    "/stock-movements",
    methods=["GET"]
)
@jwt_required()
def get_stock_movements():

    current_store_id = get_jwt_identity()

    page = request.args.get(
        "page",
        default=1,
        type=int
    )

    per_page = request.args.get(
        "per_page",
        default=20,
        type=int
    )

    product_id = request.args.get(
        "product_id",
        type=int
    )

    movement_type = request.args.get(
        "movement_type",
        type=str
    )

    start_date = request.args.get(
        "start_date",
        type=str
    )

    end_date = request.args.get(
        "end_date",
        type=str
    )

    # Prevent invalid page values.
    if page < 1:
        page = 1

    # Limit records returned per request.
    if per_page < 1:
        per_page = 20

    if per_page > 100:
        per_page = 100

    # Validate movement type.
    allowed_movement_types = [
        "STOCK_IN",
        "SALE",
        "STOCK_OUT"
    ]

    if (
        movement_type
        and movement_type not in allowed_movement_types
    ):
        return jsonify({
            "error": "Invalid movement_type.",
            "allowed_values": allowed_movement_types
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Build the query dynamically based on selected filters.
        where_conditions = [
            "p.store_id = %s"
        ]

        parameters = [
            current_store_id
        ]

        if product_id:

            where_conditions.append(
                "sm.product_id = %s"
            )

            parameters.append(
                product_id
            )

        if movement_type:

            where_conditions.append(
                "sm.movement_type = %s"
            )

            parameters.append(
                movement_type
            )

        if start_date:

            where_conditions.append(
                "DATE(sm.movement_date) >= %s"
            )

            parameters.append(
                start_date
            )

        if end_date:

            where_conditions.append(
                "DATE(sm.movement_date) <= %s"
            )

            parameters.append(
                end_date
            )

        where_clause = " AND ".join(
            where_conditions
        )

        # Count total records before pagination.
        count_sql = f"""
            SELECT
                COUNT(*) AS total_records
            FROM stock_movements sm
            JOIN products p
                ON sm.product_id = p.product_id
            WHERE {where_clause}
        """

        cursor.execute(
            count_sql,
            tuple(parameters)
        )

        total_records = cursor.fetchone()[
            "total_records"
        ]

        total_pages = (
            (total_records + per_page - 1)
            // per_page
        )

        offset = (
            (page - 1) * per_page
        )

        # Get the filtered movement records.
        sql = f"""
            SELECT
                sm.movement_id,
                sm.product_id,
                p.product_name,
                sm.movement_type,
                sm.quantity,
                sm.reference_id,
                sm.movement_date
            FROM stock_movements sm
            JOIN products p
                ON sm.product_id = p.product_id
            WHERE {where_clause}
            ORDER BY
                sm.movement_date DESC,
                sm.movement_id DESC
            LIMIT %s OFFSET %s
        """

        query_parameters = (
            parameters
            + [per_page, offset]
        )

        cursor.execute(
            sql,
            tuple(query_parameters)
        )

        movements = cursor.fetchall()

        formatted_movements = []

        for movement in movements:

            formatted_movements.append(
                format_movement(
                    cursor,
                    movement,
                    current_store_id
                )
            )

        return jsonify({

            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_records": total_records,
                "total_pages": total_pages
            },

            "filters": {
                "product_id": product_id,
                "movement_type": movement_type,
                "start_date": start_date,
                "end_date": end_date
            },

            "movement_count": len(
                formatted_movements
            ),

            "movements": formatted_movements

        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()


# Get all movements for one specific product.
@stock_movement_bp.route(
    "/stock-movements/product/<int:product_id>",
    methods=["GET"]
)
@jwt_required()
def get_product_stock_movements(product_id):

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Check that the product belongs to the logged-in store.
        cursor.execute(
            """
            SELECT
                product_id,
                product_name
            FROM products
            WHERE product_id = %s
              AND store_id = %s
            """,
            (
                product_id,
                current_store_id
            )
        )

        product = cursor.fetchone()

        if not product:

            return jsonify({
                "error": "Product not found or unauthorized."
            }), 404

        cursor.execute(
            """
            SELECT
                sm.movement_id,
                sm.product_id,
                p.product_name,
                sm.movement_type,
                sm.quantity,
                sm.reference_id,
                sm.movement_date
            FROM stock_movements sm
            JOIN products p
                ON sm.product_id = p.product_id
            WHERE sm.product_id = %s
              AND p.store_id = %s
            ORDER BY
                sm.movement_date DESC,
                sm.movement_id DESC
            """,
            (
                product_id,
                current_store_id
            )
        )

        movements = cursor.fetchall()

        formatted_movements = []

        for movement in movements:

            formatted_movements.append(
                format_movement(
                    cursor,
                    movement,
                    current_store_id
                )
            )

        return jsonify({

            "product_id": product[
                "product_id"
            ],

            "product_name": product[
                "product_name"
            ],

            "movement_count": len(
                formatted_movements
            ),

            "movements": formatted_movements

        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()


# Get one specific stock movement by movement ID.
@stock_movement_bp.route(
    "/stock-movements/<int:movement_id>",
    methods=["GET"]
)
@jwt_required()
def get_specific_stock_movement(movement_id):

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                sm.movement_id,
                sm.product_id,
                p.product_name,
                sm.movement_type,
                sm.quantity,
                sm.reference_id,
                sm.movement_date
            FROM stock_movements sm
            JOIN products p
                ON sm.product_id = p.product_id
            WHERE sm.movement_id = %s
              AND p.store_id = %s
            """,
            (
                movement_id,
                current_store_id
            )
        )

        movement = cursor.fetchone()

        if not movement:

            return jsonify({
                "error": "Stock movement not found or unauthorized."
            }), 404

        formatted_movement = format_movement(
            cursor,
            movement,
            current_store_id
        )

        return jsonify(
            formatted_movement
        ), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()