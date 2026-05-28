from connection import connection
data = []
connection.contogetrows("SELECT * FROM vat_settings", data)
print(f"VAT Settings rows: {len(data)}")
for r in data:
    print(r)
