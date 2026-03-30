from database_manager import db_manager

def migrate():
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Add user_id column
            cursor.execute('''
                IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('sales') AND name = 'user_id')
                ALTER TABLE sales ADD user_id INT
            ''')
            
            # Add status column
            cursor.execute('''
                IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('sales') AND name = 'status')
                ALTER TABLE sales ADD status NVARCHAR(50) DEFAULT 'Sale'
            ''')
            
            # Update existing status to 'Sale'
            cursor.execute("UPDATE sales SET status = 'Sale' WHERE status IS NULL")
            
            # Add foreign key for user_id if users table exists
            cursor.execute('''
                IF EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
                AND NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_sales_users')
                ALTER TABLE sales ADD CONSTRAINT FK_sales_users FOREIGN KEY (user_id) REFERENCES users(id)
            ''')
            
            conn.commit()
            print("Migration successful: Added user_id and status to sales table.")
            
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
