from connection import connection

def get_columns(table_name):
    headers = []
    try:
        connection.contogetheaders(f"SELECT * FROM {table_name} WHERE 1=0", headers)
        return headers
    except Exception as e:
        return [f"Error: {e}"]

tables = ['suppliers', 'roles', 'products', 'categories', 'role_permissions', 'users', 'expenses', 'expense_types', 'currencies']
for t in tables:
    cols = get_columns(t)
    print(f"{t}: {cols}")
