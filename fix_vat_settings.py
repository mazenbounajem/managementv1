
from database_manager import db_manager

def create_vat_settings():
    try:
        # Check if table exists
        exists = db_manager.execute_scalar(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'vat_settings'"
        )
        
        if not exists:
            sql = """
            CREATE TABLE vat_settings (
                id INT IDENTITY(1,1) PRIMARY KEY,
                vat_percentage DECIMAL(5,2) NOT NULL,
                effective_date DATE NOT NULL,
                created_at DATETIME DEFAULT GETDATE()
            )
            """
            db_manager.execute_update(sql)
            print("Table 'vat_settings' created successfully.")
            
            # Insert a default VAT record if none exists
            db_manager.execute_update(
                "INSERT INTO vat_settings (vat_percentage, effective_date) VALUES (?, ?)",
                (11.0, '2020-01-01')
            )
            print("Default VAT record inserted.")
        else:
            print("Table 'vat_settings' already exists.")
            
    except Exception as e:
        print(f"Error creating vat_settings table: {e}")

if __name__ == "__main__":
    create_vat_settings()
