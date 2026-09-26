import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), 'stocksense.db')

@contextmanager
def get_db_connection():
    """Context manager for database connections with foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_db():
    """Initialize database schema."""
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r') as f:
        schema = f.read()
    
    with get_db_connection() as conn:
        conn.executescript(schema)


# ============ USERS ============
def create_user(email, password_hash):
    """Create a new user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO users (email, password_hash) VALUES (?, ?)',
                (email, password_hash)
            )
            return True, "User created successfully"
        except sqlite3.IntegrityError:
            return False, "Email already exists"


def get_user_by_email(email):
    """Get user by email."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_user_by_id(user_id):
    """Get user by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


# ============ PRODUCTS ============
def get_all_products(search_query=""):
    """Get all products with optional search."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if search_query:
            query = '''SELECT * FROM products 
                       WHERE name ILIKE ? OR sku ILIKE ? 
                       ORDER BY name ASC'''
            cursor.execute(query, (f'%{search_query}%', f'%{search_query}%'))
        else:
            cursor.execute('SELECT * FROM products ORDER BY name ASC')
        
        rows = cursor.fetchall()
        # For each product, get the initial stock (sum across all warehouses)
        products = []
        for row in rows:
            product_dict = dict(row)
            # Get total stock across all warehouses
            cursor.execute(
                'SELECT COALESCE(SUM(quantity), 0) as total FROM stocks WHERE product_id = ?',
                (product_dict['id'],)
            )
            stock_row = cursor.fetchone()
            product_dict['initial_stock'] = stock_row['total']
            products.append(product_dict)
        
        return products


def get_product_by_id(product_id):
    """Get a single product by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        row = cursor.fetchone()
        if row:
            product_dict = dict(row)
            # Get total stock
            cursor.execute(
                'SELECT COALESCE(SUM(quantity), 0) as total FROM stocks WHERE product_id = ?',
                (product_id,)
            )
            stock_row = cursor.fetchone()
            product_dict['initial_stock'] = stock_row['total']
            return product_dict
        return None


def add_product(name, sku, category, unit, initial_stock, reorder_level):
    """Add a new product."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''INSERT INTO products (name, sku, category, unit, reorder_level) 
                   VALUES (?, ?, ?, ?, ?)''',
                (name, sku, category, unit, reorder_level)
            )
            product_id = cursor.lastrowid
            
            # Add stock record for first warehouse (Main Warehouse)
            cursor.execute('SELECT id FROM warehouses LIMIT 1')
            warehouse = cursor.fetchone()
            if warehouse:
                cursor.execute(
                    'INSERT INTO stocks (product_id, warehouse_id, quantity) VALUES (?, ?, ?)',
                    (product_id, warehouse['id'], initial_stock)
                )
            
            return True, f"Product '{name}' added successfully"
        except sqlite3.IntegrityError:
            return False, "A product with this SKU already exists"


def update_product(product_id, name, sku, category, unit, initial_stock, reorder_level):
    """Update a product."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''UPDATE products 
                   SET name = ?, sku = ?, category = ?, unit = ?, reorder_level = ? 
                   WHERE id = ?''',
                (name, sku, category, unit, reorder_level, product_id)
            )
            return True, f"Product '{name}' updated successfully"
        except sqlite3.IntegrityError:
            return False, "A product with this SKU already exists"


def delete_product(product_id):
    """Delete a product."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
        return True, "Product deleted successfully"


# ============ WAREHOUSES ============
def get_all_warehouses():
    """Get all warehouses."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM warehouses ORDER BY name ASC')
        return [dict(row) for row in cursor.fetchall()]


def get_warehouse_by_id(warehouse_id):
    """Get warehouse by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM warehouses WHERE id = ?', (warehouse_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def add_warehouse(name, code, address):
    """Add a new warehouse."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO warehouses (name, code, address, status) VALUES (?, ?, ?, ?)',
                (name, code, address, 'Active')
            )
            return True, f"Warehouse '{name}' created successfully"
        except sqlite3.IntegrityError:
            return False, "A warehouse with this code already exists"


def update_warehouse(warehouse_id, name, code, address, status):
    """Update a warehouse."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                'UPDATE warehouses SET name = ?, code = ?, address = ?, status = ? WHERE id = ?',
                (name, code, address, status, warehouse_id)
            )
            return True, "Warehouse updated successfully"
        except sqlite3.IntegrityError:
            return False, "A warehouse with this code already exists"


# ============ STOCK ============
def get_stock_by_warehouse(warehouse_id):
    """Get all stock in a warehouse."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.id, s.product_id, s.quantity, p.name, p.sku, p.unit, p.reorder_level
            FROM stocks s
            JOIN products p ON s.product_id = p.id
            WHERE s.warehouse_id = ?
            ORDER BY p.name ASC
        ''', (warehouse_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_all_stock():
    """Get all stock across all warehouses."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.id, s.product_id, s.warehouse_id, s.quantity, p.name, p.sku, p.unit, p.reorder_level, w.name as warehouse_name
            FROM stocks s
            JOIN products p ON s.product_id = p.id
            JOIN warehouses w ON s.warehouse_id = w.id
            ORDER BY p.name ASC, w.name ASC
        ''')
        return [dict(row) for row in cursor.fetchall()]


def get_stock_by_product_warehouse(product_id, warehouse_id):
    """Get stock for a specific product in a warehouse."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM stocks WHERE product_id = ? AND warehouse_id = ?',
            (product_id, warehouse_id)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def update_stock_quantity(product_id, warehouse_id, quantity):
    """Update stock quantity."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE stocks SET quantity = ?, updated_at = CURRENT_TIMESTAMP WHERE product_id = ? AND warehouse_id = ?',
            (quantity, product_id, warehouse_id)
        )


def add_stock(product_id, warehouse_id, quantity=0):
    """Add stock record for a product in a warehouse."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO stocks (product_id, warehouse_id, quantity) VALUES (?, ?, ?)',
                (product_id, warehouse_id, quantity)
            )
            return True
        except sqlite3.IntegrityError:
            return False


# ============ RECEIPTS ============
def get_all_receipts():
    """Get all receipts."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM receipts ORDER BY date DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]


def get_receipt_by_id(receipt_id):
    """Get receipt by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM receipts WHERE id = ?', (receipt_id,))
        row = cursor.fetchone()
        if row:
            receipt_dict = dict(row)
            # Get items
            cursor.execute('''
                SELECT ri.*, p.name, p.sku, p.unit, w.name as warehouse_name
                FROM receipt_items ri
                JOIN products p ON ri.product_id = p.id
                JOIN warehouses w ON ri.warehouse_id = w.id
                WHERE ri.receipt_id = ?
            ''', (receipt_id,))
            receipt_dict['items'] = [dict(row) for row in cursor.fetchall()]
            return receipt_dict
        return None


def add_receipt(reference, date, status='Pending'):
    """Add a receipt."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO receipts (reference, date, status) VALUES (?, ?, ?)',
            (reference, date, status)
        )
        return cursor.lastrowid


def add_receipt_item(receipt_id, product_id, warehouse_id, quantity):
    """Add item to receipt."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO receipt_items (receipt_id, product_id, warehouse_id, quantity) VALUES (?, ?, ?, ?)',
            (receipt_id, product_id, warehouse_id, quantity)
        )


def confirm_receipt(receipt_id):
    """Confirm receipt and update stock."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get receipt items
        cursor.execute('SELECT * FROM receipt_items WHERE receipt_id = ?', (receipt_id,))
        items = cursor.fetchall()
        
        for item in items:
            item_dict = dict(item)
            # Update stock
            stock = get_stock_by_product_warehouse(item_dict['product_id'], item_dict['warehouse_id'])
            if stock:
                new_qty = stock['quantity'] + item_dict['quantity']
                update_stock_quantity(item_dict['product_id'], item_dict['warehouse_id'], new_qty)
            else:
                add_stock(item_dict['product_id'], item_dict['warehouse_id'], item_dict['quantity'])
            
            # Add ledger entry
            add_ledger_entry(
                reference=f"RCP-{receipt_id}",
                product_id=item_dict['product_id'],
                warehouse_id=item_dict['warehouse_id'],
                movement_type='Receipt',
                quantity_in=item_dict['quantity']
            )
        
        # Update receipt status
        cursor.execute('UPDATE receipts SET status = ? WHERE id = ?', ('Confirmed', receipt_id))


def delete_receipt(receipt_id):
    """Delete receipt."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM receipt_items WHERE receipt_id = ?', (receipt_id,))
        cursor.execute('DELETE FROM receipts WHERE id = ?', (receipt_id,))


# ============ DELIVERIES ============
def get_all_deliveries():
    """Get all deliveries."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM deliveries ORDER BY date DESC')
        return [dict(row) for row in cursor.fetchall()]


def get_delivery_by_id(delivery_id):
    """Get delivery by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM deliveries WHERE id = ?', (delivery_id,))
        row = cursor.fetchone()
        if row:
            delivery_dict = dict(row)
            # Get items
            cursor.execute('''
                SELECT di.*, p.name, p.sku, p.unit, w.name as warehouse_name
                FROM delivery_items di
                JOIN products p ON di.product_id = p.id
                JOIN warehouses w ON di.warehouse_id = w.id
                WHERE di.delivery_id = ?
            ''', (delivery_id,))
            delivery_dict['items'] = [dict(row) for row in cursor.fetchall()]
            return delivery_dict
        return None


def add_delivery(reference, customer, date, status='Pending'):
    """Add a delivery."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO deliveries (reference, customer, date, status) VALUES (?, ?, ?, ?)',
            (reference, customer, date, status)
        )
        return cursor.lastrowid


def add_delivery_item(delivery_id, product_id, warehouse_id, quantity):
    """Add item to delivery."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO delivery_items (delivery_id, product_id, warehouse_id, quantity) VALUES (?, ?, ?, ?)',
            (delivery_id, product_id, warehouse_id, quantity)
        )


def confirm_delivery(delivery_id):
    """Confirm delivery and update stock."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get delivery items
        cursor.execute('SELECT * FROM delivery_items WHERE delivery_id = ?', (delivery_id,))
        items = cursor.fetchall()
        
        for item in items:
            item_dict = dict(item)
            # Update stock
            stock = get_stock_by_product_warehouse(item_dict['product_id'], item_dict['warehouse_id'])
            if stock:
                new_qty = stock['quantity'] - item_dict['quantity']
                if new_qty < 0:
                    continue  # Skip if insufficient stock
                update_stock_quantity(item_dict['product_id'], item_dict['warehouse_id'], new_qty)
            
            # Add ledger entry
            add_ledger_entry(
                reference=f"DEL-{delivery_id}",
                product_id=item_dict['product_id'],
                warehouse_id=item_dict['warehouse_id'],
                movement_type='Delivery',
                quantity_out=item_dict['quantity']
            )
        
        # Update delivery status
        cursor.execute('UPDATE deliveries SET status = ? WHERE id = ?', ('Confirmed', delivery_id))


def delete_delivery(delivery_id):
    """Delete delivery."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM delivery_items WHERE delivery_id = ?', (delivery_id,))
        cursor.execute('DELETE FROM deliveries WHERE id = ?', (delivery_id,))


# ============ TRANSFERS ============
def get_all_transfers():
    """Get all transfers."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT t.*, 
                   p.name as product_name, p.sku,
                   w1.name as from_warehouse, w2.name as to_warehouse
            FROM transfers t
            JOIN products p ON t.product_id = p.id
            JOIN warehouses w1 ON t.from_warehouse_id = w1.id
            JOIN warehouses w2 ON t.to_warehouse_id = w2.id
            ORDER BY t.date DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]


def get_transfer_by_id(transfer_id):
    """Get transfer by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT t.*, 
                   p.name as product_name, p.sku,
                   w1.name as from_warehouse, w2.name as to_warehouse
            FROM transfers t
            JOIN products p ON t.product_id = p.id
            JOIN warehouses w1 ON t.from_warehouse_id = w1.id
            JOIN warehouses w2 ON t.to_warehouse_id = w2.id
            WHERE t.id = ?
        ''', (transfer_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def add_transfer(product_id, from_warehouse_id, to_warehouse_id, quantity, date, status='Pending'):
    """Add a transfer."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO transfers (product_id, from_warehouse_id, to_warehouse_id, quantity, date, status)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (product_id, from_warehouse_id, to_warehouse_id, quantity, date, status)
        )
        return cursor.lastrowid


def confirm_transfer(transfer_id):
    """Confirm transfer and update stock."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get transfer
        cursor.execute('SELECT * FROM transfers WHERE id = ?', (transfer_id,))
        transfer = cursor.fetchone()
        if not transfer:
            return
        
        transfer_dict = dict(transfer)
        
        # Deduct from source
        source_stock = get_stock_by_product_warehouse(transfer_dict['product_id'], transfer_dict['from_warehouse_id'])
        if source_stock:
            new_qty = source_stock['quantity'] - transfer_dict['quantity']
            if new_qty >= 0:
                update_stock_quantity(transfer_dict['product_id'], transfer_dict['from_warehouse_id'], new_qty)
        
        # Add to destination
        dest_stock = get_stock_by_product_warehouse(transfer_dict['product_id'], transfer_dict['to_warehouse_id'])
        if dest_stock:
            new_qty = dest_stock['quantity'] + transfer_dict['quantity']
            update_stock_quantity(transfer_dict['product_id'], transfer_dict['to_warehouse_id'], new_qty)
        else:
            add_stock(transfer_dict['product_id'], transfer_dict['to_warehouse_id'], transfer_dict['quantity'])
        
        # Add ledger entries
        add_ledger_entry(
            reference=f"TRF-{transfer_id}",
            product_id=transfer_dict['product_id'],
            warehouse_id=transfer_dict['from_warehouse_id'],
            movement_type='Transfer',
            quantity_out=transfer_dict['quantity']
        )
        add_ledger_entry(
            reference=f"TRF-{transfer_id}",
            product_id=transfer_dict['product_id'],
            warehouse_id=transfer_dict['to_warehouse_id'],
            movement_type='Transfer',
            quantity_in=transfer_dict['quantity']
        )
        
        # Update transfer status
        cursor.execute('UPDATE transfers SET status = ? WHERE id = ?', ('Confirmed', transfer_id))


def delete_transfer(transfer_id):
    """Delete transfer."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM transfers WHERE id = ?', (transfer_id,))


# ============ ADJUSTMENTS ============
def get_all_adjustments():
    """Get all adjustments."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.*, p.name, p.sku, w.name as warehouse_name
            FROM adjustments a
            JOIN products p ON a.product_id = p.id
            JOIN warehouses w ON a.warehouse_id = w.id
            ORDER BY a.date DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]


def get_adjustment_by_id(adjustment_id):
    """Get adjustment by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.*, p.name, p.sku, w.name as warehouse_name
            FROM adjustments a
            JOIN products p ON a.product_id = p.id
            JOIN warehouses w ON a.warehouse_id = w.id
            WHERE a.id = ?
        ''', (adjustment_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def add_adjustment(product_id, warehouse_id, current_quantity, new_quantity, reason, date, status='Pending'):
    """Add an adjustment."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO adjustments (product_id, warehouse_id, current_quantity, new_quantity, reason, date, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (product_id, warehouse_id, current_quantity, new_quantity, reason, date, status)
        )
        return cursor.lastrowid


def confirm_adjustment(adjustment_id):
    """Confirm adjustment and update stock."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get adjustment
        cursor.execute('SELECT * FROM adjustments WHERE id = ?', (adjustment_id,))
        adjustment = cursor.fetchone()
        if not adjustment:
            return
        
        adj_dict = dict(adjustment)
        
        # Update stock to new quantity
        update_stock_quantity(adj_dict['product_id'], adj_dict['warehouse_id'], adj_dict['new_quantity'])
        
        # Determine quantity in or out
        diff = adj_dict['new_quantity'] - adj_dict['current_quantity']
        if diff > 0:
            add_ledger_entry(
                reference=f"ADJ-{adjustment_id}",
                product_id=adj_dict['product_id'],
                warehouse_id=adj_dict['warehouse_id'],
                movement_type='Adjustment',
                quantity_in=diff
            )
        else:
            add_ledger_entry(
                reference=f"ADJ-{adjustment_id}",
                product_id=adj_dict['product_id'],
                warehouse_id=adj_dict['warehouse_id'],
                movement_type='Adjustment',
                quantity_out=abs(diff)
            )
        
        # Update adjustment status
        cursor.execute('UPDATE adjustments SET status = ? WHERE id = ?', ('Confirmed', adjustment_id))


def delete_adjustment(adjustment_id):
    """Delete adjustment."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM adjustments WHERE id = ?', (adjustment_id,))


# ============ STOCK LEDGER ============
def add_ledger_entry(reference, product_id, warehouse_id, movement_type, quantity_in=0, quantity_out=0):
    """Add ledger entry."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get current balance
        cursor.execute(
            'SELECT COALESCE(balance, 0) as balance FROM stock_ledger WHERE product_id = ? AND warehouse_id = ? ORDER BY id DESC LIMIT 1',
            (product_id, warehouse_id)
        )
        row = cursor.fetchone()
        prev_balance = row['balance'] if row else 0
        new_balance = prev_balance + quantity_in - quantity_out
        
        cursor.execute(
            '''INSERT INTO stock_ledger (reference, product_id, warehouse_id, movement_type, quantity_in, quantity_out, balance)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (reference, product_id, warehouse_id, movement_type, quantity_in, quantity_out, new_balance)
        )


def get_all_ledger():
    """Get all ledger entries."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT sl.*, p.name, p.sku, w.name as warehouse_name
            FROM stock_ledger sl
            JOIN products p ON sl.product_id = p.id
            JOIN warehouses w ON sl.warehouse_id = w.id
            ORDER BY sl.id DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]


def get_ledger_by_product(product_id):
    """Get ledger entries for a product."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT sl.*, p.name, p.sku, w.name as warehouse_name
            FROM stock_ledger sl
            JOIN products p ON sl.product_id = p.id
            JOIN warehouses w ON sl.warehouse_id = w.id
            WHERE sl.product_id = ?
            ORDER BY sl.id DESC
        ''', (product_id,))
        return [dict(row) for row in cursor.fetchall()]


# ============ DASHBOARD STATS ============
def get_dashboard_stats():
    """Get dashboard statistics."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Total products
        cursor.execute('SELECT COUNT(*) as count FROM products')
        total_products = cursor.fetchone()['count']
        
        # Total stock
        cursor.execute('SELECT COALESCE(SUM(quantity), 0) as total FROM stocks')
        total_stock = cursor.fetchone()['total']
        
        # Low stock items
        cursor.execute('''
            SELECT COUNT(*) as count FROM stocks s
            JOIN products p ON s.product_id = p.id
            WHERE s.quantity <= p.reorder_level AND s.quantity > 0
        ''')
        low_stock_count = cursor.fetchone()['count']
        
        # Out of stock items
        cursor.execute('''
            SELECT COUNT(*) as count FROM stocks s
            WHERE s.quantity = 0
        ''')
        out_of_stock_count = cursor.fetchone()['count']
        
        # Pending receipts
        cursor.execute("SELECT COUNT(*) as count FROM receipts WHERE status = 'Pending'")
        pending_receipts = cursor.fetchone()['count']
        
        # Pending deliveries
        cursor.execute("SELECT COUNT(*) as count FROM deliveries WHERE status = 'Pending'")
        pending_deliveries = cursor.fetchone()['count']
        
        # Pending transfers
        cursor.execute("SELECT COUNT(*) as count FROM transfers WHERE status = 'Pending'")
        pending_transfers = cursor.fetchone()['count']
        
        # Recent movements
        cursor.execute('''
            SELECT sl.*, p.name, p.sku, w.name as warehouse_name
            FROM stock_ledger sl
            JOIN products p ON sl.product_id = p.id
            JOIN warehouses w ON sl.warehouse_id = w.id
            ORDER BY sl.id DESC LIMIT 10
        ''')
        recent_movements = [dict(row) for row in cursor.fetchall()]
        
        # Low stock items
        cursor.execute('''
            SELECT s.*, p.name, p.sku, p.reorder_level, w.name as warehouse_name
            FROM stocks s
            JOIN products p ON s.product_id = p.id
            JOIN warehouses w ON s.warehouse_id = w.id
            WHERE s.quantity <= p.reorder_level AND s.quantity > 0
            ORDER BY s.quantity ASC
            LIMIT 5
        ''')
        low_stock_items = [dict(row) for row in cursor.fetchall()]
        
        return {
            'total_products': total_products,
            'total_stock': total_stock,
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            'pending_receipts': pending_receipts,
            'pending_deliveries': pending_deliveries,
            'pending_transfers': pending_transfers,
            'recent_movements': recent_movements,
            'low_stock_items': low_stock_items
        }
