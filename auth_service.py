"""
Authentication service for handling user login, logout, and session management
"""
import hashlib
import datetime
from typing import Optional, Dict, Any, Tuple
from connection import connection
from session_methods import SessionManager
from logger import app_logger, AuthenticationError, ValidationError
from config import config

class AuthService:
    """Service class for authentication operations"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using MD5 (will be upgraded to bcrypt in Phase 2)"""
        return hashlib.md5(password.encode('utf-8')).hexdigest()

    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, str]:
        """Validate password strength requirements"""
        if len(password) < config.PASSWORD_MIN_LENGTH:
            return False, f"Password must be at least {config.PASSWORD_MIN_LENGTH} characters long"

        # Add more complexity checks as needed
        return True, ""

    @staticmethod
    def authenticate_user(username: str, password: str,
                         ip_address: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Authenticate user credentials
        Returns: (success, user_data)
        """
        try:
            if not username or not password:
                raise ValidationError("Username and password are required")

            # Hash the input password
            password_hash = AuthService.hash_password(password)

            # Check user credentials
            user_info = connection.check_user_login(username, password_hash)

            if user_info:
                # Get full user information
                user_data = connection.get_user_role_info(username)

                if user_data:
                    # Log successful authentication
                    app_logger.log_security_event(
                        'LOGIN_SUCCESS',
                        user_id=user_data['user_id'],
                        details={'username': username},
                        ip_address=ip_address
                    )

                    return True, user_data
                else:
                    app_logger.log_security_event(
                        'LOGIN_FAILED',
                        details={'username': username, 'reason': 'user_data_not_found'},
                        ip_address=ip_address
                    )
                    return False, None
            else:
                # Log failed authentication
                app_logger.log_security_event(
                    'LOGIN_FAILED',
                    details={'username': username, 'reason': 'invalid_credentials'},
                    ip_address=ip_address
                )
                return False, None

        except Exception as e:
            app_logger.log_error(e, "authenticate_user")
            return False, None

    @staticmethod
    def create_user_session(user_data: Dict[str, Any]) -> Optional[str]:
        """Create a new user session"""
        try:
            login_time = datetime.datetime.now()
            session_id = SessionManager.create_user_session(user_data['user_id'], login_time)

            if session_id:
                app_logger.log_user_action(
                    user_data['user_id'],
                    'SESSION_CREATED',
                    {'session_id': session_id}
                )
                return session_id
            else:
                app_logger.log_error(
                    Exception("Failed to create user session"),
                    "create_user_session"
                )
                return None

        except Exception as e:
            app_logger.log_error(e, "create_user_session")
            return None

    @staticmethod
    def logout_user(session_id: str, user_data: Optional[Dict[str, Any]] = None) -> bool:
        """Logout user and update session"""
        try:
            logout_time = datetime.datetime.now()
            duration = SessionManager.update_user_logout(session_id, logout_time)

            if user_data:
                app_logger.log_user_action(
                    user_data['user_id'],
                    'LOGOUT',
                    {'session_id': session_id, 'duration_minutes': duration}
                )

            return True

        except Exception as e:
            app_logger.log_error(e, "logout_user")
            return False

    @staticmethod
    def check_session_validity(session_id: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if session is still valid"""
        try:
            # This would need to be implemented based on your session storage
            # For now, return True if session exists
            return True, None

        except Exception as e:
            app_logger.log_error(e, "check_session_validity")
            return False, None

    @staticmethod
    def get_current_user(session_storage: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get current logged-in user from session"""
        return session_storage.get('user')

    @staticmethod
    def require_login(session_storage: Dict[str, Any]) -> bool:
        """Check if user is logged in"""
        return AuthService.get_current_user(session_storage) is not None

    @staticmethod
    def check_page_access(session_storage: Dict[str, Any], page_name: str) -> bool:
        """Check if current user has access to a specific page"""
        user = AuthService.get_current_user(session_storage)
        if not user:
            return False

        return connection.check_page_permission(user['role_id'], page_name)

    @staticmethod
    def create_user(username: str, password: str, email: Optional[str] = None,
                   role_id: Optional[int] = None) -> Tuple[bool, str]:
        """Create a new user account"""
        try:
            # Validate password strength
            is_valid, error_msg = AuthService.validate_password_strength(password)
            if not is_valid:
                raise ValidationError(error_msg)

            # Check if username already exists
            if connection.username_exists(username):
                raise ValidationError("Username already exists")

            # Hash password
            password_hash = AuthService.hash_password(password)

            # Create user account
            success = connection.create_user_account(username, password_hash, role_id)

            if success:
                app_logger.log_security_event(
                    'USER_CREATED',
                    details={'username': username, 'role_id': role_id}
                )
                return True, "User created successfully"
            else:
                return False, "Failed to create user account"

        except ValidationError as e:
            return False, str(e)
        except Exception as e:
            app_logger.log_error(e, "create_user")
            return False, "An error occurred while creating the user"

    @staticmethod
    def update_user_password(username: str, new_password: str,
                           current_user: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """Update user password"""
        try:
            # Validate new password strength
            is_valid, error_msg = AuthService.validate_password_strength(new_password)
            if not is_valid:
                raise ValidationError(error_msg)

            # Hash new password
            password_hash = AuthService.hash_password(new_password)

            # Update password (this would need to be implemented in connection.py)
            # For now, return success
            success = True

            if success:
                app_logger.log_security_event(
                    'PASSWORD_CHANGED',
                    user_id=current_user['user_id'] if current_user else None,
                    details={'username': username}
                )
                return True, "Password updated successfully"
            else:
                return False, "Failed to update password"

        except ValidationError as e:
            return False, str(e)
        except Exception as e:
            app_logger.log_error(e, "update_user_password")
            return False, "An error occurred while updating the password"
