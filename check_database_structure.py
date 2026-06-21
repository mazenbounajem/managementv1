import pyodbc

def check_database_structure():
    try:
        conn_str = 'Driver={SQL Server};Server=DESKTOP-Q7U1STD;Database=POSDB;Trusted_Connection=yes;'
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        print('=== Database Structure Check ===')

        # Check all tables
        cursor.execute("""
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
        """)
        tables = cursor.fetchall()
        print('\nTables in database:')
        for table in tables:
            print(f'  {table[0]}')

        # Check roles table structure
        print('\n1. Roles table structure:')
        cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'roles'
        ORDER BY ORDINAL_POSITION
        """)
        columns = cursor.fetchall()
        for col in columns:
            print(f'  {col[0]}: {col[1]} ({col[2]})')

        # Check role_permissions table structure
        print('\n2. Role_permissions table structure:')
        cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'role_permissions'
        ORDER BY ORDINAL_POSITION
        """)
        columns = cursor.fetchall()
        for col in columns:
            print(f'  {col[0]}: {col[1]} ({col[2]})')

        # Check users table structure
        print('\n3. Users table structure:')
        cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'users'
        ORDER BY ORDINAL_POSITION
        """)
        columns = cursor.fetchall()
        for col in columns:
            print(f'  {col[0]}: {col[1]} ({col[2]})')

        # Check services table structure
        print('\n4. Services table structure:')
        cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'services'
        ORDER BY ORDINAL_POSITION
        """)
        columns = cursor.fetchall()
        for col in columns:
            print(f'  {col[0]}: {col[1]} ({col[2]})')

        # Check appointments table structure
        print('\n5. Appointments table structure:')
        cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'appointments'
        ORDER BY ORDINAL_POSITION
        """)
        columns = cursor.fetchall()
        for col in columns:
            print(f'  {col[0]}: {col[1]} ({col[2]})')

        # Check sample data
        print('\n6. Sample data check:')

        # Roles
        cursor.execute("SELECT COUNT(*) FROM roles")
        roles_count = cursor.fetchone()[0]
        print(f'  Roles: {roles_count}')

        # Users
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]
        print(f'  Users: {users_count}')

        # Services
        cursor.execute("SELECT COUNT(*) FROM services")
        services_count = cursor.fetchone()[0]
        print(f'  Services: {services_count}')

        # Appointments
        cursor.execute("SELECT COUNT(*) FROM appointments")
        appointments_count = cursor.fetchone()[0]
        print(f'  Appointments: {appointments_count}')

        # Role permissions
        cursor.execute("SELECT COUNT(*) FROM role_permissions")
        permissions_count = cursor.fetchone()[0]
        print(f'  Role permissions: {permissions_count}')

        conn.close()
        print('\n=== Database Structure Check Complete ===')

    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    check_database_structure()
