from connection import connection
from database_manager import db_manager


def ensure_report_scope_tables():
    """
    Create minimal DB tables required to audit/report-scope accounting reports.

    Tables:
      - role_report_scope: controls which auxiliaries are visible for each audience.
      - report_audit_log: immutable log of report generation requests (who/what/when/filters).
    """
    # role_report_scope
    db_manager.execute_update("""
    IF OBJECT_ID('role_report_scope', 'U') IS NULL
    BEGIN
        CREATE TABLE role_report_scope (
            id INT IDENTITY(1,1) PRIMARY KEY,
            role_id INT NOT NULL,
            audience_key VARCHAR(50) NOT NULL,
            allowed_aux_prefixes NVARCHAR(500) NULL,
            allowed_ledger_root_prefixes NVARCHAR(200) NULL,
            created_at DATETIME DEFAULT GETDATE(),
            updated_at DATETIME DEFAULT GETDATE(),
            CONSTRAINT FK_role_report_scope_role FOREIGN KEY (role_id) REFERENCES roles(id),
            CONSTRAINT UQ_role_audience UNIQUE(role_id, audience_key)
        );
    END
    """)

    # report_audit_log
    db_manager.execute_update("""
    IF OBJECT_ID('report_audit_log', 'U') IS NULL
    BEGIN
        CREATE TABLE report_audit_log (
            id INT IDENTITY(1,1) PRIMARY KEY,
            user_id INT NULL,
            role_id INT NULL,
            role_name VARCHAR(100) NULL,
            audience_key VARCHAR(50) NOT NULL,
            report_key VARCHAR(100) NOT NULL,
            from_date DATE NULL,
            to_date DATE NULL,
            auxiliary_id VARCHAR(50) NULL,
            ledger_root_prefix VARCHAR(50) NULL,
            requested_at DATETIME DEFAULT GETDATE(),
            status VARCHAR(20) NOT NULL DEFAULT 'SUCCESS',
            error_message NVARCHAR(1000) NULL,
            filters_json NVARCHAR(2000) NULL
        );
    END
    """)

    return True
