
import pyodbc
import json

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

def analyze_db():
    conn_str = get_connection_string()
    db_info = {}
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
        tables = [row.TABLE_NAME for row in cursor.fetchall()]
        
        for table in tables:
            db_info[table] = {"columns": [], "foreign_keys": []}
            
            # Get identity columns
            cursor.execute(f"""
                SELECT name
                FROM sys.columns
                WHERE object_id = OBJECT_ID(?) AND is_identity = 1
            """, (table,))
            identities = [row.name for row in cursor.fetchall()]
            
            # Get columns
            cursor.execute(f"""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = ?
            """, (table,))
            for col in cursor.fetchall():
                db_info[table]["columns"].append({
                    "name": col.COLUMN_NAME,
                    "type": col.DATA_TYPE,
                    "nullable": col.IS_NULLABLE == "YES",
                    "max_length": col.CHARACTER_MAXIMUM_LENGTH,
                    "is_identity": col.COLUMN_NAME in identities
                })
                
            # Get foreign keys
            cursor.execute(f"""
                SELECT
                    fk.name AS FK_NAME,
                    tp.name AS PARENT_TABLE,
                    cp.name AS PARENT_COLUMN,
                    tr.name AS REFERENCED_TABLE,
                    cr.name AS REFERENCED_COLUMN
                FROM sys.foreign_keys AS fk
                INNER JOIN sys.foreign_key_columns AS fkc ON fk.object_id = fkc.constraint_object_id
                INNER JOIN sys.tables AS tp ON fkc.parent_object_id = tp.object_id
                INNER JOIN sys.columns AS cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
                INNER JOIN sys.tables AS tr ON fkc.referenced_object_id = tr.object_id
                INNER JOIN sys.columns AS cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
                WHERE tp.name = ?
            """, (table,))
            for fk in cursor.fetchall():
                db_info[table]["foreign_keys"].append({
                    "fk_name": fk.FK_NAME,
                    "parent_column": fk.PARENT_COLUMN,
                    "referenced_table": fk.REFERENCED_TABLE,
                    "referenced_column": fk.REFERENCED_COLUMN
                })
        
        with open("db_schema.json", "w") as f:
            json.dump(db_info, f, indent=2)
            
        print("Schema saved to db_schema.json")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_db()
