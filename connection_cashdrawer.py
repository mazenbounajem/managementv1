from database_manager import db_manager
from datetime import datetime

class connection_cashdrawer:
    @staticmethod
    def get_cash_drawer_balance():
        try:
            sql = "SELECT TOP 1 current_balance FROM cash_drawer ORDER BY id DESC"
            result = db_manager.execute_scalar(sql)
            return float(result) if result is not None else 0.0
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
            now = datetime.now()

            # Insert operation
            insert_sql = """
            INSERT INTO cash_drawer_operations (operation_date, operation_type, amount, user_id, notes)
            VALUES (?, ?, ?, ?, ?)
            """
            params = (now, operation_type, amount, user_id, notes)
            db_manager.execute_update(insert_sql, params)

            # Ensure there is a cash_drawer row to update (so balance actually changes)
            drawer_id = db_manager.execute_scalar("SELECT TOP 1 id FROM cash_drawer ORDER BY id DESC")
            if drawer_id is None:
                db_manager.execute_update(
                    "INSERT INTO cash_drawer (current_balance, last_updated) VALUES (?, ?)",
                    (0.0, now)
                )
                drawer_id = db_manager.execute_scalar("SELECT TOP 1 id FROM cash_drawer ORDER BY id DESC")

            # Update cash drawer balance (update specific drawer row)
            if operation_type == 'In':
                update_sql = """
                    UPDATE cash_drawer
                    SET current_balance = current_balance + ?, last_updated = ?
                    WHERE id = ?
                """
            else:
                update_sql = """
                    UPDATE cash_drawer
                    SET current_balance = current_balance - ?, last_updated = ?
                    WHERE id = ?
                """

            update_params = (amount, now, drawer_id)
            db_manager.execute_update(update_sql, update_params)

            return True
        except Exception as ex:
            print(f"Error adding cash drawer operation: {str(ex)}")
            return False
