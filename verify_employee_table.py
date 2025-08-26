from connection import connection

def verify_employee_table():
    """Verify that the employee table was created successfully"""
    
    # Check if employees table exists
    tables = connection.get_all_tables()
    print("Available tables:", tables)
    
    if 'employees' in tables:
        print("✓ Employees table exists!")
        
        # Get column headers
        headers = []
        connection.contogetheaders('SELECT * FROM employees WHERE 1=0', headers)
        print("Employee table columns:")
        for header in headers:
            print(f"  {header}")
            
        # Check sample data
        print("\nSample employee data:")
        data = []
        connection.contogetrows('SELECT first_name, last_name, position, department FROM employees', data)
        for row in data:
            print(f"  {row[0]} {row[1]} - {row[2]} ({row[3]})")
            
    else:
        print("✗ Employees table not found")

if __name__ == "__main__":
    verify_employee_table()
