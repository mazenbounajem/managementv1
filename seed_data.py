
import pyodbc
import json
import random
import string
from datetime import datetime, timedelta

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

def get_random_string(length=10):
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for i in range(length))

def get_random_value(col_type, max_length=None):
    if col_type in ['int', 'bigint', 'smallint', 'tinyint']:
        return random.randint(1, 100000)
    elif col_type in ['decimal', 'numeric', 'float', 'real', 'money', 'smallmoney']:
        return round(random.uniform(1.0, 1000.0), 2)
    elif col_type in ['nvarchar', 'varchar', 'char', 'nchar']:
        length = min(max_length or 50, 50)
        return get_random_string(length)
    elif col_type == 'text' or col_type == 'ntext':
        return get_random_string(100)
    elif col_type in ['datetime', 'date', 'smalldatetime', 'datetime2']:
        days_ago = random.randint(0, 365)
        return (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d %H:%M:%S')
    elif col_type == 'time':
        return datetime.now().strftime('%H:%M:%S')
    elif col_type == 'bit':
        return random.choice([0, 1])
    else:
        return None

def seed():
    with open("db_schema.json", "r") as f:
        schema = json.load(f)

    # Topological sort
    visited = set()
    order = []

    def visit(table_name):
        if table_name in visited:
            return
        visited.add(table_name)
        # Visit dependencies first
        for fk in schema[table_name]["foreign_keys"]:
            ref_table = fk["referenced_table"]
            if ref_table in schema and ref_table != table_name:
                visit(ref_table)
        order.append(table_name)

    for table in schema:
        visit(table)

    conn_str = get_connection_string()
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # Store generated IDs for foreign keys
    table_ids = {} # {table_name: [list of primary key values]}

    for table_name in order:
        print(f"Seeding table: {table_name}")
        table_meta = schema[table_name]
        cols = table_meta["columns"]
        fks = {fk["parent_column"]: fk for fk in table_meta["foreign_keys"]}
        
        # Identify PK (usually the identity column)
        pk_col = next((c["name"] for c in cols if c["is_identity"]), None)
        if not pk_col:
            # Fallback to first column if no identity
            pk_col = cols[0]["name"]

        table_ids[table_name] = []
        
        insert_cols = [c for c in cols if not c["is_identity"]]
        col_names = [c["name"] for c in insert_cols]
        placeholders = ["?" for _ in col_names]
        sql = f"INSERT INTO {table_name} ({', '.join(col_names)}) VALUES ({', '.join(placeholders)})"
        
        # Special case: check if it's an identity table and we want to get the inserted id
        has_identity = any(c["is_identity"] for c in cols)

        rows_to_insert = 1000
        for i in range(rows_to_insert):
            values = []
            for col in insert_cols:
                col_name = col["name"]
                if col_name in fks:
                    ref_table = fks[col_name]["referenced_table"]
                    if ref_table in table_ids and table_ids[ref_table]:
                        values.append(random.choice(table_ids[ref_table]))
                    else:
                        # Referenced table not seeded or empty, try a random value or NULL
                        if col["nullable"]:
                            values.append(None)
                        else:
                            values.append(get_random_value(col["type"], col["max_length"]))
                else:
                    values.append(get_random_value(col["type"], col["max_length"]))

            try:
                cursor.execute(sql, values)
                if has_identity:
                    cursor.execute("SELECT @@IDENTITY")
                    new_id = cursor.fetchone()[0]
                    if new_id:
                        table_ids[table_name].append(int(new_id))
                elif pk_col in col_names:
                    # If we inserted the PK manually, track it
                    idx = col_names.index(pk_col)
                    table_ids[table_name].append(values[idx])
                
                if i % 100 == 0:
                    conn.commit()
            except Exception as e:
                print(f"Error inserting into {table_name} at row {i}: {e}")
                # continue to next row or table
        
        conn.commit()
        print(f"Finished seeding {table_name}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    seed()
