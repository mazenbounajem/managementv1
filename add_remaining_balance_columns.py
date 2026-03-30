import sqlite3

db_path = 'd:/managementv1/pos_system.db'

conn = sqlite3.connect(db_path)

# Add remaining_balance to purchases if missing
# Safe ADD COLUMN - only if missing
purch_cursor = conn.execute("PRAGMA table_info(purchases)")
purch_cols = [row[1] for row in purch_cursor.fetchall()]
if 'remaining_balance' not in purch_cols:
    conn.execute("ALTER TABLE purchases ADD COLUMN remaining_balance DECIMAL(15,2) DEFAULT 0")
    conn.execute("UPDATE purchases SET remaining_balance = COALESCE(total_amount, 0) WHERE remaining_balance IS NULL OR remaining_balance = 0")

sales_cursor = conn.execute("PRAGMA table_info(sales)")
sales_cols = [row[1] for row in sales_cursor.fetchall()]
if 'remaining_balance' not in sales_cols:
    conn.execute("ALTER TABLE sales ADD COLUMN remaining_balance DECIMAL(15,2) DEFAULT 0")
    conn.execute("UPDATE sales SET remaining_balance = COALESCE(total_amount, 0) WHERE remaining_balance IS NULL OR remaining_balance = 0")

print("✅ remaining_balance columns safely added/backfilled to purchases & sales!")

conn.commit()
conn.close()

print("✅ remaining_balance columns added to purchases & sales")
print("All pending invoices now track per-invoice remaining balance!")

