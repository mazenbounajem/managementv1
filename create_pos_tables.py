import pyodbc

def create_tables():
    """Create POS system tables in SQL Server 2014 for POSDB database"""
    
    try:
        conn_str = (
            "Driver={SQL Server};"
            "Server=DESKTOP-Q7U1STD;"
            "Database=POSDB;"
            "Trusted_Connection=yes;"
        )
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Create categories table
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='categories' AND xtype='U')
            CREATE TABLE categories (
                id INT IDENTITY(1,1) PRIMARY KEY,
                category_name NVARCHAR(100) NOT NULL,
                description NVARCHAR(500),
                created_at DATETIME DEFAULT GETDATE()
            )
        ''')
        
        # Create products table with all necessary columns
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='products' AND xtype='U')
            CREATE TABLE products (
                id INT IDENTITY(1,1) PRIMARY KEY,
                product_name NVARCHAR(200) NOT NULL,
                barcode NVARCHAR(50) UNIQUE,
                sku NVARCHAR(50) UNIQUE,
                description NVARCHAR(1000),
                category_id INT,
                price DECIMAL(10,2) NOT NULL,
                cost_price DECIMAL(10,2),
                stock_quantity INT DEFAULT 0,
                min_stock_level INT DEFAULT 0,
                max_stock_level INT DEFAULT 0,
                supplier_id INT,
                created_at DATETIME DEFAULT GETDATE(),
                updated_at DATETIME DEFAULT GETDATE(),
                is_active BIT DEFAULT 1,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        ''')
        
        # Create suppliers table
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='suppliers' AND xtype='U')
            CREATE TABLE suppliers (
                id INT IDENTITY(1,1) PRIMARY KEY,
                name NVARCHAR(200) NOT NULL,
                contact_person NVARCHAR(100),
                email NVARCHAR(100),
                phone NVARCHAR(20),
                address NVARCHAR(500),
                city NVARCHAR(100),
                state NVARCHAR(100),
                zip_code NVARCHAR(20),
                country NVARCHAR(100) DEFAULT 'USA',
                balance DECIMAL(10,2) DEFAULT 0,
                created_at DATETIME DEFAULT GETDATE(),
                is_active BIT DEFAULT 1
            )
        ''')
        
        # Create customers table
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='customers' AND xtype='U')
            CREATE TABLE customers (
                id INT IDENTITY(1,1) PRIMARY KEY,
                customer_name NVARCHAR(200) NOT NULL,
                email NVARCHAR(100) UNIQUE,
                phone NVARCHAR(20),
                address NVARCHAR(500),
                city NVARCHAR(100),
                state NVARCHAR(100),
                zip_code NVARCHAR(20),
                balance DECIMAL(10,2) DEFAULT 0,
                created_at DATETIME DEFAULT GETDATE(),
                is_active BIT DEFAULT 1
            )
        ''')
        
        # Create sales table
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='sales' AND xtype='U')
            CREATE TABLE sales (
                id INT IDENTITY(1,1) PRIMARY KEY,
                sale_date DATETIME DEFAULT GETDATE(),
                customer_id INT,
                subtotal DECIMAL(10,2) NOT NULL,
                discount_amount DECIMAL(10,2) DEFAULT 0,
                tax_amount DECIMAL(10,2) DEFAULT 0,
                total_amount DECIMAL(10,2) NOT NULL,
                payment_method NVARCHAR(50),
                payment_status NVARCHAR(50) DEFAULT 'completed',
                invoice_number NVARCHAR(50) UNIQUE,
                notes NVARCHAR(1000),
                created_at DATETIME DEFAULT GETDATE(),
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        ''')
        
        # Create sale_items table
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='sale_items' AND xtype='U')
            CREATE TABLE sale_items (
                id INT IDENTITY(1,1) PRIMARY KEY,
                sale_id INT NOT NULL,
                product_id INT NOT NULL,
                quantity INT NOT NULL,
                unit_price DECIMAL(10,2) NOT NULL,
                total_price DECIMAL(10,2) NOT NULL,
                discount_amount DECIMAL(10,2) DEFAULT 0,
                created_at DATETIME DEFAULT GETDATE(),
                FOREIGN KEY (sale_id) REFERENCES sales(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')
        
        # Create purchases table
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='purchases' AND xtype='U')
            CREATE TABLE purchases (
                id INT IDENTITY(1,1) PRIMARY KEY,
                purchase_date DATETIME DEFAULT GETDATE(),
                supplier_id INT,
                subtotal DECIMAL(10,2) NOT NULL,
                discount_amount DECIMAL(10,2) DEFAULT 0,
                tax_amount DECIMAL(10,2) DEFAULT 0,
                total_amount DECIMAL(10,2) NOT NULL,
                payment_method NVARCHAR(50),
                payment_status NVARCHAR(50) DEFAULT 'completed',
                invoice_number NVARCHAR(50) UNIQUE,
                notes NVARCHAR(1000),
                created_at DATETIME DEFAULT GETDATE(),
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
            )
        ''')
        
        # Create purchase_items table
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='purchase_items' AND xtype='U')
            CREATE TABLE purchase_items (
                id INT IDENTITY(1,1) PRIMARY KEY,
                purchase_id INT NOT NULL,
                product_id INT NOT NULL,
                quantity INT NOT NULL,
                unit_cost DECIMAL(10,2) NOT NULL,
                total_cost DECIMAL(10,2) NOT NULL,
                unit_price DECIMAL(10,2) NOT NULL DEFAULT 0,
                profit DECIMAL(10,2) NOT NULL DEFAULT 0,
                discount_amount DECIMAL(10,2) DEFAULT 0,
                created_at DATETIME DEFAULT GETDATE(),
                FOREIGN KEY (purchase_id) REFERENCES purchases(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')

        # Create supplier_payment table
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='supplier_payment' AND xtype='U')
            CREATE TABLE supplier_payment (
                id INT IDENTITY(1,1) PRIMARY KEY,
                manual_reference NVARCHAR(100),
                payment_date DATETIME DEFAULT GETDATE(),
                supplier_id INT NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                payment_method NVARCHAR(50),
                status NVARCHAR(50) DEFAULT 'completed',
                notes NVARCHAR(1000),
                created_at DATETIME DEFAULT GETDATE(),
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
            )
        ''')
        
        # Create employees table
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='employees' AND xtype='U')
            CREATE TABLE employees (
                id INT IDENTITY(1,1) PRIMARY KEY,
                first_name NVARCHAR(100) NOT NULL,
                last_name NVARCHAR(100) NOT NULL,
                email NVARCHAR(100) UNIQUE,
                phone NVARCHAR(20),
                address NVARCHAR(500),
                city NVARCHAR(100),
                state NVARCHAR(100),
                zip_code NVARCHAR(20),
                hire_date DATE NOT NULL,
                position NVARCHAR(100) NOT NULL,
                department NVARCHAR(100),
                salary DECIMAL(10,2),
                role_id INT,
                is_active BIT DEFAULT 1,
                termination_date DATE NULL,
                created_at DATETIME DEFAULT GETDATE(),
                updated_at DATETIME DEFAULT GETDATE()
            )
        ''')
        
        # Insert sample data
        cursor.execute("IF NOT EXISTS (SELECT 1 FROM categories WHERE category_name='Electronics') INSERT INTO categories (category_name, description) VALUES ('Electronics', 'Electronic devices and accessories')")
        cursor.execute("IF NOT EXISTS (SELECT 1 FROM categories WHERE category_name='Clothing') INSERT INTO categories (category_name, description) VALUES ('Clothing', 'Apparel and fashion items')")
        cursor.execute("IF NOT EXISTS (SELECT 1 FROM categories WHERE category_name='Food') INSERT INTO categories (category_name, description) VALUES ('Food', 'Food and beverages')")
        
        cursor.execute("IF NOT EXISTS (SELECT 1 FROM products WHERE barcode='1234567890123') INSERT INTO products (product_name, barcode, sku, description, category_id, price, cost_price, stock_quantity) VALUES ('iPhone 14', '1234567890123', 'IPH14', 'Latest iPhone model', 1, 999.99, 750.00, 10)")
        cursor.execute("IF NOT EXISTS (SELECT 1 FROM products WHERE barcode='1234567890124') INSERT INTO products (product_name, barcode, sku, description, category_id, price, cost_price, stock_quantity) VALUES ('Samsung Galaxy S23', '1234567890124', 'SGS23', 'Samsung flagship phone', 1, 899.99, 650.00, 15)")
        cursor.execute("IF NOT EXISTS (SELECT 1 FROM products WHERE barcode='1234567890125') INSERT INTO products (product_name, barcode, sku, description, category_id, price, cost_price, stock_quantity) VALUES ('T-Shirt', '1234567890125', 'TSHIRT', 'Cotton t-shirt', 2, 19.99, 8.00, 50)")
        cursor.execute("IF NOT EXISTS (SELECT 1 FROM products WHERE barcode='1234567890126') INSERT INTO products (product_name, barcode, sku, description, category_id, price, cost_price, stock_quantity) VALUES ('Coffee', '1234567890126', 'COFFEE', 'Premium coffee beans', 3, 12.99, 5.00, 100)")
        
        cursor.execute("IF NOT EXISTS (SELECT 1 FROM customers WHERE email='john@example.com') INSERT INTO customers (customer_name, email, phone, address) VALUES ('John Doe', 'john@example.com', '123-456-7890', '123 Main St')")
        cursor.execute("IF NOT EXISTS (SELECT 1 FROM customers WHERE email='jane@example.com') INSERT INTO customers (customer_name, email, phone, address) VALUES ('Jane Smith', 'jane@example.com', '987-654-3210', '456 Oak Ave')")
        
        # Insert sample employee data
        cursor.execute("IF NOT EXISTS (SELECT 1 FROM employees WHERE email='manager@store.com') INSERT INTO employees (first_name, last_name, email, phone, address, city, state, zip_code, hire_date, position, department, salary, role_id) VALUES ('Sarah', 'Johnson', 'manager@store.com', '555-123-4567', '789 Management Ave', 'Business City', 'NY', '10001', '2023-01-15', 'Store Manager', 'Management', 65000.00, 1)")
        cursor.execute("IF NOT EXISTS (SELECT 1 FROM employees WHERE email='cashier1@store.com') INSERT INTO employees (first_name, last_name, email, phone, address, city, state, zip_code, hire_date, position, department, salary, role_id) VALUES ('Mike', 'Chen', 'cashier1@store.com', '555-234-5678', '456 Cashier St', 'Retail Town', 'NY', '10002', '2023-03-10', 'Cashier', 'Sales', 32000.00, 2)")
        cursor.execute("IF NOT EXISTS (SELECT 1 FROM employees WHERE email='cashier2@store.com') INSERT INTO employees (first_name, last_name, email, phone, address, city, state, zip_code, hire_date, position, department, salary, role_id) VALUES ('Emily', 'Rodriguez', 'cashier2@store.com', '555-345-6789', '123 Sales Rd', 'Commerce City', 'NY', '10003', '2023-05-20', 'Cashier', 'Sales', 31500.00, 2)")
        cursor.execute("IF NOT EXISTS (SELECT 1 FROM employees WHERE email='inventory@store.com') INSERT INTO employees (first_name, last_name, email, phone, address, city, state, zip_code, hire_date, position, department, salary, role_id) VALUES ('David', 'Wilson', 'inventory@store.com', '555-456-7890', '321 Stock Ave', 'Warehouse City', 'NY', '10004', '2023-02-28', 'Inventory Manager', 'Operations', 48000.00, 3)")
        
        conn.commit()
        conn.close()
        print("SQL Server 2014 tables created successfully in POSDB database")
        
    except Exception as e:
        print(f"Error creating SQL Server tables: {e}")

if __name__ == "__main__":
    create_tables()
