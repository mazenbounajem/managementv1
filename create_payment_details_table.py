try:
    import pyodbc
    conn = pyodbc.connect("Driver={SQL Server Native Client 11.0};Server=DESKTOP-Q7U1STD\\SQLEXPRESS02;Database=POSDb1Test;Trusted_Connection=yes")
    cursor = conn.cursor()
    
    # Create supplier_payment_details
    table_name = 'supplier_payment_details'
    cursor.execute(f"SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '{table_name}'")
    if cursor.fetchone()[0] == 0:
        print(f"Creating {table_name} table...")
        create_sql = f"""
        CREATE TABLE {table_name} (
            id INT IDENTITY(1,1) PRIMARY KEY,
            payment_id INT NOT NULL,
            source_type VARCHAR(50) NOT NULL,
            source_id INT NOT NULL,
            settlement_amount DECIMAL(18,2) NOT NULL,
            created_at DATETIME DEFAULT GETDATE(),
            FOREIGN KEY (payment_id) REFERENCES supplier_payment(id)
        )
        """
        cursor.execute(create_sql)
        conn.commit()
        print(f"Table {table_name} created.")
    else:
        print(f"Table {table_name} already exists.")
        
    conn.close()
except Exception as e:
    print("Error:", e)
