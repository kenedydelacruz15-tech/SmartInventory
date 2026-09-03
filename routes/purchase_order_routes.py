from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import get_db_connection


purchase_order_bp = Blueprint(
    "purchase_order_bp",
    __name__
)


# Get all purchase orders for the logged-in store.
@purchase_order_bp.route("/purchase-orders", methods=["GET"])
@jwt_required()
def get_purchase_orders():

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                po.purchase_order_id,
                po.supplier_id,
                s.supplier_name,
                po.status,
                po.order_date,
                po.notes,

                COUNT(poi.purchase_order_item_id) AS item_count,

                COALESCE(
                    SUM(poi.ordered_quantity),
                    0
                ) AS total_ordered_quantity,

                COALESCE(
                    SUM(poi.received_quantity),
                    0
                ) AS total_received_quantity

            FROM purchase_orders po

            JOIN suppliers s
                ON po.supplier_id = s.supplier_id

            LEFT JOIN purchase_order_items poi
                ON po.purchase_order_id = poi.purchase_order_id

            WHERE po.store_id = %s

            GROUP BY
                po.purchase_order_id,
                po.supplier_id,
                s.supplier_name,
                po.status,
                po.order_date,
                po.notes

            ORDER BY po.purchase_order_id DESC
            """,
            (current_store_id,)
        )

        purchase_orders = cursor.fetchall()

        return jsonify({
            "purchase_order_count": len(purchase_orders),
            "purchase_orders": purchase_orders
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()


# Get one purchase order with detailed item receiving status.
@purchase_order_bp.route(
    "/purchase-orders/<int:purchase_order_id>",
    methods=["GET"]
)
@jwt_required()
def get_purchase_order(purchase_order_id):

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Get the purchase order and supplier information.
        cursor.execute(
            """
            SELECT
                po.purchase_order_id,
                po.supplier_id,
                s.supplier_name,
                po.status,
                po.order_date,
                po.notes

            FROM purchase_orders po

            JOIN suppliers s
                ON po.supplier_id = s.supplier_id

            WHERE po.purchase_order_id = %s
              AND po.store_id = %s
            """,
            (
                purchase_order_id,
                current_store_id
            )
        )

        purchase_order = cursor.fetchone()

        if not purchase_order:

            return jsonify({
                "error": "Purchase order not found."
            }), 404

        # Get all products and their receiving progress.
        cursor.execute(
            """
            SELECT
                poi.purchase_order_item_id,
                poi.product_id,
                p.product_name,
                p.barcode,
                poi.ordered_quantity,
                poi.received_quantity,
                poi.purchase_price,

                (
                    poi.ordered_quantity
                    - poi.received_quantity
                ) AS remaining_quantity,

                CASE

                    WHEN poi.received_quantity = 0
                        THEN 'NOT_RECEIVED'

                    WHEN poi.received_quantity <
                         poi.ordered_quantity
                        THEN 'PARTIALLY_RECEIVED'

                    WHEN poi.received_quantity >=
                         poi.ordered_quantity
                        THEN 'RECEIVED'

                END AS receiving_status

            FROM purchase_order_items poi

            JOIN products p
                ON poi.product_id = p.product_id

            WHERE poi.purchase_order_id = %s
              AND p.store_id = %s

            ORDER BY poi.purchase_order_item_id ASC
            """,
            (
                purchase_order_id,
                current_store_id
            )
        )

        items = cursor.fetchall()

        total_items = len(items)

        fully_received_items = sum(
            1
            for item in items
            if item["received_quantity"]
            >= item["ordered_quantity"]
        )

        partially_received_items = sum(
            1
            for item in items
            if item["received_quantity"] > 0
            and item["received_quantity"]
            < item["ordered_quantity"]
        )

        pending_items = sum(
            1
            for item in items
            if item["received_quantity"] == 0
        )

        purchase_order["total_items"] = total_items

        purchase_order["fully_received_items"] = (
            fully_received_items
        )

        purchase_order["partially_received_items"] = (
            partially_received_items
        )

        purchase_order["pending_items"] = pending_items

        purchase_order["items"] = items

        return jsonify(purchase_order), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()


# Create a new purchase order with multiple products.
@purchase_order_bp.route(
    "/purchase-orders",
    methods=["POST"]
)
@jwt_required()
def create_purchase_order():

    current_store_id = get_jwt_identity()

    data = request.get_json() or {}

    supplier_id = data.get("supplier_id")
    notes = data.get("notes")
    items = data.get("items")

    if not supplier_id:

        return jsonify({
            "error": "supplier_id is required."
        }), 400

    if not items or not isinstance(items, list):

        return jsonify({
            "error": "At least one item is required."
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Verify that the supplier belongs to this store.
        cursor.execute(
            """
            SELECT supplier_id
            FROM suppliers
            WHERE supplier_id = %s
              AND store_id = %s
            """,
            (
                supplier_id,
                current_store_id
            )
        )

        supplier = cursor.fetchone()

        if not supplier:

            return jsonify({
                "error": "Supplier not found."
            }), 404

        # Create the main purchase order.
        cursor.execute(
            """
            INSERT INTO purchase_orders
            (
                supplier_id,
                store_id,
                status,
                notes
            )
            VALUES
            (
                %s,
                %s,
                'PENDING',
                %s
            )
            """,
            (
                supplier_id,
                current_store_id,
                notes
            )
        )

        purchase_order_id = cursor.lastrowid

        created_items = []

        for item in items:

            product_id = item.get("product_id")
            ordered_quantity = item.get(
                "ordered_quantity"
            )

            purchase_price = item.get(
                "purchase_price"
            )

            if not product_id:

                raise Exception(
                    "product_id is required."
                )

            if not ordered_quantity:

                raise Exception(
                    "ordered_quantity is required."
                )

            if ordered_quantity <= 0:

                raise Exception(
                    "ordered_quantity must be greater than 0."
                )

            # Verify product ownership.
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

                raise Exception(
                    f"Product ID {product_id} not found."
                )

            # Add the product to the purchase order.
            cursor.execute(
                """
                INSERT INTO purchase_order_items
                (
                    purchase_order_id,
                    product_id,
                    ordered_quantity,
                    purchase_price
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    purchase_order_id,
                    product_id,
                    ordered_quantity,
                    purchase_price
                )
            )

            purchase_order_item_id = cursor.lastrowid

            created_items.append({
                "purchase_order_item_id":
                    purchase_order_item_id,

                "product_id":
                    product_id,

                "product_name":
                    product["product_name"],

                "ordered_quantity":
                    ordered_quantity,

                "purchase_price":
                    purchase_price
            })

        db.commit()

        return jsonify({
            "message":
                "Purchase order created successfully.",

            "purchase_order_id":
                purchase_order_id,

            "status":
                "PENDING",

            "items":
                created_items
        }), 201

    except Exception as e:

        db.rollback()

        return jsonify({
            "error": str(e)
        }), 400

    finally:

        cursor.close()
        db.close()


# Update the status of a purchase order.
@purchase_order_bp.route(
    "/purchase-orders/<int:purchase_order_id>/status",
    methods=["PUT"]
)
@jwt_required()
def update_purchase_order_status(purchase_order_id):

    current_store_id = get_jwt_identity()

    data = request.get_json() or {}

    status = data.get("status")

    allowed_statuses = [
        "PENDING",
        "ORDERED",
        "PARTIALLY_RECEIVED",
        "RECEIVED",
        "CANCELLED"
    ]

    if status not in allowed_statuses:

        return jsonify({
            "error": "Invalid purchase order status."
        }), 400

    db = get_db_connection()
    cursor = db.cursor()

    try:

        cursor.execute(
            """
            UPDATE purchase_orders

            SET status = %s

            WHERE purchase_order_id = %s
              AND store_id = %s
            """,
            (
                status,
                purchase_order_id,
                current_store_id
            )
        )

        if cursor.rowcount == 0:

            return jsonify({
                "error": "Purchase order not found."
            }), 404

        db.commit()

        return jsonify({
            "message":
                "Purchase order status updated successfully.",

            "purchase_order_id":
                purchase_order_id,

            "status":
                status
        }), 200

    except Exception as e:

        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()


# Cancel a purchase order that belongs to the logged-in store.
@purchase_order_bp.route(
    "/purchase-orders/<int:purchase_order_id>/cancel",
    methods=["PUT"]
)
@jwt_required()
def cancel_purchase_order(purchase_order_id):

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Check the purchase order before cancelling.
        cursor.execute(
            """
            SELECT
                status
            FROM purchase_orders

            WHERE purchase_order_id = %s
              AND store_id = %s
            """,
            (
                purchase_order_id,
                current_store_id
            )
        )

        purchase_order = cursor.fetchone()

        if not purchase_order:

            return jsonify({
                "error": "Purchase order not found."
            }), 404

        if purchase_order["status"] == "RECEIVED":

            return jsonify({
                "error":
                    "A fully received purchase order cannot be cancelled."
            }), 400

        cursor.execute(
            """
            UPDATE purchase_orders

            SET status = 'CANCELLED'

            WHERE purchase_order_id = %s
              AND store_id = %s
            """,
            (
                purchase_order_id,
                current_store_id
            )
        )

        db.commit()

        return jsonify({
            "message":
                "Purchase order cancelled successfully."
        }), 200

    except Exception as e:

        db.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()


# Receive products from a supplier purchase order.
@purchase_order_bp.route(
    "/purchase-orders/<int:purchase_order_id>/receive",
    methods=["POST"]
)
@jwt_required()
def receive_purchase_order(purchase_order_id):

    current_store_id = get_jwt_identity()

    data = request.get_json() or {}

    items = data.get("items")

    if not items or not isinstance(items, list):

        return jsonify({
            "error": "Items are required."
        }), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Lock and verify the purchase order.
        cursor.execute(
            """
            SELECT
                purchase_order_id,
                supplier_id,
                status

            FROM purchase_orders

            WHERE purchase_order_id = %s
              AND store_id = %s

            FOR UPDATE
            """,
            (
                purchase_order_id,
                current_store_id
            )
        )

        purchase_order = cursor.fetchone()

        if not purchase_order:

            return jsonify({
                "error": "Purchase order not found."
            }), 404

        if purchase_order["status"] == "CANCELLED":

            return jsonify({
                "error":
                    "Cancelled purchase orders cannot receive stock."
            }), 400

        if purchase_order["status"] == "RECEIVED":

            return jsonify({
                "error":
                    "Purchase order has already been fully received."
            }), 400

        supplier_id = purchase_order["supplier_id"]

        received_items = []

        for item in items:

            purchase_order_item_id = item.get(
                "purchase_order_item_id"
            )

            received_quantity = item.get(
                "received_quantity"
            )

            expiry_date = item.get(
                "expiry_date"
            )

            if not purchase_order_item_id:

                raise Exception(
                    "purchase_order_item_id is required."
                )

            if received_quantity is None:

                raise Exception(
                    "received_quantity is required."
                )

            if received_quantity <= 0:

                raise Exception(
                    "received_quantity must be greater than 0."
                )

            if not expiry_date:

                raise Exception(
                    "expiry_date is required."
                )

            # Lock and verify the purchase order item.
            cursor.execute(
                """
                SELECT
                    poi.purchase_order_item_id,
                    poi.product_id,
                    poi.ordered_quantity,
                    poi.received_quantity,
                    poi.purchase_price,
                    p.product_name

                FROM purchase_order_items poi

                JOIN products p
                    ON poi.product_id = p.product_id

                WHERE poi.purchase_order_item_id = %s
                  AND poi.purchase_order_id = %s
                  AND p.store_id = %s

                FOR UPDATE
                """,
                (
                    purchase_order_item_id,
                    purchase_order_id,
                    current_store_id
                )
            )

            purchase_item = cursor.fetchone()

            if not purchase_item:

                raise Exception(
                    f"Purchase order item "
                    f"{purchase_order_item_id} not found."
                )

            product_id = purchase_item["product_id"]

            product_name = purchase_item["product_name"]

            remaining_quantity = (
                purchase_item["ordered_quantity"]
                - purchase_item["received_quantity"]
            )

            if received_quantity > remaining_quantity:

                raise Exception(
                    f"Cannot receive {received_quantity} units of "
                    f"{product_name}. Only "
                    f"{remaining_quantity} remaining."
                )

            purchase_price = purchase_item["purchase_price"]

            if purchase_price is None:

                raise Exception(
                    f"Purchase price is missing for "
                    f"{product_name}."
                )

            # Update the received quantity of the PO item.
            cursor.execute(
                """
                UPDATE purchase_order_items

                SET received_quantity =
                    received_quantity + %s

                WHERE purchase_order_item_id = %s
                """,
                (
                    received_quantity,
                    purchase_order_item_id
                )
            )

            # Create a stock-in transaction.
            cursor.execute(
                """
                INSERT INTO stock_in
                (
                    product_id,
                    supplier_id,
                    quantity,
                    purchase_price
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    product_id,
                    supplier_id,
                    received_quantity,
                    purchase_price
                )
            )

            stock_in_id = cursor.lastrowid

            # Create an inventory batch with expiry information.
            cursor.execute(
                """
                INSERT INTO batches
                (
                    product_id,
                    quantity,
                    purchase_price,
                    expiry_date,
                    store_id
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    product_id,
                    received_quantity,
                    purchase_price,
                    expiry_date,
                    current_store_id
                )
            )

            batch_id = cursor.lastrowid

            # Check whether inventory already exists.
            cursor.execute(
                """
                SELECT
                    inventory_id

                FROM inventory

                WHERE product_id = %s

                FOR UPDATE
                """,
                (product_id,)
            )

            inventory = cursor.fetchone()

            if inventory:

                # Increase existing inventory.
                cursor.execute(
                    """
                    UPDATE inventory

                    SET stock_quantity =
                        stock_quantity + %s

                    WHERE product_id = %s
                    """,
                    (
                        received_quantity,
                        product_id
                    )
                )

            else:

                # Create inventory for the product.
                cursor.execute(
                    """
                    INSERT INTO inventory
                    (
                        product_id,
                        stock_quantity
                    )
                    VALUES
                    (
                        %s,
                        %s
                    )
                    """,
                    (
                        product_id,
                        received_quantity
                    )
                )

            # Record the inventory movement.
            cursor.execute(
                """
                INSERT INTO stock_movements
                (
                    product_id,
                    movement_type,
                    quantity,
                    reference_id
                )
                VALUES
                (
                    %s,
                    'STOCK_IN',
                    %s,
                    %s
                )
                """,
                (
                    product_id,
                    received_quantity,
                    stock_in_id
                )
            )

            # Record detailed purchase order receiving history.
            cursor.execute(
                """
                INSERT INTO purchase_order_receiving_history
                (
                    purchase_order_id,
                    purchase_order_item_id,
                    product_id,
                    received_quantity,
                    purchase_price,
                    expiry_date,
                    stock_in_id,
                    batch_id
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    purchase_order_id,
                    purchase_order_item_id,
                    product_id,
                    received_quantity,
                    purchase_price,
                    expiry_date,
                    stock_in_id,
                    batch_id
                )
            )

            receiving_id = cursor.lastrowid

            received_items.append({
                "receiving_id":
                    receiving_id,

                "purchase_order_item_id":
                    purchase_order_item_id,

                "product_id":
                    product_id,

                "product_name":
                    product_name,

                "received_quantity":
                    received_quantity,

                "stock_in_id":
                    stock_in_id,

                "batch_id":
                    batch_id,

                "expiry_date":
                    expiry_date
            })

        # Check whether all PO items are completely received.
        cursor.execute(
            """
            SELECT
                COUNT(*) AS remaining_items

            FROM purchase_order_items

            WHERE purchase_order_id = %s
              AND received_quantity < ordered_quantity
            """,
            (purchase_order_id,)
        )

        result = cursor.fetchone()

        if result["remaining_items"] == 0:

            new_status = "RECEIVED"

        else:

            new_status = "PARTIALLY_RECEIVED"

        # Update the overall purchase order status.
        cursor.execute(
            """
            UPDATE purchase_orders

            SET status = %s

            WHERE purchase_order_id = %s
              AND store_id = %s
            """,
            (
                new_status,
                purchase_order_id,
                current_store_id
            )
        )

        db.commit()

        return jsonify({
            "message":
                "Purchase order received successfully.",

            "purchase_order_id":
                purchase_order_id,

            "status":
                new_status,

            "received_items":
                received_items
        }), 200

    except Exception as e:

        db.rollback()

        return jsonify({
            "error": str(e)
        }), 400

    finally:

        cursor.close()
        db.close()


# Get complete receiving history for one purchase order.
@purchase_order_bp.route(
    "/purchase-orders/<int:purchase_order_id>/receiving-history",
    methods=["GET"]
)
@jwt_required()
def get_purchase_order_receiving_history(purchase_order_id):

    current_store_id = get_jwt_identity()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:

        # Verify that the purchase order belongs to this store.
        cursor.execute(
            """
            SELECT
                purchase_order_id,
                supplier_id,
                status

            FROM purchase_orders

            WHERE purchase_order_id = %s
              AND store_id = %s
            """,
            (
                purchase_order_id,
                current_store_id
            )
        )

        purchase_order = cursor.fetchone()

        if not purchase_order:

            return jsonify({
                "error": "Purchase order not found."
            }), 404

        # Get every receiving transaction for this PO.
        cursor.execute(
            """
            SELECT
                porh.receiving_id,
                porh.purchase_order_id,
                porh.purchase_order_item_id,

                porh.product_id,
                p.product_name,
                p.barcode,

                porh.received_quantity,
                porh.purchase_price,
                porh.expiry_date,

                porh.stock_in_id,
                porh.batch_id,

                porh.received_date

            FROM purchase_order_receiving_history porh

            JOIN products p
                ON porh.product_id = p.product_id

            WHERE porh.purchase_order_id = %s
              AND p.store_id = %s

            ORDER BY
                porh.received_date DESC,
                porh.receiving_id DESC
            """,
            (
                purchase_order_id,
                current_store_id
            )
        )

        receiving_history = cursor.fetchall()

        return jsonify({
            "purchase_order_id":
                purchase_order_id,

            "purchase_order_status":
                purchase_order["status"],

            "receiving_count":
                len(receiving_history),

            "receiving_history":
                receiving_history
        }), 200

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        db.close()