from database_manager import db_manager
from datetime import datetime

class connection_cashdrawer:
    @staticmethod
    def get_cash_drawer_balance():
        try:
            sql = "SELECT current_balance FROM cash_drawer"
            result = db_manager.execute_scalar(sql)
            return float(result) if result else 0.0
        except Exception as ex:
            print(f"Error getting cash drawer balance: {str(ex)}")
            return 0.0

    @staticmethod
    def get_cash_drawer_history():
        try:
            sql = """
            SELECT cdo.id, cdo.operation_date, cdo.operation_type, cdo.amount, u.username as user_name
            FROM cash_drawer_operations cdo
            LEFT JOIN users u ON cdo.user_id = u.id
            ORDER BY cdo.operation_date DESC
            """
            results = db_manager.execute_query(sql)
            history = []
            for row in results:
                history.append({
                    'id': row[0],
                    'operation_date': row[1],
                    'operation_type': row[2],
                    'amount': row[3],
                    'user_name': row[4] if row[4] else 'Unknown'
                })
            return history
        except Exception as ex:
            print(f"Error getting cash drawer history: {str(ex)}")
            return []

    @staticmethod
    def add_cash_drawer_operation(amount, operation_type, user_id, notes=None):
        try:
            # Insert operation
            insert_sql = """
            INSERT INTO cash_drawer_operations (operation_date, operation_type, amount, user_id, notes)
            VALUES (?, ?, ?, ?, ?)
            """
            params = (datetime.now(), operation_type, amount, user_id, notes)
            db_manager.execute_update(insert_sql, params)

            # Update cash drawer balance
            if operation_type == 'In':
                update_sql = "UPDATE cash_drawer SET current_balance = current_balance + ?, last_updated = ?"
            else:
                update_sql = "UPDATE cash_drawer SET current_balance = current_balance - ?, last_updated = ?"
            update_params = (amount, datetime.now())
            db_manager.execute_update(update_sql, update_params)

            return True
        except Exception as ex:
            print(f"Error adding cash drawer operation: {str(ex)}")
            return False
