"""
Centralized logging and error handling for the application
"""
import logging
import logging.handlers
from datetime import datetime
from typing import Optional, Any, Dict
from functools import wraps
import traceback
from config import config

class AppLogger:
    """Centralized logging system for the application"""

    def __init__(self):
        self._setup_main_logger()
        self._setup_audit_logger()

    def _setup_main_logger(self):
        """Setup main application logger"""
        self.logger = logging.getLogger('pos_system')
        self.logger.setLevel(getattr(logging, config.LOG_LEVEL.upper()))

        # Remove existing handlers
        self.logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, config.LOG_LEVEL.upper()))
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            config.LOG_FILE,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

    def _setup_audit_logger(self):
        """Setup audit logger for security events"""
        self.audit_logger = logging.getLogger('audit')
        self.audit_logger.setLevel(logging.INFO)

        # Remove existing handlers
        self.audit_logger.handlers.clear()

        # Audit file handler
        audit_handler = logging.FileHandler(config.AUDIT_LOG_FILE)
        audit_handler.setLevel(logging.INFO)
        audit_formatter = logging.Formatter(
            '%(asctime)s - AUDIT - %(message)s'
        )
        audit_handler.setFormatter(audit_formatter)
        self.audit_logger.addHandler(audit_handler)

    def log_user_action(self, user_id: int, action: str, details: Optional[Dict[str, Any]] = None,
                       ip_address: Optional[str] = None):
        """Log user actions for audit purposes"""
        message = f"USER_ACTION: user_id={user_id}, action={action}"
        if details:
            message += f", details={details}"
        if ip_address:
            message += f", ip={ip_address}"

        self.audit_logger.info(message)

    def log_security_event(self, event_type: str, user_id: Optional[int] = None,
                          details: Optional[Dict[str, Any]] = None,
                          ip_address: Optional[str] = None):
        """Log security-related events"""
        message = f"SECURITY: event={event_type}"
        if user_id:
            message += f", user_id={user_id}"
        if details:
            message += f", details={details}"
        if ip_address:
            message += f", ip={ip_address}"

        self.audit_logger.warning(message)
        self.logger.warning(message)

    def log_error(self, error: Exception, context: Optional[str] = None,
                  user_id: Optional[int] = None):
        """Log application errors with full context"""
        error_details = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc()
        }

        if context:
            error_details['context'] = context
        if user_id:
            error_details['user_id'] = user_id

        self.logger.error(f"Application Error: {error_details}")

    def get_logger(self):
        """Get the main application logger"""
        return self.logger

    def get_audit_logger(self):
        """Get the audit logger"""
        return self.audit_logger

# Global logger instance
app_logger = AppLogger()

def log_function_call(func):
    """Decorator to log function calls"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        app_logger.logger.debug(f"Calling function: {func_name}")

        try:
            result = func(*args, **kwargs)
            app_logger.logger.debug(f"Function {func_name} completed successfully")
            return result
        except Exception as e:
            app_logger.log_error(e, f"Function {func_name} failed")
            raise

    return wrapper

def handle_errors(func):
    """Decorator to handle and log errors gracefully"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            app_logger.log_error(e, f"Error in {func.__name__}")
            # Return a user-friendly error message
            return {
                'success': False,
                'error': 'An unexpected error occurred. Please try again or contact support.',
                'details': str(e) if config.DEBUG else None
            }

    return wrapper

class AppException(Exception):
    """Base exception class for application-specific errors"""

    def __init__(self, message: str, error_code: Optional[str] = None,
                 user_message: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code
        self.user_message = user_message or message

class AuthenticationError(AppException):
    """Exception for authentication-related errors"""
    pass

class AuthorizationError(AppException):
    """Exception for authorization-related errors"""
    pass

class ValidationError(AppException):
    """Exception for validation-related errors"""
    pass

class DatabaseError(AppException):
    """Exception for database-related errors"""
    pass
