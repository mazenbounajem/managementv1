
import pyodbc

conn = pyodbc.connect('Driver={SQL Server Native Client 11.0};Server=DESKTOP-Q7U1STD\\SQLEXPRESS02;Database=POSDB;Trusted_Connection=yes')
cursor = conn.cursor()

# Get columns
cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'role_permissions'")
columns = [row[0] for row in cursor.fetchall()]
print(f"Columns: {columns}")

# Get permissions for role 1, handling multiple users or what not
cursor.execute("SELECT * FROM role_permissions WHERE role_id = 1")
rows = cursor.fetchall()
print(f"Role 1 has {len(rows)} permissions recorded.")
if len(rows) > 0:
    for r in rows[:5]:
        print(r)

cursor.close()
conn.close()
