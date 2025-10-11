from connection import connection

# Get schema of purchases table
schema = []
connection.contogetrows("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'purchases' ORDER BY ORDINAL_POSITION", schema)
print("Purchases table columns:")
for col in schema:
    print(f"  {col[0]}")
