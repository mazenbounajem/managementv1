
import pyodbc

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

def fix_and_verify():
    conn_str = get_connection_string()
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # 1. Restore common currencies
    cursor.execute("SELECT COUNT(*) FROM currencies")
    if cursor.fetchone()[0] == 0:
        print("Restoring default currencies...")
        cursor.execute("INSERT INTO currencies (currency_code, currency_name, symbol, exchange_rate, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, GETDATE(), GETDATE())", ('USD', 'US Dollar', '$', 1.0, 1))
        cursor.execute("INSERT INTO currencies (currency_code, currency_name, symbol, exchange_rate, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, GETDATE(), GETDATE())", ('EUR', 'Euro', '€', 0.92, 1))
        cursor.execute("INSERT INTO currencies (currency_code, currency_name, symbol, exchange_rate, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, GETDATE(), GETDATE())", ('LBP', 'Lebanese Pound', 'LL', 89500.0, 1))
    
    # 2. Cleanup role_permissions if still high
    cursor.execute("SELECT COUNT(*) FROM role_permissions")
    count = cursor.fetchone()[0]
    if count > 100:
        print(f"Cleaning up {count} role permissions...")
        cursor.execute("DELETE FROM role_permissions WHERE id > 100")
        
    # 3. Cleanup roles if still high
    cursor.execute("SELECT COUNT(*) FROM roles")
    count = cursor.fetchone()[0]
    if count > 100:
        print(f"Cleaning up {count} roles...")
        # Be careful with foreign keys
        try:
            cursor.execute("DELETE FROM roles WHERE id > 100")
        except:
            print("Could not delete some roles due to constraints.")

    conn.commit()
    
    # 4. Final verify
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
    tables = [row.TABLE_NAME for row in cursor.fetchall()]
    
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
            print(f"{table}: {cursor.fetchone()[0]}")
        except:
            pass

    cursor.close()
    conn.close()

if __name__ == "__main__":
    fix_and_verify()
