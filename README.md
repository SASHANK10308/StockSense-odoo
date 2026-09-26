# StockSense - Inventory Management System

A hackathon-ready inventory management prototype built with Flask, SQLite and
vanilla HTML/CSS/JS. Tracks products, multi-warehouse stock, receipts,
deliveries, internal transfers and stock adjustments, with a full audit trail
in a stock ledger.

## Features

- **Authentication** - session-based login/signup/logout with a seeded demo account
- **Dashboard** - KPI cards (products, stock, low/out of stock, pending documents),
  stock-by-category and stock-by-warehouse breakdowns, low stock alerts, and a
  recent stock movements feed
- **Products** - add/edit/delete, duplicate-SKU prevention, search and category filter
- **Warehouses** - add/edit, activate/deactivate
- **Stock** - per-warehouse quantity view with search, warehouse and category filters
- **Receipts** - create as pending, confirm to increase stock
- **Delivery Orders** - create as pending, confirm to decrease stock (never below zero)
- **Internal Transfers** - move stock between warehouses on confirmation
- **Stock Adjustments** - set a physical count; the difference is posted to the ledger
- **Stock Ledger** - a full, filterable log of every movement with running balances
- **Demo data** - one click (or `/seed`) populates warehouses, products and a
  realistic set of confirmed/pending documents so the dashboard looks alive immediately

## Technology stack

- **Backend**: Python 3 + Flask
- **Database**: SQLite3 (parameterized SQL, foreign keys enforced)
- **Frontend**: HTML5, vanilla CSS (custom design system, no framework), vanilla JS
- **Templating**: Jinja2

## Directory structure

```text
stocksense/
├── app.py                  # Flask routes / controllers
├── requirements.txt
├── database/
│   ├── schema.sql           # Table definitions
│   ├── db.py                # Connection + all CRUD / business logic (stock, ledger)
│   └── seed.py               # Demo data generator
├── templates/                # Jinja2 templates (one per page) + base.html shell
└── static/
    ├── css/style.css        # Design tokens + all component styles
    └── js/app.js            # Modal handling, flash auto-dismiss
```

## Setup

```bash
# from the project root
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000** in your browser. The SQLite file
(`database/stocksense.db`) is created automatically on first run.

## Demo login

```
Email:    admin@stocksense.com
Password: admin123
```

## Loading demo data

Click **"Load demo data"** in the sidebar, or visit `/seed` directly. This
creates 3 warehouses, 5 products, opening stock balances, and a mix of
confirmed and pending receipts/deliveries/transfers/adjustments so every
page (and the dashboard) has real numbers right away. Visit `/clear-demo`
to wipe everything and start over.

## Suggested demo workflow

1. Log in with the demo account.
2. Load demo data from the sidebar.
3. View the **Dashboard** - note the KPIs and the low stock alert list.
4. Open **Products**, add a new product with an opening warehouse quantity.
5. Go to **Receipts**, create a receipt for that product and **confirm** it -
   watch stock increase.
6. Go to **Deliveries**, create and confirm a delivery for the same product -
   stock decreases (and can't go negative - try over-delivering to see it blocked).
7. Go to **Transfers**, move stock from one warehouse to another and confirm.
8. Go to **Adjustments**, set a physical count and confirm - the delta posts
   automatically.
9. Open **Stock Ledger** to see every one of those movements with running
   balances, and return to the **Dashboard** to see the KPIs and recent
   movements feed reflect all of it.

## Database

SQLite tables (see `database/schema.sql`): `users`, `warehouses`, `products`,
`stock`, `receipts`, `receipt_items`, `deliveries`, `delivery_items`,
`transfers`, `adjustments`, `stock_ledger`. All writes go through
`database/db.py` using parameterized queries; stock changes and ledger
entries are always written together via `record_movement()` so the ledger
can never drift from the live `stock` table. Deleting a product cascades to
its stock rows and document history.

## Known limitations (hackathon scope)

- Single-item receipts/deliveries (one product per document) rather than
  multi-line documents - kept intentionally simple for the demo.
- No role-based permissions - any logged-in user has full access.
- The Flask dev server is used as-is; use a production WSGI server for
  anything beyond a demo.
