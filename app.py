import os
from flask import Flask, render_template, request, redirect, url_for, flash
from database.db import (
    init_db,
    get_all_products,
    get_product_by_id,
    add_product,
    update_product,
    delete_product
)
from database.seed import seed_demo_data, clear_demo_data

app = Flask(__name__)
# Secret key required for Flask flash messages
app.secret_key = "stocksense_secret_key_for_hackathon"

# Initialize database tables on app startup
with app.app_context():
    init_db()


@app.route("/")
def index():
    """Redirect root path to the Products page."""
    return redirect(url_for("list_products"))


@app.route("/products", methods=["GET"])
def list_products():
    """
    Renders the Products page.
    Supports search query parameter ?q=... to search by name or SKU.
    Calculates summary metrics for the dashboard header.
    """
    search_query = request.args.get("q", "").strip()
    products = get_all_products(search_query)

    # Compute statistics for summary badges
    total_products = len(products)
    low_stock_count = sum(
        1 for p in products if p["initial_stock"] <= p["reorder_level"]
    )

    return render_template(
        "products.html",
        products=products,
        search_query=search_query,
        total_products=total_products,
        low_stock_count=low_stock_count
    )


@app.route("/products/add", methods=["POST"])
def create_product():
    """
    Handles Add Product form submission with server-side validation.
    """
    name = request.form.get("name", "").strip()
    sku = request.form.get("sku", "").strip()
    category = request.form.get("category", "").strip()
    unit = request.form.get("unit", "").strip()
    initial_stock_raw = request.form.get("initial_stock", "").strip()
    reorder_level_raw = request.form.get("reorder_level", "").strip()

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

    # 3. Add product via database module (handles duplicate SKU check)
    success, message = add_product(name, sku, category, unit, initial_stock, reorder_level)

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
    # Verify product exists
    existing = get_product_by_id(product_id)
    if not existing:
        flash("Product not found.", "error")
        return redirect(url_for("list_products"))

    name = request.form.get("name", "").strip()
    sku = request.form.get("sku", "").strip()
    category = request.form.get("category", "").strip()
    unit = request.form.get("unit", "").strip()
    initial_stock_raw = request.form.get("initial_stock", "").strip()
    reorder_level_raw = request.form.get("reorder_level", "").strip()

    # 1. Required field validation
    if not name or not sku or not category or not unit or initial_stock_raw == "" or reorder_level_raw == "":
        flash("All fields are required. Please complete the edit form.", "error")
        return redirect(url_for("list_products"))

    # 2. Non-negative validation
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

    # 3. Update database
    success, message = update_product(product_id, name, sku, category, unit, initial_stock, reorder_level)

    if success:
        flash(message, "success")
    else:
        flash(message, "error")

    return redirect(url_for("list_products"))


@app.route("/products/delete/<int:product_id>", methods=["POST"])
def remove_product(product_id):
    """
    Deletes a product by ID.
    """
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


@app.route("/seed", methods=["GET"])
def seed_data():
    """Development helper route to populate demo data easily."""
    count = seed_demo_data()
    flash(f"Added {count} sample demo products!", "success")
    return redirect(url_for("list_products"))


@app.route("/clear-demo", methods=["GET"])
def clear_demo():
    """Development helper route to clear demo data easily."""
    deleted = clear_demo_data()
    flash(f"Cleared {deleted} sample demo products!", "success")
    return redirect(url_for("list_products"))


if __name__ == "__main__":
    # Run dev server on port 5000
    app.run(debug=True, port=5000)
