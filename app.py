import os
from flask import Flask, render_template, request, redirect, url_for, flash
from database.db import (
    init_db,
    # Product functions
    get_all_products,
    get_product_by_id,
    add_product,
    update_product,
    delete_product,
    # Warehouse functions (Module 2)
    get_all_warehouses,
    get_active_warehouses,
    get_warehouse_by_id,
    add_warehouse,
    update_warehouse,
    toggle_warehouse_status,
    delete_warehouse,
    # Stock functions (Module 2)
    get_all_stocks,
    set_product_stock
)
from database.seed import seed_demo_data, clear_demo_data

app = Flask(__name__)
# Secret key required for Flask flash messages
app.secret_key = "stocksense_secret_key_for_hackathon"

# Initialize database tables on app startup
with app.app_context():
    init_db()


# ============================================================================
# ROOT & PRODUCT ROUTES (MODULE 1 + EXTENDED FOR MODULE 2)
# ============================================================================

@app.route("/")
def index():
    """Redirect root path to the Products page."""
    return redirect(url_for("list_products"))


@app.route("/products", methods=["GET"])
def list_products():
    """
    Renders the Products page.
    Supports search query parameter ?q=... to search by name, SKU, or category.
    Calculates summary metrics: total products, low stock count.
    Passes active warehouses for initial stock assignment.
    """
    search_query = request.args.get("q", "").strip()
    products = get_all_products(search_query)
    active_warehouses = get_active_warehouses()

    # Compute statistics for summary badges
    total_products = len(products)
    low_stock_count = sum(
        1 for p in products if p["total_stock"] <= p["reorder_level"]
    )

    return render_template(
        "products.html",
        products=products,
        search_query=search_query,
        total_products=total_products,
        low_stock_count=low_stock_count,
        active_warehouses=active_warehouses
    )


@app.route("/products/add", methods=["POST"])
def create_product():
    """
    Handles Add Product form submission with server-side validation.
    Allows initial stock to be allocated to a selected warehouse without duplication.
    """
    name = request.form.get("name", "").strip()
    sku = request.form.get("sku", "").strip()
    category = request.form.get("category", "").strip()
    unit = request.form.get("unit", "").strip()
    initial_stock_raw = request.form.get("initial_stock", "0").strip()
    reorder_level_raw = request.form.get("reorder_level", "0").strip()
    warehouse_id_raw = request.form.get("warehouse_id", "").strip()

    # 1. Required field validation
    if not name or not sku or not category or not unit or initial_stock_raw == "" or reorder_level_raw == "":
        flash("All fields are required. Please complete the form.", "error")
        return redirect(url_for("list_products"))

    # 2. Number format and non-negative value validation
    try:
        initial_stock = float(initial_stock_raw)
        reorder_level = float(reorder_level_raw)
    except ValueError:
        flash("Initial Stock and Reorder Level must be valid numbers.", "error")
        return redirect(url_for("list_products"))

    if initial_stock < 0:
        flash("Initial Stock cannot be negative.", "error")
        return redirect(url_for("list_products"))

    if reorder_level < 0:
        flash("Reorder Level cannot be negative.", "error")
        return redirect(url_for("list_products"))

    warehouse_id = int(warehouse_id_raw) if warehouse_id_raw.isdigit() else None

    # 3. Add product via database module
    success, message = add_product(
        name=name,
        sku=sku,
        category=category,
        unit=unit,
        initial_stock=initial_stock,
        reorder_level=reorder_level,
        warehouse_id=warehouse_id
    )

    if success:
        flash(message, "success")
    else:
        flash(message, "error")

    return redirect(url_for("list_products"))


@app.route("/products/edit/<int:product_id>", methods=["POST"])
def edit_product(product_id):
    """
    Handles Edit Product form submission with server-side validation.
    """
    existing = get_product_by_id(product_id)
    if not existing:
        flash("Product not found.", "error")
        return redirect(url_for("list_products"))

    name = request.form.get("name", "").strip()
    sku = request.form.get("sku", "").strip()
    category = request.form.get("category", "").strip()
    unit = request.form.get("unit", "").strip()
    reorder_level_raw = request.form.get("reorder_level", "0").strip()

    if not name or not sku or not category or not unit or reorder_level_raw == "":
        flash("All fields are required. Please complete the edit form.", "error")
        return redirect(url_for("list_products"))

    try:
        reorder_level = float(reorder_level_raw)
    except ValueError:
        flash("Reorder Level must be a valid number.", "error")
        return redirect(url_for("list_products"))

    if reorder_level < 0:
        flash("Reorder Level cannot be negative.", "error")
        return redirect(url_for("list_products"))

    success, message = update_product(
        product_id=product_id,
        name=name,
        sku=sku,
        category=category,
        unit=unit,
        initial_stock=existing["total_stock"],
        reorder_level=reorder_level
    )

    if success:
        flash(message, "success")
    else:
        flash(message, "error")

    return redirect(url_for("list_products"))


@app.route("/products/delete/<int:product_id>", methods=["POST"])
def remove_product(product_id):
    """Deletes a product by ID."""
    existing = get_product_by_id(product_id)
    if not existing:
        flash("Product not found or already deleted.", "error")
        return redirect(url_for("list_products"))

    success, message = delete_product(product_id)
    if success:
        flash(f"Product '{existing['name']}' ({existing['sku']}) deleted.", "success")
    else:
        flash(message, "error")

    return redirect(url_for("list_products"))


# ============================================================================
# WAREHOUSE MANAGEMENT ROUTES (MODULE 2)
# ============================================================================

@app.route("/warehouses", methods=["GET"])
def list_warehouses():
    """
    Renders the Warehouses management page.
    Displays warehouse name, code, address, status, distinct products stored,
    total stock units, and management actions.
    """
    search_query = request.args.get("q", "").strip()
    warehouses = get_all_warehouses(search_query)

    total_warehouses = len(warehouses)
    active_count = sum(1 for w in warehouses if w["status"] == "Active")
    inactive_count = total_warehouses - active_count

    return render_template(
        "warehouses.html",
        warehouses=warehouses,
        search_query=search_query,
        total_warehouses=total_warehouses,
        active_count=active_count,
        inactive_count=inactive_count
    )


@app.route("/warehouses/add", methods=["POST"])
def create_warehouse():
    """Handles Add Warehouse form submission."""
    name = request.form.get("name", "").strip()
    code = request.form.get("code", "").strip()
    address = request.form.get("address", "").strip()
    status = request.form.get("status", "Active").strip()

    if not name or not code or not address:
        flash("Warehouse Name, Code, and Address are required.", "error")
        return redirect(url_for("list_warehouses"))

    success, message = add_warehouse(name=name, code=code, address=address, status=status)
    if success:
        flash(message, "success")
    else:
        flash(message, "error")

    return redirect(url_for("list_warehouses"))


@app.route("/warehouses/edit/<int:warehouse_id>", methods=["POST"])
def edit_warehouse(warehouse_id):
    """Handles Edit Warehouse form submission."""
    name = request.form.get("name", "").strip()
    code = request.form.get("code", "").strip()
    address = request.form.get("address", "").strip()
    status = request.form.get("status", "Active").strip()

    if not name or not code or not address:
        flash("Warehouse Name, Code, and Address are required.", "error")
        return redirect(url_for("list_warehouses"))

    success, message = update_warehouse(
        warehouse_id=warehouse_id,
        name=name,
        code=code,
        address=address,
        status=status
    )

    if success:
        flash(message, "success")
    else:
        flash(message, "error")

    return redirect(url_for("list_warehouses"))


@app.route("/warehouses/toggle/<int:warehouse_id>", methods=["POST"])
def toggle_warehouse(warehouse_id):
    """Toggles warehouse between Active and Inactive status."""
    success, message = toggle_warehouse_status(warehouse_id)
    if success:
        flash(message, "success")
    else:
        flash(message, "error")
    return redirect(url_for("list_warehouses"))


@app.route("/warehouses/delete/<int:warehouse_id>", methods=["POST"])
def remove_warehouse(warehouse_id):
    """Deletes a warehouse if it has no stock associated with it."""
    success, message = delete_warehouse(warehouse_id)
    if success:
        flash(message, "success")
    else:
        flash(message, "error")
    return redirect(url_for("list_warehouses"))


# ============================================================================
# STOCK MANAGEMENT ROUTES (MODULE 2)
# ============================================================================

@app.route("/stock", methods=["GET"])
def list_stock():
    """
    Renders the Stock Overview page.
    Displays Product, SKU, Warehouse, Quantity, Unit, Reorder Threshold, and Stock Status.
    Supports filtering by text search (?q=), warehouse (?warehouse_id=), and status (?status=).
    """
    search_query = request.args.get("q", "").strip()
    wh_id_raw = request.args.get("warehouse_id", "").strip()
    status_filter = request.args.get("status", "").strip()

    selected_wh_id = int(wh_id_raw) if wh_id_raw.isdigit() else None
    selected_status = status_filter if status_filter in ["In Stock", "Low Stock", "Out of Stock"] else None

    stocks = get_all_stocks(
        search_query=search_query,
        warehouse_id=selected_wh_id,
        status_filter=selected_status
    )

    all_products = get_all_products()
    all_warehouses = get_all_warehouses()
    active_warehouses = get_active_warehouses()

    # Calculate metrics
    total_units = sum(item["quantity"] for item in stocks)
    in_stock_count = sum(1 for item in stocks if item["stock_status"] == "In Stock")
    low_stock_count = sum(1 for item in stocks if item["stock_status"] == "Low Stock")
    out_of_stock_count = sum(1 for item in stocks if item["stock_status"] == "Out of Stock")

    return render_template(
        "stock.html",
        stocks=stocks,
        products=all_products,
        warehouses=all_warehouses,
        active_warehouses=active_warehouses,
        search_query=search_query,
        selected_wh_id=selected_wh_id,
        selected_status=selected_status,
        total_units=total_units,
        in_stock_count=in_stock_count,
        low_stock_count=low_stock_count,
        out_of_stock_count=out_of_stock_count
    )


@app.route("/stock/update", methods=["POST"])
def update_stock():
    """
    Handles stock allocation/adjustment for a product in a warehouse.
    """
    product_id_raw = request.form.get("product_id", "").strip()
    warehouse_id_raw = request.form.get("warehouse_id", "").strip()
    quantity_raw = request.form.get("quantity", "").strip()

    if not product_id_raw or not warehouse_id_raw or quantity_raw == "":
        flash("Product, Warehouse, and Quantity are required.", "error")
        return redirect(url_for("list_stock"))

    try:
        product_id = int(product_id_raw)
        warehouse_id = int(warehouse_id_raw)
        quantity = float(quantity_raw)
    except ValueError:
        flash("Invalid input format for Product, Warehouse, or Quantity.", "error")
        return redirect(url_for("list_stock"))

    if quantity < 0:
        flash("Stock quantity cannot be negative.", "error")
        return redirect(url_for("list_stock"))

    success, message = set_product_stock(
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity=quantity
    )

    if success:
        flash(message, "success")
    else:
        flash(message, "error")

    return redirect(url_for("list_stock"))


# ============================================================================
# DEMO DATA HELPERS
# ============================================================================

@app.route("/seed", methods=["GET"])
def seed_data():
    """Development helper route to populate demo data easily."""
    count = seed_demo_data()
    flash(f"Populated demo warehouses, products, and {count} stock distributions!", "success")
    return redirect(url_for("list_products"))


@app.route("/clear-demo", methods=["GET"])
def clear_demo():
    """Development helper route to clear demo data easily."""
    deleted = clear_demo_data()
    flash(f"Cleared {deleted} sample demo products and stocks!", "success")
    return redirect(url_for("list_products"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
