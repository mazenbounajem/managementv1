"""
report_designer_service.py

Service layer for the user-driven Report Designer.

Responsibilities
----------------
* Curate the list of business tables users can build reports against.
* Read live column metadata for those tables (cached per session).
* Build a parameterised SELECT query from a user definition.
* Run the query safely and return rows as plain dicts.
* Persist / load / delete user-defined report definitions in
  the `custom_reports` table.
"""
from __future__ import annotations

import json
import re
import threading
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from database_manager import db_manager
from session_storage import session_storage


# ---------------------------------------------------------------------------
# Curated tables.  Each entry is a (key, label, table_name, description) tuple
# shown in the designer's data source dropdown.  Restricting the list keeps
# users away from internal / sensitive tables.
# ---------------------------------------------------------------------------
CURATED_TABLES: List[Dict[str, str]] = [
    {"key": "sales",         "label": "Sales",                  "table": "sales",         "description": "Customer sale invoices"},
    {"key": "sale_items",    "label": "Sales - Line Items",     "table": "sale_items",    "description": "Items inside each sale"},
    {"key": "sales_payment", "label": "Sales - Payments",       "table": "sales_payment", "description": "Payments received against sales"},
    {"key": "sales_returns", "label": "Sales Returns",          "table": "sales_returns", "description": "Returned sales invoices"},
    {"key": "sales_return_items", "label": "Sales Return Items", "table": "sales_return_items", "description": "Items inside each return"},
    {"key": "purchases",     "label": "Purchases",              "table": "purchases",     "description": "Supplier purchase invoices"},
    {"key": "purchase_items","label": "Purchases - Line Items", "table": "purchase_items","description": "Items inside each purchase"},
    {"key": "purchase_payment", "label": "Purchases - Payments", "table": "purchase_payment", "description": "Payments made against purchases"},
    {"key": "purchase_returns", "label": "Purchase Returns",     "table": "purchase_returns", "description": "Returned purchase invoices"},
    {"key": "purchase_return_items", "label": "Purchase Return Items", "table": "purchase_return_items", "description": "Items inside each return"},
    {"key": "products",      "label": "Products",               "table": "products",      "description": "Product master data"},
    {"key": "categories",    "label": "Categories",             "table": "categories",    "description": "Product categories"},
    {"key": "customers",     "label": "Customers",              "table": "customers",     "description": "Customer master data"},
    {"key": "suppliers",     "label": "Suppliers",              "table": "suppliers",     "description": "Supplier master data"},
    {"key": "expenses",      "label": "Expenses",               "table": "expenses",      "description": "Expense records"},
    {"key": "expense_types", "label": "Expense Types",          "table": "expense_types", "description": "Expense categories"},
    {"key": "stock_operations", "label": "Stock Operations",     "table": "stock_operations", "description": "Stock adjustments and transfers"},
    {"key": "stock_operation_items", "label": "Stock Operation Items", "table": "stock_operation_items", "description": "Line items in stock adjustments"},
    {"key": "employees",     "label": "Employees",              "table": "employees",     "description": "Employee records"},
    {"key": "appointments",  "label": "Appointments",           "table": "appointments",  "description": "Customer appointments"},
    {"key": "services",      "label": "Services",               "table": "services",      "description": "Service catalog"},
    {"key": "cash_drawer",   "label": "Cash Drawer",            "table": "cash_drawer",   "description": "Cash drawer balances"},
    {"key": "cash_drawer_operations", "label": "Cash Drawer Operations", "table": "cash_drawer_operations", "description": "Cash drawer movements"},
    {"key": "customer_payments", "label": "Customer Payments",   "table": "customer_payments", "description": "Customer payment records"},
    {"key": "customer_receipt",  "label": "Customer Receipts",   "table": "customer_receipt",  "description": "Customer receipt headers"},
    {"key": "supplier_payment",  "label": "Supplier Payments",   "table": "supplier_payment",  "description": "Supplier payment records"},
    {"key": "accounting_transactions",     "label": "Accounting - Transactions", "table": "accounting_transactions",     "description": "Journal voucher headers"},
    {"key": "accounting_transaction_lines", "label": "Accounting - Transaction Lines", "table": "accounting_transaction_lines", "description": "Journal voucher lines"},
    {"key": "Ledger",        "label": "Ledger Chart of Accounts", "table": "Ledger",        "description": "Chart of accounts"},
    {"key": "auxiliary",     "label": "Auxiliary Accounts",     "table": "auxiliary",     "description": "Auxiliary / sub-ledger accounts"},
]


# ---------------------------------------------------------------------------
# Per-request column cache so we don't hit INFORMATION_SCHEMA on every
# dropdown change.  The cache lives on the session storage proxy.
# ---------------------------------------------------------------------------
_COL_CACHE_KEY = "_rd_column_cache"


def _cache_get() -> Dict[str, List[Dict[str, str]]]:
    return session_storage.get(_COL_CACHE_KEY, {}) or {}


def _cache_set(cache: Dict[str, List[Dict[str, str]]]) -> None:
    session_storage[_COL_CACHE_KEY] = cache


def get_curated_tables() -> List[Dict[str, str]]:
    """Return the list of data sources the designer can build reports on."""
    return list(CURATED_TABLES)


def get_table_label(table_name: str) -> str:
    for entry in CURATED_TABLES:
        if entry["table"] == table_name:
            return entry["label"]
    return table_name


def get_columns(table_name: str, *, refresh: bool = False) -> List[Dict[str, str]]:
    """Return live column metadata for a table from INFORMATION_SCHEMA."""
    if not refresh:
        cached = _cache_get().get(table_name)
        if cached:
            return cached

    if not any(t["table"] == table_name for t in CURATED_TABLES):
        raise ValueError(f"Table '{table_name}' is not part of the curated list.")

    rows: List[Dict[str, str]] = []
    try:
        results = db_manager.execute_query(
            "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH "
            "FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = ? ORDER BY ORDINAL_POSITION",
            (table_name,),
        )
    except Exception as ex:
        raise RuntimeError(f"Could not read columns for {table_name}: {ex}") from ex

    for col_name, data_type, is_nullable, max_len in results:
        rows.append(
            {
                "name": col_name,
                "type": (data_type or "").lower(),
                "nullable": (is_nullable or "NO") == "YES",
                "max_length": str(max_len) if max_len is not None else "",
            }
        )

    cache = _cache_get()
    cache[table_name] = rows
    _cache_set(cache)
    return rows


# ---------------------------------------------------------------------------
# Type-aware filter rendering
# ---------------------------------------------------------------------------
NUMERIC_TYPES = {
    "int", "bigint", "smallint", "tinyint", "bit",
    "decimal", "numeric", "money", "smallmoney", "float", "real",
}
DATE_TYPES = {"date", "datetime", "datetime2", "smalldatetime", "datetimeoffset", "time", "timestamp"}


def _is_numeric(type_name: str) -> bool:
    return type_name.lower() in NUMERIC_TYPES


def _is_date(type_name: str) -> bool:
    return type_name.lower() in DATE_TYPES


def _is_text(type_name: str) -> bool:
    t = type_name.lower()
    return t.startswith(("char", "varchar", "nvarchar", "nchar", "text", "ntext"))


def _quote_param(value: Any) -> Any:
    """Convert a Python value to a pyodbc-friendly parameter."""
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, Decimal):
        return value
    return value


_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _safe_ident(name: str) -> str:
    if not _IDENTIFIER_RE.match(name or ""):
        raise ValueError(f"Invalid identifier: {name!r}")
    # SQL Server uses [] for delimited identifiers
    return f"[{name}]"


# ---------------------------------------------------------------------------
# Query builder
# ---------------------------------------------------------------------------
class QueryBuildError(ValueError):
    """Raised when a definition can't be turned into a safe query."""


def build_query(definition: Dict[str, Any]) -> Tuple[str, List[Any]]:
    """Turn a report definition into (sql, params).

    The definition is fully user-driven but limited to the curated table
    list and a whitelist of operators.  Every column / table reference is
    validated against `_IDENTIFIER_RE` before being quoted.
    """
    table_name = (definition.get("table") or "").strip()
    if not table_name:
        raise QueryBuildError("Pick a data source first.")
    if not any(t["table"] == table_name for t in CURATED_TABLES):
        raise QueryBuildError("That data source is not allowed.")

    columns = definition.get("columns") or []
    if not columns:
        raise QueryBuildError("Pick at least one column to display.")
    if len(columns) > 30:
        raise QueryBuildError("Too many columns (max 30).")

    select_parts: List[str] = []
    for col in columns:
        raw_name = (col.get("name") or "").strip()
        if not raw_name:
            raise QueryBuildError("A column is missing a name.")
        _safe_ident(raw_name)  # validate
        # Optional friendly alias
        alias = (col.get("alias") or "").strip()
        if alias:
            _safe_ident(alias)
            select_parts.append(f"{_safe_ident(raw_name)} AS {_safe_ident(alias)}")
        else:
            select_parts.append(_safe_ident(raw_name))

    sql = f"SELECT {', '.join(select_parts)} FROM {_safe_ident(table_name)}"

    params: List[Any] = []
    where_clauses: List[str] = []

    for f in definition.get("filters") or []:
        col = (f.get("column") or "").strip()
        op = (f.get("op") or "").strip().lower()
        value = f.get("value")
        if not col or not op:
            continue
        _safe_ident(col)

        if op == "isnull":
            where_clauses.append(f"{_safe_ident(col)} IS NULL")
        elif op == "isnotnull":
            where_clauses.append(f"{_safe_ident(col)} IS NOT NULL")
        elif op == "isempty":
            where_clauses.append(f"({_safe_ident(col)} IS NULL OR {_safe_ident(col)} = '')")
        elif op == "isnotempty":
            where_clauses.append(f"({_safe_ident(col)} IS NOT NULL AND {_safe_ident(col)} <> '')")
        elif op == "eq":
            where_clauses.append(f"{_safe_ident(col)} = ?")
            params.append(_quote_param(value))
        elif op == "neq":
            where_clauses.append(f"{_safe_ident(col)} <> ?")
            params.append(_quote_param(value))
        elif op == "gt":
            where_clauses.append(f"{_safe_ident(col)} > ?")
            params.append(_quote_param(value))
        elif op == "gte":
            where_clauses.append(f"{_safe_ident(col)} >= ?")
            params.append(_quote_param(value))
        elif op == "lt":
            where_clauses.append(f"{_safe_ident(col)} < ?")
            params.append(_quote_param(value))
        elif op == "lte":
            where_clauses.append(f"{_safe_ident(col)} <= ?")
            params.append(_quote_param(value))
        elif op == "contains":
            where_clauses.append(f"CAST({_safe_ident(col)} AS NVARCHAR(MAX)) LIKE ?")
            params.append(f"%{value}%")
        elif op == "startswith":
            where_clauses.append(f"CAST({_safe_ident(col)} AS NVARCHAR(MAX)) LIKE ?")
            params.append(f"{value}%")
        elif op == "endswith":
            where_clauses.append(f"CAST({_safe_ident(col)} AS NVARCHAR(MAX)) LIKE ?")
            params.append(f"%{value}")
        elif op == "in":
            if not isinstance(value, list) or not value:
                continue
            placeholders = ", ".join(["?"] * len(value))
            where_clauses.append(f"{_safe_ident(col)} IN ({placeholders})")
            for v in value:
                params.append(_quote_param(v))
        elif op == "between":
            if not isinstance(value, list) or len(value) != 2:
                continue
            where_clauses.append(f"{_safe_ident(col)} BETWEEN ? AND ?")
            params.append(_quote_param(value[0]))
            params.append(_quote_param(value[1]))
        else:
            raise QueryBuildError(f"Unknown filter operator: {op}")

    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    group_by_cols = []
    for g in definition.get("group_by") or []:
        name = (g or "").strip()
        if not name:
            continue
        _safe_ident(name)
        group_by_cols.append(_safe_ident(name))
    if group_by_cols:
        sql += " GROUP BY " + ", ".join(group_by_cols)

    order_clauses: List[str] = []
    for s in definition.get("sort") or []:
        name = (s.get("column") or "").strip()
        direction = (s.get("direction") or "ASC").strip().upper()
        if not name:
            continue
        if direction not in ("ASC", "DESC"):
            direction = "ASC"
        order_clauses.append(f"{_safe_ident(name)} {direction}")
    if order_clauses:
        sql += " ORDER BY " + ", ".join(order_clauses)

    row_limit = definition.get("row_limit")
    try:
        limit_n = int(row_limit) if row_limit not in (None, "", 0) else 0
    except (TypeError, ValueError):
        limit_n = 0
    # Cap at 10,000 to keep the app responsive.
    limit_n = max(0, min(limit_n, 10000))
    if limit_n > 0:
        # SQL Server 2012+ OFFSET/FETCH
        sql += f" OFFSET 0 ROWS FETCH NEXT {limit_n} ROWS ONLY"

    return sql, params


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------
def run_query(definition: Dict[str, Any]) -> Tuple[List[str], List[List[Any]]]:
    """Execute a definition and return (headers, rows) where headers is the
    list of column aliases the user picked (or raw column names)."""
    sql, params = build_query(definition)

    headers: List[str] = []
    raw_rows = db_manager.execute_query(sql, params) if params else db_manager.execute_query(sql)

    for col in definition.get("columns") or []:
        alias = (col.get("alias") or "").strip()
        name = (col.get("name") or "").strip()
        headers.append(alias or name)

    rows: List[List[Any]] = []
    for r in raw_rows:
        rows.append([_json_safe(v) for v in r])

    return headers, rows


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ")
    return value


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
class ReportDefinitionError(ValueError):
    pass


def _validate_definition(definition: Dict[str, Any]) -> None:
    if not isinstance(definition, dict):
        raise ReportDefinitionError("Definition must be a dict.")
    if not (definition.get("table") or "").strip():
        raise ReportDefinitionError("Definition is missing a data source.")
    if not definition.get("columns"):
        raise ReportDefinitionError("Definition must include at least one column.")
    # Try to compile it once to catch bad identifiers/operators early.
    build_query(definition)


def list_saved_reports() -> List[Dict[str, Any]]:
    """Return all saved custom reports (most recent first)."""
    try:
        rows = db_manager.execute_query(
            "SELECT id, name, description, base_table, definition, "
            "       created_by, created_at, updated_at "
            "FROM custom_reports ORDER BY updated_at DESC, id DESC"
        )
    except Exception as ex:
        raise RuntimeError(f"Could not load custom reports: {ex}") from ex

    out: List[Dict[str, Any]] = []
    for r in rows:
        rid, name, description, base_table, definition, created_by, created_at, updated_at = r
        try:
            defn = json.loads(definition) if definition else {}
        except Exception:
            defn = {}
        out.append(
            {
                "id": rid,
                "name": name,
                "description": description or "",
                "base_table": base_table,
                "definition": defn,
                "created_by": created_by or "",
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )
    return out


def save_report(
    name: str,
    description: str,
    definition: Dict[str, Any],
    *,
    report_id: Optional[int] = None,
) -> int:
    """Insert or update a custom report.  Returns the row id."""
    name = (name or "").strip()
    if not name:
        raise ReportDefinitionError("Report name is required.")
    if len(name) > 200:
        raise ReportDefinitionError("Report name is too long (max 200 chars).")
    if not isinstance(definition, dict):
        raise ReportDefinitionError("Definition is invalid.")
    _validate_definition(definition)

    owner = ""
    try:
        user = session_storage.get("user")
        if isinstance(user, dict):
            owner = user.get("username") or user.get("name") or ""
    except Exception:
        owner = ""

    blob = json.dumps(definition, ensure_ascii=False, default=str)
    base_table = (definition.get("table") or "").strip()

    if report_id:
        db_manager.execute_update(
            "UPDATE custom_reports "
            "SET name = ?, description = ?, base_table = ?, definition = ?, "
            "    created_by = COALESCE(NULLIF(created_by, ''), ?), "
            "    updated_at = GETDATE() "
            "WHERE id = ?",
            (name, description, base_table, blob, owner, report_id),
        )
        return int(report_id)

    try:
        db_manager.execute_update(
            "INSERT INTO custom_reports (name, description, base_table, definition, created_by) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, description, base_table, blob, owner),
        )
    except Exception as ex:
        # If it's a duplicate name, update instead.
        if "IX_custom_reports_name" in str(ex) or "duplicate" in str(ex).lower():
            db_manager.execute_update(
                "UPDATE custom_reports "
                "SET description = ?, base_table = ?, definition = ?, "
                "    created_by = COALESCE(NULLIF(created_by, ''), ?), "
                "    updated_at = GETDATE() "
                "WHERE name = ?",
                (description, base_table, blob, owner, name),
            )
            row = db_manager.execute_query(
                "SELECT id FROM custom_reports WHERE name = ?", (name,)
            )
            return int(row[0][0]) if row else 0
        raise

    row = db_manager.execute_query(
        "SELECT id FROM custom_reports WHERE name = ?", (name,)
    )
    return int(row[0][0]) if row else 0


def delete_report(report_id: int) -> None:
    db_manager.execute_update("DELETE FROM custom_reports WHERE id = ?", (int(report_id)))


# ---------------------------------------------------------------------------
# Ensure the table exists (call from page entrypoint)
# ---------------------------------------------------------------------------
_migration_lock = threading.Lock()
_migration_done = False


def ensure_table() -> None:
    """Create the `custom_reports` table on first use, idempotently."""
    global _migration_done
    with _migration_lock:
        if _migration_done:
            return
        try:
            exists = db_manager.execute_scalar(
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
                "WHERE TABLE_NAME = 'custom_reports'"
            )
            if not exists:
                # Inline migration (mirrors db_migrations_create_custom_reports.py)
                db_manager.execute_update(
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
                )
                db_manager.execute_update(
                    "CREATE UNIQUE INDEX IX_custom_reports_name ON custom_reports(name);"
                )
            _migration_done = True
        except Exception as ex:
            print(f"[report_designer] ensure_table error: {ex}")
