from connection import connection

# Add account_code column to purchases table if it doesn't exist
try:
    connection.update_supplierbalance("IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('purchases') AND name = 'account_code') ALTER TABLE purchases ADD account_code NVARCHAR(10) DEFAULT '6011'", ())
    print("account_code column added or already exists")
except Exception as e:
    print(f"Error: {e}")
