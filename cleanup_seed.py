
import pyodbc
import re

CONNECTION_CONFIG = {
    "driver": "SQL Server Native Client 11.0",
    "server": "DESKTOP-Q7U1STD\\SQLEXPRESS02",
    "database": "POSDB",
    "trusted_connection": "yes"
}

def get_connection_string():
    return (
        f"Driver={{{CONNECTION_CONFIG['driver']}}};"
        f"Server={CONNECTION_CONFIG['server']};"
        f"Database={CONNECTION_CONFIG['database']};"
        f"Trusted_Connection={CONNECTION_CONFIG['trusted_connection']};"
    )

def cleanup():
    # Even more careful order (delete leaves first)
    deletion_order = [
        "purchase_returns", "purchase_return_items",
        "sales_return_items", "sales_returns",
        "sale_items", "sales_payment", "sales",
        "purchase_items", "purchase_payment", "purchases",
        "customer_payments", "customer_receipt", "customers",
        "supplier_payment", "suppliers",
        "appointments", "services", "employees",
        "stock_operation_items", "stock_operations",
        "price_cost_date_history", "products", "categories",
        "cash_drawer_operations", "cash_drawer",
        "accounting_transaction_lines", "accounting_transactions",
        "expenses", "expense_types",
        "Ledger", "auxiliary",
        "role_permissions", "roles", "vat_settings", "subtype",
        "user_sessions", "users", "currencies"
    ]

    ranges = {}
    if os.path.exists("table_ranges.txt"):
        with open("table_ranges.txt", "r") as f:
            for line in f:
                match = re.match(r"(.+): Min=(.+), Max=(.+), Count=(.+)", line)
                if match:
                    table, min_id, max_id, count = match.groups()
                    ranges[table] = (min_id, max_id)

    conn_str = get_connection_string()
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    log = []

    # Run in a loop to handle layered dependencies if needed
    for table in deletion_order:
        if table in ranges:
            min_id, max_id = ranges[table]
            if min_id != "N/A" and min_id != "None" and min_id is not None:
                try:
                    cursor.execute(f"DELETE FROM [{table}] WHERE id >= ? AND id <= ?", (min_id, max_id))
                    conn.commit()
                    log.append(f"Deleted {cursor.rowcount} rows from {table}")
                except Exception as e:
                    log.append(f"Error cleaning {table}: {e}")
            elif table in ["accounting_transactions", "accounting_transaction_lines"]:
                # Special case: no ID but maybe we can delete by some other field?
                # Actually, if I can't identify them, I'll just leave them for now.
                log.append(f"Skipping {table} (No ID range)")
        else:
            # Try to delete from table regardless if it's very large? No.
            log.append(f"Table {table} not in ranges.")

    with open("cleanup_log.txt", "w") as f:
        f.write("\n".join(log))
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    import os
    cleanup()
