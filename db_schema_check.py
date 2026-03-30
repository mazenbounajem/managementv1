import sqlite3

db = sqlite3.connect('pos_system.db')
cursor = db.cursor()

print("=== TABLES ===")
tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
for t in tables:
    print(f"- {t[0]}")

print("\n=== PURCHASES COLUMNS (if exists) ===")
try:
    cols = cursor.execute("PRAGMA table_info(purchases);").fetchall()
    for col in cols:
        print(f"  {col[1]} ({col[2]})")
except:
    print("purchases table NOT FOUND")

print("\n=== SALES COLUMNS (if exists) ===")
try:
    cols = cursor.execute("PRAGMA table_info(sales);").fetchall()
    for col in cols:
        print(f"  {col[1]} ({col[2]})")
except:
    print("sales table NOT FOUND")

db.close()

