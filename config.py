"""
Configuration management for the application
"""
import os
from typing import Optional

class Config:
    """Application configuration class"""

    # Database Configuration
    DATABASE_HOST: str = os.getenv('DATABASE_HOST', 'localhost')
    DATABASE_NAME: str = os.getenv('DATABASE_NAME', 'pos_system')
    DATABASE_USER: str = os.getenv('DATABASE_USER', 'sa')
    DATABASE_PASSWORD: str = os.getenv('DATABASE_PASSWORD', '')
    DATABASE_DRIVER: str = os.getenv('DATABASE_DRIVER', 'ODBC Driver 17 for SQL Server')

    # Application Configuration
    APP_HOST: str = os.getenv('APP_HOST', '0.0.0.0')
    APP_PORT: int = int(os.getenv('APP_PORT', '8080'))
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

    # Security Configuration
    SESSION_TIMEOUT_MINUTES: int = int(os.getenv('SESSION_TIMEOUT_MINUTES', '30'))
    PASSWORD_MIN_LENGTH: int = int(os.getenv('PASSWORD_MIN_LENGTH', '8'))
    MAX_LOGIN_ATTEMPTS: int = int(os.getenv('MAX_LOGIN_ATTEMPTS', '5'))
    ACCOUNT_LOCKOUT_MINUTES: int = int(os.getenv('ACCOUNT_LOCKOUT_MINUTES', '15'))

    # Email Configuration (for future password reset)
    SMTP_SERVER: Optional[str] = os.getenv('SMTP_SERVER')
    SMTP_PORT: int = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USERNAME: Optional[str] = os.getenv('SMTP_USERNAME')
    SMTP_PASSWORD: Optional[str] = os.getenv('SMTP_PASSWORD')
    EMAIL_FROM: Optional[str] = os.getenv('EMAIL_FROM')

    # Logging Configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', 'app.log')
    AUDIT_LOG_FILE: str = os.getenv('AUDIT_LOG_FILE', 'audit.log')

    # File Upload Configuration
    UPLOAD_FOLDER: str = os.getenv('UPLOAD_FOLDER', 'uploads')
    MAX_FILE_SIZE: int = int(os.getenv('MAX_FILE_SIZE', '10485760'))  # 10MB

    @classmethod
    def get_database_connection_string(cls) -> str:
        """Generate database connection string"""
        return f"DRIVER={{{cls.DATABASE_DRIVER}}};SERVER={cls.DATABASE_HOST};DATABASE={cls.DATABASE_NAME};UID={cls.DATABASE_USER};PWD={cls.DATABASE_PASSWORD}"

    @classmethod
    def validate_config(cls) -> list[str]:
        """Validate configuration and return list of missing required settings"""
        missing = []

        if not cls.DATABASE_PASSWORD:
            missing.append('DATABASE_PASSWORD')

        if not cls.SECRET_KEY or cls.SECRET_KEY == 'your-secret-key-change-in-production':
            missing.append('SECRET_KEY')

        return missing

# Global configuration instance
config = Config()
