from connection import connection

sql = """
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'customers' AND COLUMN_NAME = 'is_default')
BEGIN
    ALTER TABLE customers ADD is_default BIT DEFAULT 0;
END
"""
try:
    connection.insertingtodatabase(sql)
    print("Column is_default checked/added successfully.")
except Exception as e:
    print(f"Error: {e}")
