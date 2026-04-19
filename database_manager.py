import pyodbc
import logging
from contextlib import contextmanager

class DatabaseManager:
    """Centralized database connection manager"""
    
    # Configuration - change these values to switch databases
    CONNECTION_CONFIG = {
        "driver": "SQL Server Native Client 11.0",
        "server": "DESKTOP-Q7U1STD\SQLEXPRESS01",
        "database": "POSDB",
        "trusted_connection": "yes"
    }
    
    def __init__(self):
        self.connection_string = self._build_connection_string()
        
    def _build_connection_string(self):
        """Build connection string from configuration"""
        return (
            f"Driver={{{self.CONNECTION_CONFIG['driver']}}};"
            f"Server={self.CONNECTION_CONFIG['server']};"
            f"Database={self.CONNECTION_CONFIG['database']};"
            f"Trusted_Connection={self.CONNECTION_CONFIG['trusted_connection']};"
        )
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        connection = None
        try:
            connection = pyodbc.connect(self.connection_string)
            yield connection
        except Exception as e:
            logging.error(f"Database connection error: {str(e)}")
            raise
        finally:
            if connection:
                connection.close()
    
    def execute_query(self, sql, params=None):
        """Execute SELECT query and return results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            return cursor.fetchall()
    
    def execute_update(self, sql, params=None):
        """Execute INSERT/UPDATE/DELETE queries"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            conn.commit()
            return cursor.rowcount
    
    def execute_scalar(self, sql, params=None):
        """Execute query and return single value"""
        results = self.execute_query(sql, params)
        return results[0][0] if results else None

# Create global instance
db_manager = DatabaseManager()
