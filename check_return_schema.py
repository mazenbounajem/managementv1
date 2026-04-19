from connection import db_manager

def check_columns(table_name):
    query = f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}'"
    try:
        results = db_manager.execute_query(query)
        print(f"Columns in {table_name}:")
        cols = [r[0] for r in results]
        print(", ".join(cols))
    except Exception as e:
        print(f"Error checking {table_name}: {e}")

check_columns('purchase_returns')
