"""
migrate_returns.py
Run once to create sales_returns, sales_return_items,
purchase_returns, purchase_return_items tables.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from connection import connection

TABLES = [
    ("sales_returns", """
    CREATE TABLE sales_returns (
        id INT IDENTITY PRIMARY KEY,
        sales_id INT REFERENCES sales(id),
        sale_date DATETIME DEFAULT GETDATE(),
        return_date DATETIME DEFAULT GETDATE(),
        invoice_number NVARCHAR(50),
        customer_id INT REFERENCES customers(id),
        subtotal DECIMAL(18,2) DEFAULT 0,
        discount_amount DECIMAL(18,2) DEFAULT 0,
        total_amount DECIMAL(18,2) DEFAULT 0,
        total_vat DECIMAL(18,2) DEFAULT 0,
        reason NVARCHAR(500),
        status NVARCHAR(20) DEFAULT 'Return',
        payment_status NVARCHAR(20) DEFAULT 'completed',
        payment_method NVARCHAR(50) DEFAULT 'Cash',
        currency_id INT DEFAULT 1,
        user_id INT,
        created_at DATETIME DEFAULT GETDATE()
    )"""),
    ("sales_return_items", """
    CREATE TABLE sales_return_items (
        id INT IDENTITY PRIMARY KEY,
        sales_return_id INT REFERENCES sales_returns(id),
        product_id INT REFERENCES products(id),
        barcode NVARCHAR(100),
        quantity INT DEFAULT 0,
        unit_price DECIMAL(18,2) DEFAULT 0,
        total_price DECIMAL(18,2) DEFAULT 0,
        vat_percentage DECIMAL(5,2) DEFAULT 0,
        vat_amount DECIMAL(18,2) DEFAULT 0,
        discount_amount DECIMAL(18,2) DEFAULT 0,
        profit DECIMAL(18,2) DEFAULT 0
    )"""),
    ("purchase_returns", """
    CREATE TABLE purchase_returns (
        id INT IDENTITY PRIMARY KEY,
        purchase_id INT REFERENCES purchases(id),
        purchase_date DATETIME DEFAULT GETDATE(),
        return_date DATETIME DEFAULT GETDATE(),
        invoice_number NVARCHAR(50),
        supplier_id INT REFERENCES suppliers(id),
        subtotal DECIMAL(18,2) DEFAULT 0,
        discount_amount DECIMAL(18,2) DEFAULT 0,
        total_amount DECIMAL(18,2) DEFAULT 0,
        total_vat DECIMAL(18,2) DEFAULT 0,
        reason NVARCHAR(500),
        status NVARCHAR(20) DEFAULT 'Return',
        payment_status NVARCHAR(20) DEFAULT 'completed',
        payment_method NVARCHAR(50) DEFAULT 'Cash',
        currency_id INT DEFAULT 1,
        user_id INT,
        created_at DATETIME DEFAULT GETDATE()
    )"""),
    ("purchase_return_items", """
    CREATE TABLE purchase_return_items (
        id INT IDENTITY PRIMARY KEY,
        purchase_return_id INT REFERENCES purchase_returns(id),
        product_id INT REFERENCES products(id),
        barcode NVARCHAR(100),
        quantity INT DEFAULT 0,
        unit_cost DECIMAL(18,2) DEFAULT 0,
        total_cost DECIMAL(18,2) DEFAULT 0,
        vat_percentage DECIMAL(5,2) DEFAULT 0,
        vat_amount DECIMAL(18,2) DEFAULT 0,
        discount_amount DECIMAL(18,2) DEFAULT 0,
        unit_price DECIMAL(18,2) DEFAULT 0,
        profit DECIMAL(18,2) DEFAULT 0
    )"""),
]

# --- CREATE TABLES IF THEY DO NOT EXIST ---
for name, ddl in TABLES:
    print(f"  Ensuring table {name} exists...")
    exists = connection.getid(f"SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '{name}'", [])
    if not exists:
         print(f"  CREATE {name}")
         connection.insertingtodatabase(ddl, ())
    else:
         print(f"  Table {name} already exists.")

# --- UPDATING sales_payment TABLE ---
print("  ALTER  sales_payment (add sales_return_id)")
try:
    # 1. Add sales_return_id if it doesn't exist
    cols = []
    connection.contogetrows("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'sales_payment'", cols)
    col_names = [c[0] for c in cols]
    
    if 'sales_return_id' not in col_names:
        connection.insertingtodatabase("ALTER TABLE sales_payment ADD sales_return_id INT NULL", ())
        connection.insertingtodatabase("ALTER TABLE sales_payment ADD CONSTRAINT FK_sales_payment_sales_returns FOREIGN KEY (sales_return_id) REFERENCES sales_returns(id)", ())
        print("  [+] Added sales_return_id")

    # 2. Make sales_id nullable (requires dropping FK first)
    # Check if sales_id is already nullable
    is_nullable = False
    connection.contogetrows("SELECT IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'sales_payment' AND COLUMN_NAME = 'sales_id'", [])
    # Wait, need to fetch result correctly
    res = []
    connection.contogetrows("SELECT IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'sales_payment' AND COLUMN_NAME = 'sales_id'", res)
    if res and res[0][0] == 'NO':
        print("  [*] Making sales_id NULLABLE...")
        # Drop known FK
        try:
            connection.insertingtodatabase("ALTER TABLE sales_payment DROP CONSTRAINT FK__sales_pay__sales__15FA39EE", ())
        except:
            pass # Already dropped or different name
            
        connection.insertingtodatabase("ALTER TABLE sales_payment ALTER COLUMN sales_id INT NULL", ())
        connection.insertingtodatabase("ALTER TABLE sales_payment ADD CONSTRAINT FK_sales_payment_sales FOREIGN KEY (sales_id) REFERENCES sales(id)", ())
        print("  [+] sales_id is now NULLABLE")
        
except Exception as e:
    print(f"  [!] Error altering sales_payment: {e}")

# --- UPDATING purchase_payment TABLE ---
print("  ALTER  purchase_payment (add purchase_return_id)")
try:
    cols = []
    connection.contogetrows("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'purchase_payment'", cols)
    col_names = [c[0] for c in cols]
    
    if 'purchase_return_id' not in col_names:
        connection.insertingtodatabase("ALTER TABLE purchase_payment ADD purchase_return_id INT NULL", ())
        connection.insertingtodatabase("ALTER TABLE purchase_payment ADD CONSTRAINT FK_purchase_payment_purchase_returns FOREIGN KEY (purchase_return_id) REFERENCES purchase_returns(id)", ())
        print("  [+] Added purchase_return_id")

    res = []
    connection.contogetrows("SELECT IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'purchase_payment' AND COLUMN_NAME = 'purchase_id'", res)
    if res and res[0][0] == 'NO':
        print("  [*] Making purchase_id NULLABLE...")
        try:
             # Dropping any existing FK on purchase_id
             fks = []
             connection.contogetrows("SELECT name FROM sys.foreign_keys WHERE parent_object_id = OBJECT_ID('purchase_payment')", fks)
             for fk in fks:
                 if 'purchase' in fk[0].lower():
                     connection.insertingtodatabase(f"ALTER TABLE purchase_payment DROP CONSTRAINT {fk[0]}", ())
        except:
            pass
            
        connection.insertingtodatabase("ALTER TABLE purchase_payment ALTER COLUMN purchase_id INT NULL", ())
        connection.insertingtodatabase("ALTER TABLE purchase_payment ADD CONSTRAINT FK_purchase_payment_purchase FOREIGN KEY (purchase_id) REFERENCES purchases(id)", ())
        print("  [+] purchase_id is now NULLABLE")
except Exception as e:
    print(f"  [!] Error altering purchase_payment: {e}")

print("Migration complete.")
