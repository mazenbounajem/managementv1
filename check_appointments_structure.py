import pyodbc

def check_appointments_structure():
    try:
        conn_str = 'Driver={SQL Server};Server=DESKTOP-Q7U1STD;Database=POSDB;Trusted_Connection=yes;'
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Check appointments table columns
        cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'appointments'
        ORDER BY ORDINAL_POSITION
        """)
        columns = cursor.fetchall()
        print('Appointments table columns:')
        for col in columns:
            print(f'  {col[0]}: {col[1]} ({col[2]}) - Default: {col[3]}')

        # Check if service_id column exists
        cursor.execute("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'appointments' AND COLUMN_NAME = 'service_id'
        """)
        has_service_id = cursor.fetchone()
        print(f'\nHas service_id column: {has_service_id is not None}')

        # Check if service_type column exists
        cursor.execute("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'appointments' AND COLUMN_NAME = 'service_type'
        """)
        has_service_type = cursor.fetchone()
        print(f'Has service_type column: {has_service_type is not None}')

        conn.close()

    except Exception as e:
        print(f'Database error: {e}')

if __name__ == "__main__":
    check_appointments_structure()
