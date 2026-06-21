from database_manager import db_manager


def column_exists(table: str, column: str) -> bool:
    sql = """
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME = ? AND COLUMN_NAME = ?
    """
    cnt = db_manager.execute_scalar(sql, (table, column))
    return bool(cnt and int(cnt) > 0)


def table_exists(table: str) -> bool:
    sql = """
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_NAME = ?
    """
    cnt = db_manager.execute_scalar(sql, (table,))
    return bool(cnt and int(cnt) > 0)


def add_column_if_missing(table: str, column: str, ddl: str) -> None:
    if not table_exists(table):
        print(f"[skip] table not found: {table}")
        return
    if column_exists(table, column):
        print(f"[ok] {table}.{column} already exists")
        return
    alter_sql = f"ALTER TABLE {table} ADD {ddl}"
    print(f"[add] {table}.{column} -> {ddl}")
    db_manager.execute_update(alter_sql)


def main():
    # sale_items
    add_column_if_missing(
        "sale_items",
        "currency_id",
        "currency_id INT NULL"
    )
    add_column_if_missing(
        "sale_items",
        "fx_rate_used",
        "fx_rate_used DECIMAL(18,6) NULL"
    )
    add_column_if_missing(
        "sale_items",
        "unit_price_usd",
        "unit_price_usd DECIMAL(18,6) NULL"
    )
    add_column_if_missing(
        "sale_items",
        "profit_usd",
        "profit_usd DECIMAL(18,6) NULL"
    )

    # purchase_items
    add_column_if_missing(
        "purchase_items",
        "currency_id",
        "currency_id INT NULL"
    )
    add_column_if_missing(
        "purchase_items",
        "fx_rate_used",
        "fx_rate_used DECIMAL(18,6) NULL"
    )
    add_column_if_missing(
        "purchase_items",
        "unit_cost_usd",
        "unit_cost_usd DECIMAL(18,6) NULL"
    )
    add_column_if_missing(
        "purchase_items",
        "profit_usd",
        "profit_usd DECIMAL(18,6) NULL"
    )

    # price_cost_date_history
    add_column_if_missing(
        "price_cost_date_history",
        "currency_id",
        "currency_id INT NULL"
    )

    # suppliers
    add_column_if_missing(
        "suppliers",
        "balance_ll",
        "balance_ll DECIMAL(18,6) NULL"
    )

    print("Currency migration completed.")


if __name__ == "__main__":
    main()
