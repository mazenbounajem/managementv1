from connection import connection
data = []
connection.contogetrows("SELECT * FROM subtype", data)
print(f"Subtype rows: {len(data)}")
for r in data:
    print(r)
