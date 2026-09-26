import os
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

from database.db import (
    init_db, today,
    get_user_by_email, get_user_by_id, create_user,
    get_all_warehouses, get_warehouse_by_id, add_warehouse, update_warehouse, toggle_warehouse_status,
    get_all_products, get_products_with_stock, get_product_by_id, get_all_categories,
    add_product, update_product, delete_product,
    get_stock_overview,
    get_all_receipts, create_receipt, confirm_receipt,
    get_all_deliveries, create_delivery, confirm_delivery,
    get_all_transfers, create_transfer, confirm_transfer,
    get_all_adjustments, create_adjustment, confirm_adjustment,
    get_ledger,
    get_dashboard_stats,
)
from database.seed import seed_demo_data, clear_demo_data

app = Flask(__name__)
app.secret_key = "stocksense_secret_key_for_hackathon"

with app.app_context():
    init_db()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_user():
    return {
        "current_user_name": session.get("user_name"),
        "current_user_email": session.get("user_email"),
    }


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "error")
            return render_template("login.html")

        user = get_user_by_email(email)
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_email"] = user["email"]
        flash(f"Welcome back, {user['name']}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not name or not email or not password or not confirm:
            flash("All fields are required.", "error")
            return render_template("signup.html")
        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("signup.html")
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("signup.html")

        success, message = create_user(name, email, generate_password_hash(password))
        flash(message, "success" if success else "error")
        if success:
            return redirect(url_for("login"))
        return render_template("signup.html")

    return render_template("signup.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    stats = get_dashboard_stats()
    warehouses = get_all_warehouses(include_inactive=False)
    categories = get_all_categories()
    return render_template("dashboard.html", stats=stats, warehouses=warehouses, categories=categories)


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

@app.route("/products", methods=["GET"])
@login_required
def list_products():
    search_query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    products = get_products_with_stock(search_query, category)

    total_products = len(get_all_products())
    low_stock_count = sum(1 for p in products if 0 < p["total_stock"] <= p["reorder_level"])
    categories = get_all_categories()
    warehouses = get_all_warehouses(include_inactive=False)

    return render_template(
        "products.html",
        products=products,
        search_query=search_query,
        selected_category=category,
        categories=categories,
        warehouses=warehouses,
        total_products=total_products,
        low_stock_count=low_stock_count,
    )


@app.route("/products/add", methods=["POST"])
@login_required
def create_product():
    name = request.form.get("name", "").strip()
    sku = request.form.get("sku", "").strip()
    category = request.form.get("category", "").strip()
    unit = request.form.get("unit", "").strip()
    initial_stock_raw = request.form.get("initial_stock", "").strip()
    reorder_level_raw = request.form.get("reorder_level", "").strip()
    warehouse_id = request.form.get("warehouse_id", "").strip()

    if not name or not sku or not category or not unit or initial_stock_raw == "" or reorder_level_raw == "":
        flash("All fields are required. Please complete the form.", "error")
        return redirect(url_for("list_products"))

    try:
        initial_stock = float(initial_stock_raw)
        reorder_level = float(reorder_level_raw)
    except ValueError:
        flash("Initial Stock and Reorder Level must be valid numbers.", "error")
        return redirect(url_for("list_products"))

    if initial_stock < 0 or reorder_level < 0:
        flash("Initial Stock and Reorder Level cannot be negative.", "error")
        return redirect(url_for("list_products"))

    success, message = add_product(
        name, sku, category, unit, initial_stock, reorder_level,
        warehouse_id=int(warehouse_id) if warehouse_id else None,
    )
    flash(message, "success" if success else "error")
    return redirect(url_for("list_products"))


@app.route("/products/edit/<int:product_id>", methods=["POST"])
@login_required
def edit_product(product_id):
    existing = get_product_by_id(product_id)
    if not existing:
        flash("Product not found.", "error")
        return redirect(url_for("list_products"))

    name = request.form.get("name", "").strip()
    sku = request.form.get("sku", "").strip()
    category = request.form.get("category", "").strip()
    unit = request.form.get("unit", "").strip()
    reorder_level_raw = request.form.get("reorder_level", "").strip()

    if not name or not sku or not category or not unit or reorder_level_raw == "":
        flash("All fields are required.", "error")
        return redirect(url_for("list_products"))

    try:
        reorder_level = float(reorder_level_raw)
    except ValueError:
        flash("Reorder Level must be a valid number.", "error")
        return redirect(url_for("list_products"))

    if reorder_level < 0:
        flash("Reorder Level cannot be negative.", "error")
        return redirect(url_for("list_products"))

    success, message = update_product(product_id, name, sku, category, unit, reorder_level)
    flash(message, "success" if success else "error")
    return redirect(url_for("list_products"))


@app.route("/products/delete/<int:product_id>", methods=["POST"])
@login_required
def remove_product(product_id):
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


# ---------------------------------------------------------------------------
# Warehouses
# ---------------------------------------------------------------------------

@app.route("/warehouses", methods=["GET"])
@login_required
def list_warehouses():
    warehouses = get_all_warehouses()
    return render_template("warehouses.html", warehouses=warehouses)


@app.route("/warehouses/add", methods=["POST"])
@login_required
def create_warehouse():
    name = request.form.get("name", "").strip()
    code = request.form.get("code", "").strip().upper()
    location = request.form.get("location", "").strip()

    if not name or not code:
        flash("Name and code are required.", "error")
        return redirect(url_for("list_warehouses"))

    success, message = add_warehouse(name, code, location)
    flash(message, "success" if success else "error")
    return redirect(url_for("list_warehouses"))


@app.route("/warehouses/edit/<int:warehouse_id>", methods=["POST"])
@login_required
def edit_warehouse(warehouse_id):
    if not get_warehouse_by_id(warehouse_id):
        flash("Warehouse not found.", "error")
        return redirect(url_for("list_warehouses"))

    name = request.form.get("name", "").strip()
    code = request.form.get("code", "").strip().upper()
    location = request.form.get("location", "").strip()

    if not name or not code:
        flash("Name and code are required.", "error")
        return redirect(url_for("list_warehouses"))

    success, message = update_warehouse(warehouse_id, name, code, location)
    flash(message, "success" if success else "error")
    return redirect(url_for("list_warehouses"))


@app.route("/warehouses/toggle/<int:warehouse_id>", methods=["POST"])
@login_required
def toggle_warehouse(warehouse_id):
    success, message = toggle_warehouse_status(warehouse_id)
    flash(message, "success" if success else "error")
    return redirect(url_for("list_warehouses"))


# ---------------------------------------------------------------------------
# Stock
# ---------------------------------------------------------------------------

@app.route("/stock")
@login_required
def stock_view():
    search_query = request.args.get("q", "").strip()
    warehouse_id = request.args.get("warehouse_id", "").strip()
    category = request.args.get("category", "").strip()

    rows = get_stock_overview(search_query, warehouse_id, category)
    warehouses = get_all_warehouses(include_inactive=False)
    categories = get_all_categories()

    return render_template(
        "stock.html", rows=rows, warehouses=warehouses, categories=categories,
        search_query=search_query, selected_warehouse=warehouse_id, selected_category=category,
    )


# ---------------------------------------------------------------------------
# Receipts
# ---------------------------------------------------------------------------

@app.route("/receipts", methods=["GET"])
@login_required
def receipts_view():
    status = request.args.get("status", "").strip()
    receipts = get_all_receipts(status)
    products = get_all_products()
    warehouses = get_all_warehouses(include_inactive=False)
    return render_template(
        "receipts.html", receipts=receipts, products=products, warehouses=warehouses,
        selected_status=status, today=today(),
    )


@app.route("/receipts/add", methods=["POST"])
@login_required
def add_receipt():
    reference = request.form.get("reference", "").strip()
    product_id = request.form.get("product_id", "").strip()
    warehouse_id = request.form.get("warehouse_id", "").strip()
    quantity_raw = request.form.get("quantity", "").strip()
    movement_date = request.form.get("date", "").strip() or today()

    if not reference or not product_id or not warehouse_id or not quantity_raw:
        flash("All fields are required to create a receipt.", "error")
        return redirect(url_for("receipts_view"))

    try:
        quantity = float(quantity_raw)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        flash("Quantity must be a positive number.", "error")
        return redirect(url_for("receipts_view"))

    success, message = create_receipt(reference, int(product_id), int(warehouse_id), quantity, movement_date)
    flash(message, "success" if success else "error")
    return redirect(url_for("receipts_view"))


@app.route("/receipts/confirm/<int:receipt_id>", methods=["POST"])
@login_required
def confirm_receipt_route(receipt_id):
    success, message = confirm_receipt(receipt_id)
    flash(message, "success" if success else "error")
    return redirect(url_for("receipts_view"))


# ---------------------------------------------------------------------------
# Deliveries
# ---------------------------------------------------------------------------

@app.route("/deliveries", methods=["GET"])
@login_required
def deliveries_view():
    status = request.args.get("status", "").strip()
    deliveries = get_all_deliveries(status)
    products = get_all_products()
    warehouses = get_all_warehouses(include_inactive=False)
    return render_template(
        "deliveries.html", deliveries=deliveries, products=products, warehouses=warehouses,
        selected_status=status, today=today(),
    )


@app.route("/deliveries/add", methods=["POST"])
@login_required
def add_delivery():
    reference = request.form.get("reference", "").strip()
    product_id = request.form.get("product_id", "").strip()
    warehouse_id = request.form.get("warehouse_id", "").strip()
    customer = request.form.get("customer", "").strip()
    quantity_raw = request.form.get("quantity", "").strip()
    movement_date = request.form.get("date", "").strip() or today()

    if not reference or not product_id or not warehouse_id or not quantity_raw:
        flash("All fields are required to create a delivery order.", "error")
        return redirect(url_for("deliveries_view"))

    try:
        quantity = float(quantity_raw)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        flash("Quantity must be a positive number.", "error")
        return redirect(url_for("deliveries_view"))

    success, message = create_delivery(reference, int(product_id), int(warehouse_id), customer, quantity, movement_date)
    flash(message, "success" if success else "error")
    return redirect(url_for("deliveries_view"))


@app.route("/deliveries/confirm/<int:delivery_id>", methods=["POST"])
@login_required
def confirm_delivery_route(delivery_id):
    success, message = confirm_delivery(delivery_id)
    flash(message, "success" if success else "error")
    return redirect(url_for("deliveries_view"))


# ---------------------------------------------------------------------------
# Transfers
# ---------------------------------------------------------------------------

@app.route("/transfers", methods=["GET"])
@login_required
def transfers_view():
    status = request.args.get("status", "").strip()
    transfers = get_all_transfers(status)
    products = get_all_products()
    warehouses = get_all_warehouses(include_inactive=False)
    return render_template(
        "transfers.html", transfers=transfers, products=products, warehouses=warehouses,
        selected_status=status, today=today(),
    )


@app.route("/transfers/add", methods=["POST"])
@login_required
def add_transfer():
    product_id = request.form.get("product_id", "").strip()
    from_warehouse_id = request.form.get("from_warehouse_id", "").strip()
    to_warehouse_id = request.form.get("to_warehouse_id", "").strip()
    quantity_raw = request.form.get("quantity", "").strip()
    movement_date = request.form.get("date", "").strip() or today()

    if not product_id or not from_warehouse_id or not to_warehouse_id or not quantity_raw:
        flash("All fields are required to create a transfer.", "error")
        return redirect(url_for("transfers_view"))

    try:
        quantity = float(quantity_raw)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        flash("Quantity must be a positive number.", "error")
        return redirect(url_for("transfers_view"))

    success, message = create_transfer(int(product_id), int(from_warehouse_id), int(to_warehouse_id), quantity, movement_date)
    flash(message, "success" if success else "error")
    return redirect(url_for("transfers_view"))


@app.route("/transfers/confirm/<int:transfer_id>", methods=["POST"])
@login_required
def confirm_transfer_route(transfer_id):
    success, message = confirm_transfer(transfer_id)
    flash(message, "success" if success else "error")
    return redirect(url_for("transfers_view"))


# ---------------------------------------------------------------------------
# Adjustments
# ---------------------------------------------------------------------------

@app.route("/adjustments", methods=["GET"])
@login_required
def adjustments_view():
    status = request.args.get("status", "").strip()
    adjustments = get_all_adjustments(status)
    products = get_all_products()
    warehouses = get_all_warehouses(include_inactive=False)
    return render_template(
        "adjustments.html", adjustments=adjustments, products=products, warehouses=warehouses,
        selected_status=status, today=today(),
    )


@app.route("/adjustments/add", methods=["POST"])
@login_required
def add_adjustment():
    product_id = request.form.get("product_id", "").strip()
    warehouse_id = request.form.get("warehouse_id", "").strip()
    new_quantity_raw = request.form.get("new_quantity", "").strip()
    reason = request.form.get("reason", "").strip()
    movement_date = request.form.get("date", "").strip() or today()

    if not product_id or not warehouse_id or new_quantity_raw == "":
        flash("All fields are required to create an adjustment.", "error")
        return redirect(url_for("adjustments_view"))

    try:
        new_quantity = float(new_quantity_raw)
        if new_quantity < 0:
            raise ValueError
    except ValueError:
        flash("Physical quantity must be zero or a positive number.", "error")
        return redirect(url_for("adjustments_view"))

    success, message = create_adjustment(int(product_id), int(warehouse_id), new_quantity, reason, movement_date)
    flash(message, "success" if success else "error")
    return redirect(url_for("adjustments_view"))


@app.route("/adjustments/confirm/<int:adjustment_id>", methods=["POST"])
@login_required
def confirm_adjustment_route(adjustment_id):
    success, message = confirm_adjustment(adjustment_id)
    flash(message, "success" if success else "error")
    return redirect(url_for("adjustments_view"))


# ---------------------------------------------------------------------------
# Stock ledger
# ---------------------------------------------------------------------------

@app.route("/ledger")
@login_required
def ledger_view():
    search_query = request.args.get("q", "").strip()
    warehouse_id = request.args.get("warehouse_id", "").strip()
    movement_type = request.args.get("movement_type", "").strip()

    entries = get_ledger(search_query, warehouse_id, movement_type)
    warehouses = get_all_warehouses(include_inactive=False)

    return render_template(
        "ledger.html", entries=entries, warehouses=warehouses,
        search_query=search_query, selected_warehouse=warehouse_id, selected_type=movement_type,
    )


# ---------------------------------------------------------------------------
# Demo data helpers
# ---------------------------------------------------------------------------

@app.route("/seed", methods=["GET"])
@login_required
def seed_data():
    count = seed_demo_data()
    flash(f"Demo data ready ({count} new records added).", "success")
    return redirect(url_for("dashboard"))


@app.route("/clear-demo", methods=["GET"])
@login_required
def clear_demo():
    deleted = clear_demo_data()
    flash(f"Cleared {deleted} rows. Add demo data again to repopulate.", "success")
    return redirect(url_for("dashboard"))


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True, port=5000)
