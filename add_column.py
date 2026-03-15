from connection import connection

# Add account_code column to purchases table if it doesn't exist
try:
    connection.update_supplierbalance("IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('purchases') AND name = 'account_code') ALTER TABLE purchases ADD account_code NVARCHAR(10) DEFAULT '6011'", ())
    print("account_code column added or already exists")
except Exception as e:
    print(f"Error: {e}")

# Add currency_id column to products table if it doesn't exist
try:
    connection.update_supplierbalance("IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('products') AND name = 'currency_id') ALTER TABLE products ADD currency_id INT NULL", ())
    print("currency_id column added or already exists")
except Exception as e:
    print(f"Error adding currency_id: {e}")

# Add local_price column to products table if it doesn't exist
try:
    connection.update_supplierbalance("IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('products') AND name = 'local_price') ALTER TABLE products ADD local_price DECIMAL(15,2) NULL", ())
    print("local_price column added or already exists")
except Exception as e:
    print(f"Error adding local_price: {e}")

# Add foreign key constraint for currency_id if it doesn't exist
try:
    connection.update_supplierbalance("""
    IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE object_id = OBJECT_ID('FK_products_currencies') AND parent_object_id = OBJECT_ID('products'))
    ALTER TABLE products ADD CONSTRAINT FK_products_currencies FOREIGN KEY (currency_id) REFERENCES currencies(id)
    """, ())
    print("Foreign key constraint for currency_id added or already exists")
except Exception as e:
    print(f"Error adding foreign key: {e}")

# Add currency_id column to sales table if it doesn't exist
try:
    connection.update_supplierbalance("IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('sales') AND name = 'currency_id') ALTER TABLE sales ADD currency_id INT NULL", ())
    print("currency_id column added to sales table or already exists")
except Exception as e:
    print(f"Error: {e}")

# Add foreign key constraint for currency_id in sales if it doesn't exist
try:
    connection.update_supplierbalance("""
    IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE object_id = OBJECT_ID('FK_sales_currencies') AND parent_object_id = OBJECT_ID('sales'))
    ALTER TABLE sales ADD CONSTRAINT FK_sales_currencies FOREIGN KEY (currency_id) REFERENCES currencies(id)
    """, ())
    print("Foreign key constraint for currency_id in sales added or already exists")
except Exception as e:
    print(f"Error adding foreign key: {e}")

# Add balance_usd column to suppliers table if it doesn't exist
try:
    connection.update_supplierbalance("IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('suppliers') AND name = 'balance_usd') ALTER TABLE suppliers ADD balance_usd DECIMAL(15,2) DEFAULT 0.00", ())
    print("balance_usd column added or already exists")

    # Alter balance column to DECIMAL(15,2) to match other financial columns
    try:
        connection.update_supplierbalance("ALTER TABLE suppliers ALTER COLUMN balance DECIMAL(15,2)", ())
        print("balance column altered to DECIMAL(15,2)")
    except Exception as e:
        print(f"balance column may already be DECIMAL(15,2) or error: {e}")

    # Alter all DECIMAL(10,2) columns to DECIMAL(15,2) to prevent overflow errors
    try:
        connection.update_supplierbalance("ALTER TABLE purchases ALTER COLUMN subtotal DECIMAL(15,2)", ())
        connection.update_supplierbalance("ALTER TABLE purchases ALTER COLUMN discount_amount DECIMAL(15,2)", ())
        connection.update_supplierbalance("ALTER TABLE purchases ALTER COLUMN tax_amount DECIMAL(15,2)", ())
        connection.update_supplierbalance("ALTER TABLE purchases ALTER COLUMN total_amount DECIMAL(15,2)", ())
        connection.update_supplierbalance("ALTER TABLE purchase_items ALTER COLUMN unit_cost DECIMAL(15,2)", ())
        connection.update_supplierbalance("ALTER TABLE purchase_items ALTER COLUMN total_cost DECIMAL(15,2)", ())
        connection.update_supplierbalance("ALTER TABLE purchase_items ALTER COLUMN unit_price DECIMAL(15,2)", ())
        connection.update_supplierbalance("ALTER TABLE purchase_items ALTER COLUMN profit DECIMAL(15,2)", ())
        connection.update_supplierbalance("ALTER TABLE purchase_items ALTER COLUMN discount_amount DECIMAL(15,2)", ())
        connection.update_supplierbalance("ALTER TABLE purchase_payment ALTER COLUMN total_amount DECIMAL(15,2)", ())
        connection.update_supplierbalance("ALTER TABLE purchase_payment ALTER COLUMN amount_paid DECIMAL(15,2)", ())
        connection.update_supplierbalance("ALTER TABLE purchase_payment ALTER COLUMN debit DECIMAL(15,2)", ())
        connection.update_supplierbalance("ALTER TABLE purchase_payment ALTER COLUMN credit DECIMAL(15,2)", ())
        connection.update_supplierbalance("ALTER TABLE supplier_payment ALTER COLUMN amount DECIMAL(15,2)", ())
        print("All DECIMAL(10,2) columns altered to DECIMAL(15,2)")
    except Exception as e:
        print(f"Error altering DECIMAL columns: {e}")
except Exception as e:
    print(f"Error adding balance_usd: {e}")
