
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

def check_ranges():
    conn_str = get_connection_string()
    results = []
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
        tables = [row.TABLE_NAME for row in cursor.fetchall()]
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ? AND COLUMN_NAME = 'id'", (table,))
                if cursor.fetchone():
                    cursor.execute(f"SELECT MIN(id), MAX(id), COUNT(*) FROM [{table}]")
                    row = cursor.fetchone()
                    results.append(f"{table}: Min={row[0]}, Max={row[1]}, Count={row[2]}")
                else:
                    cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
                    count = cursor.fetchone()[0]
                    results.append(f"{table}: Min=N/A, Max=N/A, Count={count}")
            except Exception as e:
                results.append(f"{table}: Error {e}")
            
        with open("table_ranges.txt", "w") as f:
            f.write("\n".join(results))
            
        print("Ranges saved to table_ranges.txt")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_ranges()
