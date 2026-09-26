# StockSense-odoo
Modular Inventory Management System for real-time stock tracking and streamlined warehouse operations.
# StockSense - Modular Inventory Management System

**StockSense** is an open-source, modular inventory management system designed for small to medium enterprises. Built for the Odoo Hackathon, it prioritizes clean architecture, clear code structure, and intuitive user experiences.

---

## 🚀 Current Module Implemented
- **Module 1**: Project Foundation & Product Management

---

## 🛠️ Technology Stack
- **Backend Framework**: Python 3 + Flask
- **Database**: SQLite3 (relational, zero-config embedded database)
- **Frontend**: HTML5, Vanilla CSS3 (Custom design system), Vanilla JavaScript (No heavy JS frameworks)
- **Templating**: Jinja2

---

## 📁 Directory Structure
```text
stocksense/
│── app.py                  # Flask route controllers & request handlers
│── requirements.txt        # Application dependencies (Flask)
│── README.md               # Project documentation
│── .gitignore              # Git ignore rules
│── database/
│   ├── schema.sql          # SQLite table definitions
│   ├── db.py               # Database connection & CRUD helper functions
│   └── seed.py             # Script to seed sample demo products
│── templates/
│   ├── base.html           # Main layout template (navbar, flash alerts, footer)
│   └── products.html       # Products catalog & management page (table & modals)
└── static/
    ├── css/
    │   └── style.css       # Clean hackathon design stylesheet
    └── js/
        └── products.js     # Modal management & validation scripts
```

---

## ⚙️ Installation & Setup

### 1. Prerequisites
- Python 3.8+ installed on your machine.

### 2. Create Virtual Environment
```bash
# Navigate to the project directory
cd stocksense

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# macOS / Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## ▶️ Running the Application

```bash
python app.py
```
Open your browser and navigate to:
👉 `http://127.0.0.1:5000`

### Optional: Populating Demo Data
To test with pre-configured sample products, you can either:
- Click the **"+ Add Demo Data"** button in the top navigation bar.
- Or run the seed script directly from the terminal:
  ```bash
  python database/seed.py
  ```

---

## 💡 How Product Management Works
1. **Database Abstraction (`database/db.py`)**: All SQLite SQL queries use **parameterized placeholders (`?`)** to isolate database operations safely from presentation logic.
2. **Product Fields**: Each product includes Name, unique SKU/Code, Category, Unit of Measure, Initial Stock, and Reorder Level.
3. **Validations Enforced**:
   - Required field check on all inputs.
   - Non-negative constraint on Initial Stock (`>= 0`) and Reorder Level (`>= 0`).
   - Case-insensitive duplicate SKU prevention.
4. **Low Stock Alerts**: Items where `Initial Stock <= Reorder Level` are automatically tagged with a `⚠️ Low Stock` warning badge.

---

## ⚠️ Current Limitations (Module 1 Scope)
- Initial Stock is currently recorded as the baseline starting balance.
- Stock movements (receipts, deliveries, adjustments) and multi-location warehouse stock are not yet active in Module 1.

---

## 🔮 Planned Future Modules
- **Module 2**: Receipts (Incoming Stock Purchases & Vendor Log)
- **Module 3**: Deliveries (Outgoing Sales Orders & Customer Dispatch)
- **Module 4**: Internal Transfers (Warehouse & Location Stock Movements)
- **Module 5**: Stock Adjustments (Physical Inventory Audits & Discrepancies)
- **Module 6**: Stock Ledger & Inventory Valuation Report
- **Module 7**: Executive Dashboard & Reorder Automated Notifications
