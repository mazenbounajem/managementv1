import sqlite3

conn = sqlite3.connect('management.db')
cursor = conn.cursor()

for table in ['products', 'suppliers', 'customers']:
    print(f"--- {table} ---")
    cursor.execute(f"PRAGMA table_info({table})")
    for row in cursor.fetchall():
        print(row)
    print()
conn.close()
