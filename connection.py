from database_manager import db_manager

class connection:
    """Refactored connection class using centralized database management"""
    
    @staticmethod
    def contogetrows(sql='', data=[]):
        """Get rows from database"""
        try:
            results = db_manager.execute_query(sql)
            data.extend(results)
        except Exception as ex:
            print(f"Error getting rows: {str(ex)}")
    
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
                    role VARCHAR(50)
                )
                """
                db_manager.execute_update(create_table_sql)
        except Exception as ex:
            print(f"Error creating users table: {str(ex)}")
    
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
    def contogetsupplier(sql='', data=[]):
        """Get rows from database"""
        try:
            results = db_manager.execute_query(sql)
            # Convert each row to a dictionary
            data.extend([dict(row) for row in results])
        except Exception as ex:
            print(f"Error getting rows: {str(ex)}")
        