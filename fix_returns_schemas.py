import pyodbc
from database_manager import db_manager

def fix_returns_schema():
    print("Fixing purchase_returns and sales_returns schemas...")
    
    # 1. Fix purchase_returns
    queries_purchase = [
        "IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('purchase_returns') AND name = 'auxiliary_number') ALTER TABLE purchase_returns ADD auxiliary_number NVARCHAR(50)",
        "IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('purchase_returns') AND name = 'account_code') ALTER TABLE purchase_returns ADD account_code NVARCHAR(50)",
        "IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('purchase_returns') AND name = 'user_id') ALTER TABLE purchase_returns ADD user_id INT",
        "IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('purchase_returns') AND name = 'currency_id') ALTER TABLE purchase_returns ADD currency_id INT",
        "IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('purchase_returns') AND name = 'total_vat') ALTER TABLE purchase_returns ADD total_vat DECIMAL(18, 2)",
        "IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('purchase_returns') AND name = 'status') ALTER TABLE purchase_returns ADD status NVARCHAR(50)"
    ]
    
    # 2. Fix sales_returns
    queries_sales = [
        "IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('sales_returns') AND name = 'auxiliary_number') ALTER TABLE sales_returns ADD auxiliary_number NVARCHAR(50)",
        "IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('sales_returns') AND name = 'user_id') ALTER TABLE sales_returns ADD user_id INT",
        "IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('sales_returns') AND name = 'currency_id') ALTER TABLE sales_returns ADD currency_id INT",
        "IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('sales_returns') AND name = 'total_vat') ALTER TABLE sales_returns ADD total_vat DECIMAL(18, 2)",
        "IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('sales_returns') AND name = 'status') ALTER TABLE sales_returns ADD status NVARCHAR(50)"
    ]

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        
        print("Updating purchase_returns...")
        for q in queries_purchase:
            try:
                cursor.execute(q)
                conn.commit()
            except Exception as e:
                print(f"Error executing purchase query {q[:50]}...: {e}")
                
        print("Updating sales_returns...")
        for q in queries_sales:
            try:
                cursor.execute(q)
                conn.commit()
            except Exception as e:
                print(f"Error executing sales query {q[:50]}...: {e}")
                
    print("Schema updates completed.")

if __name__ == "__main__":
    fix_returns_schema()
