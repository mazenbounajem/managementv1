import pyodbc
from database_manager import db_manager
from create_pos_tables import create_tables

def clear_database():
    """
    Clear all data from the database by dropping and recreating all tables.
    Handles foreign key constraints automatically by disabling them during drop.
    """
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Disable all foreign key constraints to allow dropping tables
            cursor.execute("EXEC sp_MSforeachtable 'ALTER TABLE ? NOCHECK CONSTRAINT all'")

            # Get all user tables (excluding system tables)
            cursor.execute("""
                SELECT TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_TYPE = 'BASE TABLE'
                AND TABLE_SCHEMA = 'dbo'
            """)
            tables = [row[0] for row in cursor.fetchall()]

            # Drop all tables
            for table in tables:
                try:
                    cursor.execute(f"DROP TABLE IF EXISTS [{table}]")
                    print(f"Dropped table: {table}")
                except Exception as e:
                    print(f"Error dropping {table}: {str(e)}")

            # Re-enable foreign key constraints
            cursor.execute("EXEC sp_MSforeachtable 'ALTER TABLE ? CHECK CONSTRAINT all'")

            conn.commit()

        # Recreate all tables with their structures
        create_tables()

        print("Database cleared and recreated successfully!")
        print("All data has been deleted and table structures restored.")

    except Exception as e:
        print(f"Error clearing database: {str(e)}")
        raise

if __name__ == "__main__":
    clear_database()
