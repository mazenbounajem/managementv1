from connection import connection
import pyodbc

def check_database_structure():
    try:
        # Get all tables
        tables = connection.get_all_tables()
        print("All tables:", tables)
        
        # Check for purchase-related tables
        purchase_tables = []
        for table in tables:
            if 'purchase' in table.lower():
                purchase_tables.append(table)
        
        print("\nPurchase tables found:", purchase_tables)
        
        # Check suppliers table structure
        if 'suppliers' in tables:
            print("\nSuppliers table structure:")
            conn = pyodbc.connect('DRIVER={SQL Server Native Client 11.0};SERVER=DESKTOP-Q7U1STD;DATABASE=POSDB;Trusted_Connection=yes')
            cursor = conn.cursor()
            cursor.execute("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'suppliers' ORDER BY ORDINAL_POSITION")
            supplier_columns = cursor.fetchall()
            for col in supplier_columns:
                print(f"  {col[0]}: {col[1]}")
        
        # Check sales table structure for reference
        if 'sales' in tables:
            print("\nSales table structure (for reference):")
            cursor.execute("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'sales' ORDER BY ORDINAL_POSITION")
            sales_columns = cursor.fetchall()
            for col in sales_columns:
                print(f"  {col[0]}: {col[1]}")
                
        if 'sale_items' in tables:
            print("\nSale_items table structure (for reference):")
            cursor.execute("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'sale_items' ORDER BY ORDINAL_POSITION")
            sale_items_columns = cursor.fetchall()
            for col in sale_items_columns:
                print(f"  {col[0]}: {col[1]}")
                
    except Exception as e:
        print(f"Error checking database structure: {e}")

if __name__ == "__main__":
    check_database_structure()
