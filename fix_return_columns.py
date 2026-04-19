from connection import db_manager

def run_alter(table_name, col_name, dtype):
    try:
        # Check if column exists
        check_query = f"SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}' AND COLUMN_NAME = '{col_name}'"
        exists = db_manager.execute_scalar(check_query)
        if not exists:
            print(f"Adding {col_name} to {table_name}...")
            db_manager.execute_update(f"ALTER TABLE {table_name} ADD {col_name} {dtype} NULL")
        else:
            print(f"Column {col_name} already exists in {table_name}.")
    except Exception as e:
        print(f"Error altering {table_name}: {e}")

run_alter('purchase_returns', 'account_code', 'NVARCHAR(20)')
run_alter('purchase_returns', 'auxiliary_number', 'NVARCHAR(20)')
run_alter('sales_returns', 'account_code', 'NVARCHAR(20)')
run_alter('sales_returns', 'auxiliary_number', 'NVARCHAR(20)')
