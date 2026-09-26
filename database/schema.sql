-- StockSense Modular Inventory System - SQLite Schema
-- Module 1: Products
-- Module 2: Warehouses, Locations & Relational Stock

PRAGMA foreign_keys = ON;

-- 1. Warehouses / Locations Table
CREATE TABLE IF NOT EXISTS warehouses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    code TEXT NOT NULL UNIQUE COLLATE NOCASE,
    address TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active', 'Inactive')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Products Table
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    sku TEXT NOT NULL UNIQUE COLLATE NOCASE,
    category TEXT NOT NULL,
    unit TEXT NOT NULL,
    reorder_level REAL NOT NULL DEFAULT 0.0 CHECK(reorder_level >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Relational Stock Table
-- Each product has at most one stock record per warehouse
CREATE TABLE IF NOT EXISTS stocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    warehouse_id INTEGER NOT NULL,
    quantity REAL NOT NULL DEFAULT 0.0 CHECK(quantity >= 0),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (warehouse_id) REFERENCES warehouses(id) ON DELETE RESTRICT,
    UNIQUE (product_id, warehouse_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_warehouses_code ON warehouses(code);
CREATE INDEX IF NOT EXISTS idx_stocks_product ON stocks(product_id);
CREATE INDEX IF NOT EXISTS idx_stocks_warehouse ON stocks(warehouse_id);

