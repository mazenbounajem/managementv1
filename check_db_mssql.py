from database_manager import db_manager

def check_table(table):
    print(f"--- {table} ---")
    try:
        results = db_manager.execute_query(f"SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table}'")
        for row in results:
            print(f"{row[0]}: {row[1]}")
    except Exception as e:
        print(f"Error: {e}")
    print()

for t in ['products', 'suppliers', 'customers', 'Ledger', 'auxiliary']:
    check_table(t)
