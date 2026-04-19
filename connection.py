import pandas as pd

from database_manager import db_manager

class connection:
    """Refactored connection class using centralized database management"""
    
    @staticmethod
    def contogetrows(sql='', data=[], params=None):
        """Get rows from database"""
        try:
            if params:
                results = db_manager.execute_query(sql, params)
            else:
                results = db_manager.execute_query(sql)
            data.extend(results)
        except Exception as ex:
            print(f"Error getting rows: {str(ex)}")
    
    @staticmethod
    def contogetrows_with_params(sql='', data=[], params=None):
        """Get rows from database with parameters"""
        try:
            results = db_manager.execute_query(sql, params)
            data.extend(results)
        except Exception as ex:
            print(f"Error getting rows with params: {str(ex)}")
    
    @staticmethod
    def contogetheaders(sqlh='', datah=[]):
        """Get column headers from query"""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sqlh)
                for i in cursor.description:
                    datah.append(i[0])
        except Exception as ex:
            print(f"Error getting headers: {str(ex)}")
    
    @staticmethod
    def insertingtodatabase(sqli='', values=()):
        """Insert data into database"""
        try:
            db_manager.execute_update(sqli, values)
        except Exception as ex:
            print(f"Error inserting data: {str(ex)}")
            raise
    
    @staticmethod
    def deleterow(sqli='', name=''):
        """Delete row from database"""
        try:
            rows_affected = db_manager.execute_update(sqli, name)
            if rows_affected > 0:
                print("Deleted successfully")
        except Exception as ex:
            print(f"Error deleting row: {str(ex)}")
    
    @staticmethod
    def getid(sql='', name=''):
        """Get ID from table based on name"""
        try:
            return db_manager.execute_scalar(sql, name)
        except Exception as ex:
            print(f"Error getting ID: {str(ex)}")
            return None
    
    @staticmethod
    def getrow(sql='', id=0):
        """Get row from table based on ID"""
        try:
            results = db_manager.execute_query(sql, id)
            return results[0] if results else None
        except Exception as ex:
            print(f"Error getting row: {str(ex)}")
            return None
    
    @staticmethod
    def create_users_table():
        """Create users table if it doesn't exist"""
        try:
            # Check if table exists
            table_exists = db_manager.execute_scalar(
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'users'"
            )
            
            if not table_exists:
                create_table_sql = """
                CREATE TABLE users (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    username VARCHAR(255) NOT NULL UNIQUE,
                    password VARCHAR(255) NOT NULL,
                    date_created DATETIME DEFAULT GETDATE(),
                    session VARCHAR(255),
                    login_time DATETIME,
                    logout_time DATETIME,
                    role INT,
                    CONSTRAINT FK_users_roles FOREIGN KEY (role) REFERENCES roles(id)
                )
                """
                db_manager.execute_update(create_table_sql)
        except Exception as ex:
            print(f"Error creating users table: {str(ex)}")

    @staticmethod
    def create_roles_tables():
        """Create roles and role_permissions tables if they don't exist"""
        try:
            # Check if roles table exists
            roles_table_exists = db_manager.execute_scalar(
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'roles'"
            )
            
            if not roles_table_exists:
                create_roles_table_sql = """
                CREATE TABLE roles (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    description VARCHAR(255),
                    created_at DATETIME DEFAULT GETDATE(),
                    updated_at DATETIME DEFAULT GETDATE()
                )
                """
                db_manager.execute_update(create_roles_table_sql)
                
                # Insert default roles
                default_roles = [
                    ('Admin', 'Administrator with full access to all features'),
                    ('Manager', 'Manager with access to most features'),
                    ('Employee', 'Regular employee with limited access')
                ]
                
                for role_name, description in default_roles:
                    db_manager.execute_update(
                        "INSERT INTO roles (name, description) VALUES (?, ?)",
                        (role_name, description)
                    )

            # Check if role_permissions table exists
            permissions_table_exists = db_manager.execute_scalar(
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'role_permissions'"
            )
            
            if not permissions_table_exists:
                create_permissions_table_sql = """
                CREATE TABLE role_permissions (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    role_id INT NOT NULL,
                    page_name VARCHAR(100) NOT NULL,
                    can_access BIT DEFAULT 1,
                    created_at DATETIME DEFAULT GETDATE(),
                    updated_at DATETIME DEFAULT GETDATE(),
                    FOREIGN KEY (role_id) REFERENCES roles(id),
                    UNIQUE(role_id, page_name)
                )
                """
                db_manager.execute_update(create_permissions_table_sql)
                
                # Insert default permissions for Admin role (access to all pages)
                admin_role_id = db_manager.execute_scalar("SELECT id FROM roles WHERE name = 'Admin'")
                if admin_role_id:
                    pages = [
                        'dashboard', 'employees', 'products', 'purchase', 'reports', 'sales',
                        'suppliers', 'supplierpayment', 'category', 'consignment', 'customers',
                        'customerreceipt', 'expenses', 'expensestype', 'accounting', 'roles', 'backup',
                        'appointments', 'timespend', 'stockoperations', 'statistical-reports',
                        'currencies', 'cash-drawer', 'company', 'services', 'ledger', 'auxiliary',
                        'journal_voucher', 'voucher_subtype'
                    ]

                    for page in pages:
                        db_manager.execute_update(
                            "INSERT INTO role_permissions (role_id, page_name, can_access) VALUES (?, ?, ?)",
                            (admin_role_id, page, 1)
                        )
                
                # Insert default permissions for Manager role
                manager_role_id = db_manager.execute_scalar("SELECT id FROM roles WHERE name = 'Manager'")
                if manager_role_id:
                    manager_pages = [
                        'dashboard', 'products', 'purchase', 'sales', 'reports', 'customers', 
                        'suppliers', 'category', 'expenses', 'stockoperations', 'statistical-reports'
                    ]
                    for page in manager_pages:
                        db_manager.execute_update(
                            "INSERT INTO role_permissions (role_id, page_name, can_access) VALUES (?, ?, ?)",
                            (manager_role_id, page, 1)
                        )

                # Insert default permissions for Employee role
                employee_role_id = db_manager.execute_scalar("SELECT id FROM roles WHERE name = 'Employee'")
                if employee_role_id:
                    employee_pages = [
                        'dashboard', 'sales', 'products', 'customers', 'category'
                    ]
                    for page in employee_pages:
                        db_manager.execute_update(
                            "INSERT INTO role_permissions (role_id, page_name, can_access) VALUES (?, ?, ?)",
                            (employee_role_id, page, 1)
                        )

            # Update employees table to include role_id if it doesn't exist
            employees_columns = db_manager.execute_query(
                "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'employees'"
            )
            employees_columns = [col[0] for col in employees_columns]
            
            if 'role_id' not in employees_columns:
                db_manager.execute_update("ALTER TABLE employees ADD role_id INT NULL")
                
        except Exception as ex:
            print(f"Error creating roles tables: {str(ex)}")

    @staticmethod
    def create_default_admin_user():
        """Create default admin user if it doesn't exist"""
        try:
            import hashlib

            # Check if admin user already exists
            admin_exists = db_manager.execute_scalar(
                "SELECT COUNT(*) FROM users WHERE username = 'mazen'"
            )

            if not admin_exists:
                # Create MD5 hash of the password
                password_hash = hashlib.md5('forever12345'.encode('utf-8')).hexdigest()

                # Get role_id for 'Admin'
                admin_role_id = db_manager.execute_scalar("SELECT id FROM roles WHERE name = 'Admin'")

                # Insert admin user with role_id
                db_manager.execute_update(
                    "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    ('mazen', password_hash, admin_role_id)
                )
                print("Default admin user 'mazen' created successfully")
            # Removed the "already exists" message to avoid repeated output

        except Exception as ex:
            print(f"Error creating default admin user: {str(ex)}")
    
    @staticmethod
    def get_all_tables():
        """Get all table names from database"""
        try:
            results = db_manager.execute_query(
                "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'"
            )
            return [row[0] for row in results]
        except Exception as ex:
            print(f"Error getting tables: {str(ex)}")
            return []
    
    @staticmethod
    def check_user_login(username, password_hash):
        """Check user login credentials"""
        try:
            sql = """
            SELECT id, username, role, date_created
            FROM users
            WHERE username = ? AND password = ? AND role IS NOT NULL
            """
            results = db_manager.execute_query(sql, (username, password_hash))
            return results[0] if results else None
        except Exception as ex:
            print(f"Error checking user login: {str(ex)}")
            return None

    @staticmethod
    def get_user_permissions(role_id):
        """Get all permissions for a specific role"""
        try:
            sql = """
            SELECT page_name, can_access
            FROM role_permissions
            WHERE role_id = ?
            """
            results = db_manager.execute_query(sql, role_id)
            # Return as dictionary {page_name: can_access}
            return {row[0]: bool(row[1]) for row in results}
        except Exception as ex:
            print(f"Error getting user permissions: {str(ex)}")
            return {}

    @staticmethod
    def check_page_permission(role_id, page_name):
        """Check if a role has permission to access a specific page"""
        try:
            sql = """
            SELECT can_access
            FROM role_permissions
            WHERE role_id = ? AND page_name = ?
            """
            result = db_manager.execute_scalar(sql, (role_id, page_name))
            return bool(result) if result is not None else False
        except Exception as ex:
            print(f"Error checking page permission: {str(ex)}")
            return False

    @staticmethod
    def get_user_role_info(username):
        """Get user role information by username"""
        try:
            sql = """
            SELECT u.id, u.username, u.role, r.name as role_name
            FROM users u
            LEFT JOIN roles r ON u.role = r.id
            WHERE u.username = ?
            """
            results = db_manager.execute_query(sql, username)
            if results:
                user_id, username, role_id, role_name = results[0]
                return {
                    'user_id': user_id,
                    'username': username,
                    'role_id': role_id,
                    'role_name': role_name
                }
            return None
        except Exception as ex:
            print(f"Error getting user role info: {str(ex)}")
            return None
    @staticmethod
    def getprofit(sql=''):
        """Get row from table based on ID"""
        try:
            results = db_manager.execute_query(sql)
            return results[0] if results else None
        except Exception as ex:
            print(f"Error getting row: {str(ex)}")
            return None
    def getcount(sql=''):
        """Get row from table based on ID"""
        try:
            results = db_manager.execute_query(sql)
            return results[0] if results else None
        except Exception as ex:
            print(f"Error getting row: {str(ex)}")
            return None

    @staticmethod
    def update_product(sql='', params=()):
        """Update product information in database"""
        try:
            rows_affected = db_manager.execute_update(sql, params)
            return rows_affected
        except Exception as ex:
            print(f"Error updating product: {str(ex)}")
            raise
    
    @staticmethod
    def update_customerbalance(sql='', params=()):
        """Update customer balance information in database"""
        try:
            rows_affected = db_manager.execute_update(sql, params)
            return rows_affected
        except Exception as ex:
            print(f"Error updating product: {str(ex)}")
            raise    
    @staticmethod
    def update_supplierbalance(sql='', params=()):
        """Update customer balance information in database"""
        try:
            rows_affected = db_manager.execute_update(sql, params)
            return rows_affected
        except Exception as ex:
            print(f"Error updating product: {str(ex)}")
            raise

    @staticmethod
    def update_cash_drawer_balance(amount, operation_type, user_id, notes=None):
        """Update cash drawer balance and record the operation"""
        try:
            from datetime import datetime

            # First, insert the operation record
            insert_sql = """
            INSERT INTO cash_drawer_operations (operation_date, operation_type, amount, user_id, notes)
            VALUES (?, ?, ?, ?, ?)
            """
            params = (datetime.now(), operation_type, amount, user_id, notes)
            db_manager.execute_update(insert_sql, params)

            # Then update the cash drawer balance
            if operation_type == 'In':
                update_sql = "UPDATE cash_drawer SET current_balance = current_balance + ?, last_updated = ?"
            else:
                update_sql = "UPDATE cash_drawer SET current_balance = current_balance - ?, last_updated = ?"
            update_params = (amount, datetime.now())
            db_manager.execute_update(update_sql, update_params)

            return True
        except Exception as ex:
            print(f"Error updating cash drawer balance: {str(ex)}")
            return False
    @staticmethod
    def contogetsupplier(sql='', data=[]):
        """Get rows from database"""
        try:
            results = db_manager.execute_query(sql)
            # Convert each row to a dictionary
            data.extend([dict(row) for row in results])
        except Exception as ex:
            print(f"Error getting rows: {str(ex)}")
    
    @staticmethod
    def get_all_roles():
        """Get all roles from database for dropdown selection"""
        try:
            results = db_manager.execute_query("SELECT id, name FROM roles ORDER BY name")
            return results
        except Exception as ex:
            print(f"Error getting roles: {str(ex)}")
            return []

    @staticmethod
    def get_role_name_by_id(role_id):
        """Get role name by role ID"""
        try:
            result = db_manager.execute_scalar("SELECT name FROM roles WHERE id = ?", role_id)
            return result
        except Exception as ex:
            print(f"Error getting role name: {str(ex)}")
            return None

    @staticmethod
    def username_exists(username):
        """Check if username already exists in users table"""
        try:
            count = db_manager.execute_scalar("SELECT COUNT(*) FROM users WHERE username = ?", username)
            return count > 0
        except Exception as ex:
            print(f"Error checking username: {str(ex)}")
            return False

    @staticmethod
    def create_user_account(username, password_hash, role_id):
        """Create user account in users table"""
        try:
            sql = "INSERT INTO users (username, password, role) VALUES (?, ?, ?)"
            values = (username, password_hash, role_id)
            db_manager.execute_update(sql, values)
            return True
        except Exception as ex:
            print(f"Error creating user account: {str(ex)}")
            return False

    @staticmethod
    def update_user_account(username, password_hash, role_id):
        """Update user account in users table"""
        try:
            sql = "UPDATE users SET password = ?, role = ? WHERE username = ?"
            values = (password_hash, role_id, username)
            rows_affected = db_manager.execute_update(sql, values)
            return rows_affected > 0
        except Exception as ex:
            print(f"Error updating user account: {str(ex)}")
            return False

    @staticmethod
    def get_company_info():
        """Get company information from database"""
        try:
            results = db_manager.execute_query("SELECT * FROM company_info")
            if results:
                # Convert to dictionary with column names
                columns = ['id', 'company_name', 'address', 'city', 'state', 'zip_code', 
                          'phone', 'email', 'website', 'logo_path', 'created_at', 'updated_at']
                return dict(zip(columns, results[0]))
            return None
        except Exception as ex:
            print(f"Error getting company info: {str(ex)}")
            return None
    
    @staticmethod
    def save_company_info(company_data):
        """Save or update company information"""
        try:
            # Check if company info already exists
            existing_info = connection.get_company_info()
            
            if existing_info:
                # Update existing record
                update_sql = """
                UPDATE company_info 
                SET company_name = ?, address = ?, city = ?, state = ?, zip_code = ?,
                    phone = ?, email = ?, website = ?, logo_path = ?, updated_at = GETDATE()
                WHERE id = ?
                """
                params = (
                    company_data.get('company_name'),
                    company_data.get('address'),
                    company_data.get('city'),
                    company_data.get('state'),
                    company_data.get('zip_code'),
                    company_data.get('phone'),
                    company_data.get('email'),
                    company_data.get('website'),
                    company_data.get('logo_path'),
                    existing_info['id']
                )
                connection.insertingtodatabase(update_sql, params)
                return "Company information updated successfully"
            else:
                # Insert new record
                insert_sql = """
                INSERT INTO company_info 
                (company_name, address, city, state, zip_code, phone, email, website, logo_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = (
                    company_data.get('company_name'),
                    company_data.get('address'),
                    company_data.get('city'),
                    company_data.get('state'),
                    company_data.get('zip_code'),
                    company_data.get('phone'),
                    company_data.get('email'),
                    company_data.get('website'),
                    company_data.get('logo_path')
                )
                connection.insertingtodatabase(insert_sql, params)
                return "Company information saved successfully"
                
        except Exception as ex:
            print(f"Error saving company info: {str(ex)}")
            raise

    @staticmethod
    def get_today_sales():
        """Get today's total sales amount"""
        try:
            sql = """
            SELECT COALESCE(SUM(total_amount), 0)
            FROM sales
            WHERE CAST(sale_date AS DATE) = CAST(GETDATE() AS DATE)
            """
            result = db_manager.execute_scalar(sql)
            return float(result) if result else 0.0
        except Exception as ex:
            print(f"Error getting today's sales: {str(ex)}")
            return 0.0

    @staticmethod
    def get_week_sales():
        """Get this week's total sales amount"""
        try:
            sql = """
            SELECT COALESCE(SUM(total_amount), 0)
            FROM sales
            WHERE DATEPART(WEEK, sale_date) = DATEPART(WEEK, GETDATE())
            AND DATEPART(YEAR, sale_date) = DATEPART(YEAR, GETDATE())
            """
            result = db_manager.execute_scalar(sql)
            return float(result) if result else 0.0
        except Exception as ex:
            print(f"Error getting week's sales: {str(ex)}")
            return 0.0

    @staticmethod
    def get_month_sales():
        """Get this month's total sales amount"""
        try:
            sql = """
            SELECT COALESCE(SUM(total_amount), 0)
            FROM sales
            WHERE DATEPART(MONTH, sale_date) = DATEPART(MONTH, GETDATE())
            AND DATEPART(YEAR, sale_date) = DATEPART(YEAR, GETDATE())
            """
            result = db_manager.execute_scalar(sql)
            return float(result) if result else 0.0
        except Exception as ex:
            print(f"Error getting month's sales: {str(ex)}")
            return 0.0

    @staticmethod
    def get_total_products():
        """Get total number of products"""
        try:
            sql = "SELECT COUNT(*) FROM products"
            result = db_manager.execute_scalar(sql)
            return int(result) if result else 0
        except Exception as ex:
            print(f"Error getting total products: {str(ex)}")
            return 0

    @staticmethod
    def get_total_customers():
        """Get total number of customers"""
        try:
            sql = "SELECT COUNT(*) FROM customers"
            result = db_manager.execute_scalar(sql)
            return int(result) if result else 0
        except Exception as ex:
            print(f"Error getting total customers: {str(ex)}")
            return 0

    @staticmethod
    def get_low_stock_count():
        """Get count of products with low stock (below min_stock_level)"""
        try:
            sql = """
            SELECT COUNT(*)
            FROM products
            WHERE stock_quantity <= min_stock_level AND is_active = 1
            """
            result = db_manager.execute_scalar(sql)
            return int(result) if result else 0
        except Exception as ex:
            print(f"Error getting low stock count: {str(ex)}")
            return 0

    @staticmethod
    def get_sale_items_with_products():
        """Get sale items with product details as DataFrame"""
        try:
            with db_manager.get_connection() as conn:
                query = """
                SELECT s.sale_date, p.barcode, si.product_id, p.product_name, si.quantity AS sold_quantity,
                       si.unit_price, p.stock_quantity AS quantity_from_stock, p.cost_price AS cost
                FROM sale_items si
                JOIN products p ON si.product_id = p.id
                JOIN sales s ON si.sales_id = s.id
                """
                df = pd.read_sql(query, conn)
                return df
        except Exception as ex:
            print(f"Error getting sale items with products: {str(ex)}")
            return None

    @staticmethod
    def ensure_appointments_permission():
        """Ensure all roles have appointments permission"""
        try:
            # Get all roles
            roles = db_manager.execute_query("SELECT id FROM roles")

            # Add appointments permission for each role if it doesn't exist
            for role in roles:
                role_id = role[0]

                # Check if appointments permission already exists
                existing = db_manager.execute_scalar(
                    "SELECT COUNT(*) FROM role_permissions WHERE role_id = ? AND page_name = 'appointments'",
                    role_id
                )

                if not existing:
                    db_manager.execute_update(
                        "INSERT INTO role_permissions (role_id, page_name, can_access) VALUES (?, ?, ?)",
                        (role_id, 'appointments', 1)
                    )
                    print(f"Added appointments permission for role ID {role_id}")

        except Exception as ex:
            print(f"Error ensuring appointments permission: {str(ex)}")

    @staticmethod
    def ensure_services_permission():
        """Ensure all roles have services permission"""
        try:
            # Get all roles
            roles = db_manager.execute_query("SELECT id FROM roles")

            # Add services permission for each role if it doesn't exist
            for role in roles:
                role_id = role[0]

                # Check if services permission already exists
                existing = db_manager.execute_scalar(
                    "SELECT COUNT(*) FROM role_permissions WHERE role_id = ? AND page_name = 'services'",
                    role_id
                )

                if not existing:
                    db_manager.execute_update(
                        "INSERT INTO role_permissions (role_id, page_name, can_access) VALUES (?, ?, ?)",
                        (role_id, 'services', 1)
                    )
                    print(f"Added services permission for role ID {role_id}")

        except Exception as ex:
            print(f"Error ensuring services permission: {str(ex)}")

    @staticmethod
    def ensure_ledger_permission():
        """Ensure all roles have ledger permission"""
        try:
            # Get all roles
            roles = db_manager.execute_query("SELECT id FROM roles")

            # Add ledger permission for each role if it doesn't exist
            for role in roles:
                role_id = role[0]

                # Check if ledger permission already exists
                existing = db_manager.execute_scalar(
                    "SELECT COUNT(*) FROM role_permissions WHERE role_id = ? AND page_name = 'ledger'",
                    role_id
                )

                if not existing:
                    db_manager.execute_update(
                        "INSERT INTO role_permissions (role_id, page_name, can_access) VALUES (?, ?, ?)",
                        (role_id, 'ledger', 1)
                    )
                    print(f"Added ledger permission for role ID {role_id}")

        except Exception as ex:
            print(f"Error ensuring ledger permission: {str(ex)}")

    @staticmethod
    def ensure_auxiliary_permission():
        """Ensure all roles have auxiliary permission"""
        try:
            # Get all roles
            roles = db_manager.execute_query("SELECT id FROM roles")

            # Add auxiliary permission for each role if it doesn't exist
            for role in roles:
                role_id = role[0]

                # Check if auxiliary permission already exists
                existing = db_manager.execute_scalar(
                    "SELECT COUNT(*) FROM role_permissions WHERE role_id = ? AND page_name = 'auxiliary'",
                    role_id
                )

                if not existing:
                    db_manager.execute_update(
                        "INSERT INTO role_permissions (role_id, page_name, can_access) VALUES (?, ?, ?)",
                        (role_id, 'auxiliary', 1)
                    )
                    print(f"Added auxiliary permission for role ID {role_id}")

        except Exception as ex:
            print(f"Error ensuring auxiliary permission: {str(ex)}")

    @staticmethod
    def ensure_accounting_tables():
       # \"\"\"Ensure both accounting_transactions and accounting_transaction_lines tables exist\"\"\"
        try:
            # Ensure accounting_transactions
            exists = db_manager.execute_scalar(
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'accounting_transactions'"
            )
            if not exists:
                sql = """
                CREATE TABLE accounting_transactions (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    reference_type VARCHAR(50),
                    reference_id VARCHAR(100),
                    description VARCHAR(500),
                    transaction_date DATETIME DEFAULT GETDATE(),
                    created_at DATETIME DEFAULT GETDATE()
                )
                """
                db_manager.execute_update(sql)
                print("accounting_transactions table created successfully")

            # Ensure accounting_transaction_lines
            lines_exists = db_manager.execute_scalar(
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'accounting_transaction_lines'"
            )
            if not lines_exists:
                sql_lines = """
                CREATE TABLE accounting_transaction_lines (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    jv_id INT NOT NULL,
                    account_number VARCHAR(20),
                    auxiliary_id VARCHAR(20) NOT NULL,
                    debit DECIMAL(18,2) DEFAULT 0,
                    credit DECIMAL(18,2) DEFAULT 0,
                    FOREIGN KEY (jv_id) REFERENCES accounting_transactions(id)
                )
                """
                db_manager.execute_update(sql_lines)
                print("accounting_transaction_lines table created successfully")

            # Ensure permissions
            roles = db_manager.execute_query("SELECT id FROM roles")
            for role in roles:
                role_id = role[0]
                for page in ['accounting-transactions']:
                    existing = db_manager.execute_scalar(
                        "SELECT COUNT(*) FROM role_permissions WHERE role_id = ? AND page_name = ?",
                        (role_id, page)
                    )
                    if not existing:
                        db_manager.execute_update(
                            "INSERT INTO role_permissions (role_id, page_name, can_access) VALUES (?, ?, 1)",
                            (role_id, page)
                        )
        except Exception as ex:
            print(f"Error ensuring accounting tables: {str(ex)}")
