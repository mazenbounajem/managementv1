
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

def create_config_table():
    conn_str = get_connection_string()
    conn = pyodbc.connect(conn_str, autocommit=True)
    cursor = conn.cursor()

    try:
        # Create table if it doesn't exist
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='configuration' AND xtype='U')
            BEGIN
                CREATE TABLE configuration (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    setting_key VARCHAR(100) UNIQUE NOT NULL,
                    setting_value NVARCHAR(1000) NULL,
                    description NVARCHAR(500) NULL,
                    updated_at DATETIME DEFAULT GETDATE()
                )
                PRINT 'Table configuration created.'
            END
            ELSE
            BEGIN
                PRINT 'Table configuration already exists.'
            END
        """)

        # Insert default backup directory setting if it doesn't exist
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM configuration WHERE setting_key = 'backup_directory')
            BEGIN
                INSERT INTO configuration (setting_key, setting_value, description, updated_at)
                VALUES ('backup_directory', 'C:\\dbbackup\\backups', 'Directory where database backups are saved.', GETDATE())
                PRINT 'Inserted default backup_directory setting.'
            END
            ELSE
            BEGIN
                PRINT 'Setting backup_directory already exists.'
            END
        """)
        
        # Another setting for auto backups
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM configuration WHERE setting_key = 'auto_backup_enabled')
            BEGIN
                INSERT INTO configuration (setting_key, setting_value, description, updated_at)
                VALUES ('auto_backup_enabled', 'false', 'Enable or disable automatic daily backups.', GETDATE())
                PRINT 'Inserted auto_backup_enabled setting.'
            END
        """)

        # Fetch and show contents
        cursor.execute("SELECT setting_key, setting_value FROM configuration")
        print("\n--- Current Configuration ---")
        for row in cursor.fetchall():
            print(f"{row.setting_key}: {row.setting_value}")
            
    except Exception as e:
        print(f"Error creating table: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    create_config_table()
