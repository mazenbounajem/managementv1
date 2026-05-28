from connection import connection
data = []
connection.contogetrows("SELECT * FROM configuration", data)
print(f"Configuration rows: {len(data)}")
for r in data:
    print(r)
