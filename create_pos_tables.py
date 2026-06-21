import pyodbc

def create_tables():
    """Create POS system tables in SQL Server 2014 for POSDB database"""
    
    try:
        conn_str = (
            "Driver={SQL Server Native Client 11.0};"
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
                photo NVARCHAR(500),
                created_at DATETIME DEFAULT GETDATE(),
                updated_at DATETIME DEFAULT GETDATE(),
                is_active BIT DEFAULT 1,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        ''')

        # Add photo column to existing products table if it doesn't exist
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('products') AND name = 'photo')
            ALTER TABLE products ADD photo NVARCHAR(500)
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

        # Add auxiliary_id column to customers table if it doesn't exist
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('customers') AND name = 'auxiliary_id')
            ALTER TABLE customers ADD auxiliary_id NVARCHAR(10)
        ''')

        # Add auxiliary_number column to customers table if it doesn't exist
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('customers') AND name = 'auxiliary_number')
            ALTER TABLE customers ADD auxiliary_number NVARCHAR(10)
        ''')

        # Add auxiliary_id column to suppliers table if it doesn't exist
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('suppliers') AND name = 'auxiliary_id')
            ALTER TABLE suppliers ADD auxiliary_id NVARCHAR(10)
        ''')

        # Add auxiliary_number column to suppliers table if it doesn't exist
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('suppliers') AND name = 'auxiliary_number')
            ALTER TABLE suppliers ADD auxiliary_number NVARCHAR(10)
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
                account_code NVARCHAR(10) DEFAULT '6011',
                auxiliary_number NVARCHAR(10),
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
            )
        ''')

        # Drop auxiliary_id column from purchases table if it exists
        cursor.execute('''
            IF EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('purchases') AND name = 'auxiliary_id')
            ALTER TABLE purchases DROP COLUMN auxiliary_id
        ''')

        # Add auxiliary_number column to purchases table if it doesn't exist
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('purchases') AND name = 'auxiliary_number')
            ALTER TABLE purchases ADD auxiliary_number NVARCHAR(10)
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

        # Create price_cost_date_history table
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='price_cost_date_history' AND xtype='U')
            CREATE TABLE price_cost_date_history (
                id INT IDENTITY(1,1) PRIMARY KEY,
                product_id INT NOT NULL,
                old_price DECIMAL(10,2),
                new_price DECIMAL(10,2),
                old_cost_price DECIMAL(10,2),
                new_cost_price DECIMAL(10,2),
                change_date DATETIME DEFAULT GETDATE(),
                changed_by NVARCHAR(100),
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

        # Create purchase_payment table
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='purchase_payment' AND xtype='U')
            CREATE TABLE purchase_payment (
                id INT IDENTITY(1,1) PRIMARY KEY,
                purchase_id INT NOT NULL,
                purchase_invoice_number NVARCHAR(50) NOT NULL,
                total_amount DECIMAL(10,2) NOT NULL,
                purchase_date DATETIME NOT NULL,
                created_date DATETIME DEFAULT GETDATE(),
                supplier_id INT NOT NULL,
                status NVARCHAR(50) DEFAULT 'pending',
                amount_paid DECIMAL(10,2) NOT NULL,
                payment_method NVARCHAR(50),
                debit DECIMAL(10,2) NOT NULL,
                credit  DECIMAL(10,2) NOT NULL,
                notes NVARCHAR(1000),
                FOREIGN KEY (purchase_id) REFERENCES purchases(id),
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
            )
        ''')

        # Create sales_payment table
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='sales_payment' AND xtype='U')
            CREATE TABLE sales_payment (
                id INT IDENTITY(1,1) PRIMARY KEY,
                sales_id INT NOT NULL,
                customer_id INT NOT NULL,
                invoice_number NVARCHAR(50) NOT NULL,
                total_amount DECIMAL(10,2) NOT NULL,
                sale_date DATETIME NOT NULL,
                payment_status NVARCHAR(50) DEFAULT 'pending',
                debit DECIMAL(10,2) NOT NULL DEFAULT 0,
                credit DECIMAL(10,2) NOT NULL DEFAULT 0,
                notes NVARCHAR(1000),
                FOREIGN KEY (sales_id) REFERENCES sales(id),
                FOREIGN KEY (customer_id) REFERENCES customers(id)
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

        # Create Ledger table
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Ledger' AND xtype='U')
            CREATE TABLE Ledger (
                Id INT IDENTITY(1,1) PRIMARY KEY,
                AccountNumber NVARCHAR(50) NOT NULL,
                SubNumber NVARCHAR(50),
                ParentId INT,
                Name_en NVARCHAR(200) NOT NULL,
                Name_fr NVARCHAR(200),
                Name_ar NVARCHAR(200),
                UpdateDate DATETIME DEFAULT GETDATE(),
                Status INT DEFAULT 1
            )
        ''')

        # Create auxiliary table
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='auxiliary' AND xtype='U')
            CREATE TABLE auxiliary (
                id INT IDENTITY(1,1) PRIMARY KEY,
                auxiliary_id INT,
                account_name NVARCHAR(200) NOT NULL,
                number NVARCHAR(50)
            )
        ''')

        # Add status column to auxiliary table if it doesn't exist
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('auxiliary') AND name = 'status')
            ALTER TABLE auxiliary ADD status INT DEFAULT 1
        ''')

        # Add update_date column to auxiliary table if it doesn't exist
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('auxiliary') AND name = 'update_date')
            ALTER TABLE auxiliary ADD update_date DATETIME DEFAULT GETDATE()
        ''')

        # Add ledger_id column to auxiliary table if it doesn't exist
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('auxiliary') AND name = 'ledger_id')
            ALTER TABLE auxiliary ADD ledger_id INT
        ''')

        # Add short_cut column to auxiliary table if it doesn't exist
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('auxiliary') AND name = 'short_cut')
            ALTER TABLE auxiliary ADD short_cut NVARCHAR(200)
        ''')

        # Create subtype table
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='subtype' AND xtype='U')
            CREATE TABLE subtype (
                id INT IDENTITY(1,1) PRIMARY KEY,
                code NVARCHAR(50) NOT NULL UNIQUE,
                name NVARCHAR(200) NOT NULL,
                sequence INT DEFAULT 0,
                created_at DATETIME DEFAULT GETDATE(),
                updated_at DATETIME DEFAULT GETDATE()
            )
        ''')

        # Create journal_voucher_header table
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='journal_voucher_header' AND xtype='U')
            CREATE TABLE journal_voucher_header (
                id INT IDENTITY(1,1) PRIMARY KEY,
                date DATETIME DEFAULT GETDATE(),
                voucher_number NVARCHAR(50) NOT NULL UNIQUE,
                subtype_code NVARCHAR(50),
                manual_reference NVARCHAR(200),
                created_at DATETIME DEFAULT GETDATE(),
                FOREIGN KEY (subtype_code) REFERENCES subtype(code)
            )
        ''')

        # Create journal_voucher_lines table
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='journal_voucher_lines' AND xtype='U')
            CREATE TABLE journal_voucher_lines (
                id INT IDENTITY(1,1) PRIMARY KEY,
                header_id INT NOT NULL,
                account NVARCHAR(50),
                currency_code NVARCHAR(10),
                debit DECIMAL(18,2) DEFAULT 0,
                credit DECIMAL(18,2) DEFAULT 0,
                lbp_value DECIMAL(18,2) DEFAULT 0,
                usd_value DECIMAL(18,2) DEFAULT 0,
                parity_rate DECIMAL(10,4) DEFAULT 0,
                remark NVARCHAR(500),
                created_at DATETIME DEFAULT GETDATE(),
                FOREIGN KEY (header_id) REFERENCES journal_voucher_header(id),
                FOREIGN KEY (account) REFERENCES auxiliary(number),
                FOREIGN KEY (currency_code) REFERENCES currencies(currency_code)
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

        # Insert main ledger accounts
        cursor.execute("IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountNumber='4111') INSERT INTO Ledger (AccountNumber, Name_en, Status) VALUES ('4111', 'Customers', 1)")
        cursor.execute("IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountNumber='4011') INSERT INTO Ledger (AccountNumber, Name_en, Status) VALUES ('4011', 'Suppliers', 1)")
        cursor.execute("IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountNumber='7011') INSERT INTO Ledger (AccountNumber, Name_en, Status) VALUES ('7011', 'Sales', 1)")
        cursor.execute("IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountNumber='6011') INSERT INTO Ledger (AccountNumber, Name_en, Status) VALUES ('6011', 'Purchases', 1)")
        cursor.execute("IF NOT EXISTS (SELECT 1 FROM Ledger WHERE AccountNumber='6261') INSERT INTO Ledger (AccountNumber, Name_en, Status) VALUES ('6261', 'Expenses', 1)")

        # Fill auxiliary table from Ledger where AccountNumber has more than 3 characters
        cursor.execute('''
            INSERT INTO auxiliary (auxiliary_id, account_name, update_date)
            SELECT AccountNumber, Name_en, GETDATE()
            FROM Ledger
            WHERE LEN(AccountNumber) > 3
            AND NOT EXISTS (SELECT 1 FROM auxiliary WHERE auxiliary_id = Ledger.AccountNumber)
        ''')
        
        conn.commit()
        conn.close()
        print("SQL Server 2014 tables created successfully in POSDB database")
        
    except Exception as e:
        print(f"Error creating SQL Server tables: {e}")

if __name__ == "__main__":
    create_tables()
