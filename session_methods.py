from database_manager import db_manager
from connection import connection

class SessionManager:
    """Class to manage user session tracking functionality"""

    @staticmethod
    def create_user_session(user_id, login_time):
        """Create a new user session entry when user logs in"""
        try:
            sql = """
            INSERT INTO user_sessions (user_id, login_date, login_time)
            VALUES (?, CONVERT(DATE, ?), ?)
            """
            values = (user_id, login_time, login_time)
            connection.insertingtodatabase(sql, values)

            # Get the session ID of the newly created session
            session_id = connection.getrow(
                "SELECT MAX(id) FROM user_sessions WHERE user_id = ?",
                user_id
            )
            return session_id[0] if session_id else None
        except Exception as ex:
            print(f"Error creating user session: {str(ex)}")
            return None

    @staticmethod
    def update_user_logout(session_id, logout_time):
        """Update user session with logout time and calculate duration"""
        try:
            # Get login time for duration calculation
            login_data = connection.getrow(
                "SELECT login_time FROM user_sessions WHERE id = ?",
                session_id
            )

            if login_data:
                login_time = login_data[0]
                # Calculate duration in minutes
                duration_minutes = int((logout_time - login_time).total_seconds() / 60)

                sql = """
                UPDATE user_sessions
                SET logout_date = CONVERT(DATE, ?),
                    logout_time = ?,
                    session_duration_minutes = ?
                WHERE id = ?
                """
                values = (logout_time, logout_time, duration_minutes, session_id)
                connection.insertingtodatabase(sql, values)
                return duration_minutes
            return 0
        except Exception as ex:
            print(f"Error updating user logout: {str(ex)}")
            return 0

    @staticmethod
    def get_user_sessions(user_id, limit=10):
        """Get recent user sessions for a specific user"""
        try:
            sql = """
            SELECT id, login_date, login_time, logout_date, logout_time, session_duration_minutes
            FROM user_sessions
            WHERE user_id = ?
            ORDER BY login_time DESC
            """
            if limit:
                sql += f" OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"

            results = db_manager.execute_query(sql, user_id)
            return results
        except Exception as ex:
            print(f"Error getting user sessions: {str(ex)}")
            return []

    @staticmethod
    def get_current_session_duration(user_id):
        """Get the duration of the current active session"""
        try:
            sql = """
            SELECT DATEDIFF(MINUTE, login_time, GETDATE())
            FROM user_sessions
            WHERE user_id = ? AND logout_time IS NULL
            ORDER BY login_time DESC
            """
            result = db_manager.execute_scalar(sql, user_id)
            return result if result else 0
        except Exception as ex:
            print(f"Error getting current session duration: {str(ex)}")
            return 0
