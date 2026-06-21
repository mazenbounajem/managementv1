"""
db_migrations_create_custom_reports.py

Migration to create the `custom_reports` table that stores user-defined
report definitions for the Report Designer.

A report definition is a JSON blob with the following shape:
    {
        "table": "sales",
        "columns": [{"name": "id", "alias": "ID", "format": "int"}, ...],
        "filters": [{"column": "sale_date", "op": "between", "value": ["2024-01-01", "2024-12-31"]}, ...],
        "sort":    [{"column": "sale_date", "direction": "DESC"}],
        "group_by": ["customer_id"],
        "row_limit": 1000,
        "options": {
            "show_totals": true,
            "orientation": "portrait"
        }
    }
"""
from database_manager import db_manager


def _table_exists(table: str) -> bool:
    sql = (
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = ?"
    )
    cnt = db_manager.execute_scalar(sql, (table,))
    return bool(cnt and int(cnt) > 0)


def _index_exists(table: str, index_name: str) -> bool:
    sql = (
        "SELECT COUNT(*) FROM sys.indexes "
        "WHERE name = ? AND object_id = OBJECT_ID(?)"
    )
    cnt = db_manager.execute_scalar(sql, (index_name, table))
    return bool(cnt and int(cnt) > 0)


def main():
    stmts = [
        """
        IF OBJECT_ID('custom_reports','U') IS NULL
        CREATE TABLE custom_reports (
            id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(200) NOT NULL,
            description NVARCHAR(500) NULL,
            base_table NVARCHAR(200) NOT NULL,
            definition NVARCHAR(MAX) NOT NULL,
            created_by NVARCHAR(200) NULL,
            created_at DATETIME DEFAULT GETDATE(),
            updated_at DATETIME DEFAULT GETDATE()
        );
        """
    ]

    for s in stmts:
        db_manager.execute_update(s)

    if _table_exists('custom_reports') and not _index_exists(
        'custom_reports', 'IX_custom_reports_name'
    ):
        db_manager.execute_update(
            "CREATE UNIQUE INDEX IX_custom_reports_name "
            "ON custom_reports(name);"
        )

    if _table_exists('custom_reports'):
        print("custom_reports_table_ready")
    else:
        print("custom_reports_table_missing")


if __name__ == "__main__":
    main()
