from io import BytesIO
import csv
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfgen import canvas
from datetime import datetime
from connection import connection


class Reports:

    @staticmethod
    def fetch_sales_by_item(from_date=None, to_date=None):
        """Fetch sales grouped by product/item with revenue, cost, and profit"""
        headers = ['product_name', 'barcode', 'total_qty_sold', 'total_revenue', 'total_cost', 'total_profit', 'profit_margin_pct']
        data = []
        sql = """
            SELECT
                p.product_name,
                p.barcode,
                SUM(si.quantity) as total_qty_sold,
                SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0)) as total_revenue,
                SUM(si.quantity * ISNULL(p.cost_price, 0)) as total_cost,
                SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0))
                    - SUM(si.quantity * ISNULL(p.cost_price, 0)) as total_profit,
                CASE
                    WHEN SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0)) > 0
                    THEN ROUND(
                        (SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0))
                         - SUM(si.quantity * ISNULL(p.cost_price, 0)))
                        / SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0)) * 100, 2)
                    ELSE 0
                END as profit_margin_pct
            FROM sale_items si
            JOIN products p ON si.product_id = p.id
            JOIN sales s ON si.sales_id = s.id
            WHERE 1=1
        """
        params = []
        if from_date and to_date:
            sql += " AND s.sale_date BETWEEN ? AND ?"
            params.extend([from_date, to_date])
        elif from_date:
            sql += " AND s.sale_date >= ?"
            params.append(from_date)
        elif to_date:
            sql += " AND s.sale_date <= ?"
            params.append(to_date)
        sql += " GROUP BY p.product_name, p.barcode ORDER BY total_revenue DESC"
        connection.contogetrows_with_params(sql, data, params)
        return [dict(zip(headers, row)) for row in data]

    @staticmethod
    def fetch_profit_by_day(from_date=None, to_date=None):
        """Fetch profit aggregated by day"""
        headers = ['sale_day', 'total_revenue', 'total_cost', 'total_profit', 'total_orders']
        data = []
        sql = """
            SELECT
                CAST(s.sale_date AS DATE) as sale_day,
                SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0)) as total_revenue,
                SUM(si.quantity * ISNULL(p.cost_price, 0)) as total_cost,
                SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0))
                    - SUM(si.quantity * ISNULL(p.cost_price, 0)) as total_profit,
                COUNT(DISTINCT s.id) as total_orders
            FROM sale_items si
            JOIN products p ON si.product_id = p.id
            JOIN sales s ON si.sales_id = s.id
            WHERE 1=1
        """
        params = []
        if from_date and to_date:
            sql += " AND s.sale_date BETWEEN ? AND ?"
            params.extend([from_date, to_date])
        elif from_date:
            sql += " AND s.sale_date >= ?"
            params.append(from_date)
        sql += " GROUP BY CAST(s.sale_date AS DATE) ORDER BY sale_day DESC"
        connection.contogetrows_with_params(sql, data, params)
        return [dict(zip(headers, row)) for row in data]

    @staticmethod
    def fetch_profit_by_week(from_date=None, to_date=None):
        """Fetch profit aggregated by week"""
        headers = ['year', 'week_number', 'week_start', 'total_revenue', 'total_cost', 'total_profit', 'total_orders']
        data = []
        sql = """
            SELECT
                DATEPART(YEAR, s.sale_date) as year,
                DATEPART(WEEK, s.sale_date) as week_number,
                CAST(DATEADD(DAY, 1 - DATEPART(WEEKDAY, s.sale_date), CAST(s.sale_date AS DATE)) AS DATE) as week_start,
                SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0)) as total_revenue,
                SUM(si.quantity * ISNULL(p.cost_price, 0)) as total_cost,
                SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0))
                    - SUM(si.quantity * ISNULL(p.cost_price, 0)) as total_profit,
                COUNT(DISTINCT s.id) as total_orders
            FROM sale_items si
            JOIN products p ON si.product_id = p.id
            JOIN sales s ON si.sales_id = s.id
            WHERE 1=1
        """
        params = []
        if from_date and to_date:
            sql += " AND s.sale_date BETWEEN ? AND ?"
            params.extend([from_date, to_date])
        elif from_date:
            sql += " AND s.sale_date >= ?"
            params.append(from_date)
        sql += " GROUP BY DATEPART(YEAR, s.sale_date), DATEPART(WEEK, s.sale_date) ORDER BY year DESC, week_number DESC"
        connection.contogetrows_with_params(sql, data, params)
        return [dict(zip(headers, row)) for row in data]

    @staticmethod
    def fetch_profit_by_month(from_date=None, to_date=None):
        """Fetch profit aggregated by month"""
        headers = ['year', 'month_number', 'month_name', 'total_revenue', 'total_cost', 'total_profit', 'total_orders']
        data = []
        sql = """
            SELECT
                DATEPART(YEAR, s.sale_date) as year,
                DATEPART(MONTH, s.sale_date) as month_number,
                FORMAT(s.sale_date, 'MMMM') as month_name,
                SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0)) as total_revenue,
                SUM(si.quantity * ISNULL(p.cost_price, 0)) as total_cost,
                SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0))
                    - SUM(si.quantity * ISNULL(p.cost_price, 0)) as total_profit,
                COUNT(DISTINCT s.id) as total_orders
            FROM sale_items si
            JOIN products p ON si.product_id = p.id
            JOIN sales s ON si.sales_id = s.id
            WHERE 1=1
        """
        params = []
        if from_date and to_date:
            sql += " AND s.sale_date BETWEEN ? AND ?"
            params.extend([from_date, to_date])
        elif from_date:
            sql += " AND s.sale_date >= ?"
            params.append(from_date)
        sql += " GROUP BY DATEPART(YEAR, s.sale_date), DATEPART(MONTH, s.sale_date) ORDER BY year DESC, month_number DESC"
        connection.contogetrows_with_params(sql, data, params)
        return [dict(zip(headers, row)) for row in data]

    @staticmethod
    def fetch_profit_by_year():
        """Fetch profit aggregated by year"""
        headers = ['year', 'total_revenue', 'total_cost', 'total_profit', 'total_orders', 'profit_margin_pct']
        data = []
        sql = """
            SELECT
                DATEPART(YEAR, s.sale_date) as year,
                SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0)) as total_revenue,
                SUM(si.quantity * ISNULL(p.cost_price, 0)) as total_cost,
                SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0))
                    - SUM(si.quantity * ISNULL(p.cost_price, 0)) as total_profit,
                COUNT(DISTINCT s.id) as total_orders,
                CASE
                    WHEN SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0)) > 0
                    THEN ROUND(
                        (SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0))
                         - SUM(si.quantity * ISNULL(p.cost_price, 0)))
                        / SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0)) * 100, 2)
                    ELSE 0
                END as profit_margin_pct
            FROM sale_items si
            JOIN products p ON si.product_id = p.id
            JOIN sales s ON si.sales_id = s.id
            GROUP BY DATEPART(YEAR, s.sale_date)
            ORDER BY year DESC
        """
        connection.contogetrows(sql, data)
        return [dict(zip(headers, row)) for row in data]

    @staticmethod
    def fetch_most_profitable_by_amount(from_date=None, to_date=None, limit=20):
        """Fetch most profitable items ranked by absolute profit amount"""
        headers = ['rank', 'product_name', 'barcode', 'total_qty_sold', 'total_revenue', 'total_cost', 'total_profit']
        data = []
        sql = f"""
            WITH RankedProfits AS (
                SELECT 
                    SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0))
                        - SUM(si.quantity * ISNULL(p.cost_price, 0)) as total_profit,
                    p.product_name,
                    p.barcode,
                    SUM(si.quantity) as total_qty_sold,
                    SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0)) as total_revenue,
                    SUM(si.quantity * ISNULL(p.cost_price, 0)) as total_cost
                FROM sale_items si
                JOIN products p ON si.product_id = p.id
                JOIN sales s ON si.sales_id = s.id
                WHERE 1=1
        """
        params = []
        if from_date and to_date:
            sql += " AND s.sale_date BETWEEN ? AND ?"
            params.extend([from_date, to_date])
        sql += """
                GROUP BY p.product_name, p.barcode
            )
            SELECT TOP {limit}
                ROW_NUMBER() OVER (ORDER BY total_profit DESC) as rank,
                product_name, barcode, total_qty_sold, total_revenue, total_cost, total_profit
            FROM RankedProfits
            ORDER BY total_profit DESC
        """
        connection.contogetrows_with_params(sql, data, params)
        return [dict(zip(headers, row)) for row in data]

    @staticmethod
    def fetch_most_profitable_by_percentage(from_date=None, to_date=None, limit=20):
        """Fetch most profitable items ranked by profit margin percentage"""
        headers = ['rank', 'product_name', 'barcode', 'total_qty_sold', 'total_revenue', 'total_cost', 'total_profit', 'profit_margin_pct']
        data = []
        sql = f"""
            SELECT TOP {limit}
                ROW_NUMBER() OVER (ORDER BY
                    CASE
                        WHEN SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0)) > 0
                        THEN (SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0))
                              - SUM(si.quantity * ISNULL(p.cost_price, 0)))
                             / SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0)) * 100
                        ELSE 0
                    END DESC) as rank,
                p.product_name,
                p.barcode,
                SUM(si.quantity) as total_qty_sold,
                SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0)) as total_revenue,
                SUM(si.quantity * ISNULL(p.cost_price, 0)) as total_cost,
                SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0))
                    - SUM(si.quantity * ISNULL(p.cost_price, 0)) as total_profit,
                CASE
                    WHEN SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0)) > 0
                    THEN ROUND(
                        (SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0))
                         - SUM(si.quantity * ISNULL(p.cost_price, 0)))
                        / SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0)) * 100, 2)
                    ELSE 0
                END as profit_margin_pct
            FROM sale_items si
            JOIN products p ON si.product_id = p.id
            JOIN sales s ON si.sales_id = s.id
            WHERE 1=1
        """
        params = []
        if from_date and to_date:
            sql += " AND s.sale_date BETWEEN ? AND ?"
            params.extend([from_date, to_date])
        sql += """
            GROUP BY p.product_name, p.barcode
            ORDER BY profit_margin_pct DESC
        """
        connection.contogetrows_with_params(sql, data, params)
        return [dict(zip(headers, row)) for row in data]

    @staticmethod
    def fetch_fast_moving_items(from_date=None, to_date=None, limit=20):
        """Fetch fast moving items - highest quantity sold"""
        headers = ['rank', 'product_name', 'barcode', 'total_qty_sold', 'total_revenue', 'num_transactions', 'last_sale_date']
        data = []
        sql = f"""
            SELECT TOP {limit}
                ROW_NUMBER() OVER (ORDER BY SUM(si.quantity) DESC) as rank,
                p.product_name,
                p.barcode,
                SUM(si.quantity) as total_qty_sold,
                SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0)) as total_revenue,
                COUNT(DISTINCT s.id) as num_transactions,
                MAX(s.sale_date) as last_sale_date
            FROM sale_items si
            JOIN products p ON si.product_id = p.id
            JOIN sales s ON si.sales_id = s.id
            WHERE 1=1
        """
        params = []
        if from_date and to_date:
            sql += " AND s.sale_date BETWEEN ? AND ?"
            params.extend([from_date, to_date])
        elif from_date:
            sql += " AND s.sale_date >= ?"
            params.append(from_date)
        sql += " GROUP BY p.product_name, p.barcode ORDER BY total_qty_sold DESC"
        connection.contogetrows_with_params(sql, data, params)
        return [dict(zip(headers, row)) for row in data]

    @staticmethod
    def fetch_slow_moving_items(from_date=None, to_date=None, limit=20):
        """Fetch slow moving items - lowest quantity sold (but at least 1 sale)"""
        headers = ['rank', 'product_name', 'barcode', 'total_qty_sold', 'total_revenue', 'num_transactions', 'last_sale_date']
        data = []
        sql = f"""
            SELECT TOP {limit}
                ROW_NUMBER() OVER (ORDER BY SUM(si.quantity) ASC) as rank,
                p.product_name,
                p.barcode,
                SUM(si.quantity) as total_qty_sold,
                SUM(si.quantity * si.unit_price * (1 - ISNULL(si.discount, 0) / 100.0)) as total_revenue,
                COUNT(DISTINCT s.id) as num_transactions,
                MAX(s.sale_date) as last_sale_date
            FROM sale_items si
            JOIN products p ON si.product_id = p.id
            JOIN sales s ON si.sales_id = s.id
            WHERE 1=1
        """
        params = []
        if from_date and to_date:
            sql += " AND s.sale_date BETWEEN ? AND ?"
            params.extend([from_date, to_date])
        elif from_date:
            sql += " AND s.sale_date >= ?"
            params.append(from_date)
        sql += " GROUP BY p.product_name, p.barcode HAVING SUM(si.quantity) > 0 ORDER BY total_qty_sold ASC"
        connection.contogetrows_with_params(sql, data, params)
        return [dict(zip(headers, row)) for row in data]


    @staticmethod
    def fetch_expenses(from_date=None, to_date=None):
        """Fetch expenses with optional date filtering"""
        headers = []
        data = []
        
        # Get headers dynamically
        connection.contogetheaders("SELECT * FROM expenses WHERE 1=0", headers)
        
        # Build query with date filtering
        query = "SELECT * FROM expenses"
        params = []
        if from_date and to_date:
            query += " WHERE expense_date BETWEEN ? AND ?"
            params = [from_date, to_date]
        elif from_date:
            query += " WHERE expense_date >= ?"
            params = [from_date]
        elif to_date:
            query += " WHERE expense_date <= ?"
            params = [to_date]
            
        # Get rows
        connection.contogetrows_with_params(query, data, params)
        
        # Convert to list of dicts with column names
        return [dict(zip(headers, row)) for row in data]

    @staticmethod
    def fetch_sales(from_date=None, to_date=None):
        """Fetch sales with optional date filtering"""
        headers = []
        data = []

        # Get headers dynamically from the joined query
        connection.contogetheaders("SELECT s.*, c.customer_name FROM sales s LEFT JOIN customers c ON s.customer_id = c.id WHERE 1=0", headers)

        # Build query with date filtering
        query = "SELECT s.*, c.customer_name FROM sales s LEFT JOIN customers c ON s.customer_id = c.id"
        params = []
        if from_date and to_date:
            query += " WHERE s.sale_date BETWEEN ? AND ?"
            params = [from_date, to_date]
        elif from_date:
            query += " WHERE s.sale_date >= ?"
            params = [from_date]
        elif to_date:
            query += " WHERE s.sale_date <= ?"
            params = [to_date]

        # Get rows
        connection.contogetrows_with_params(query, data, params)

        # Convert to list of dicts with column names
        return [dict(zip(headers, row)) for row in data]

    @staticmethod
    def fetch_purchases(from_date=None, to_date=None):
        """Fetch purchases with optional date filtering"""
        headers = []
        data = []

        # Get headers dynamically from the joined query
        connection.contogetheaders("SELECT p.*, s.name as supplier_name FROM purchases p LEFT JOIN suppliers s ON p.supplier_id = s.id WHERE 1=0", headers)

        # Build query with date filtering
        query = "SELECT p.*, s.name as supplier_name FROM purchases p LEFT JOIN suppliers s ON p.supplier_id = s.id"
        params = []
        if from_date and to_date:
            query += " WHERE p.purchase_date BETWEEN ? AND ?"
            params = [from_date, to_date]
        elif from_date:
            query += " WHERE p.purchase_date >= ?"
            params = [from_date]
        elif to_date:
            query += " WHERE p.purchase_date <= ?"
            params = [to_date]

        # Get rows
        connection.contogetrows_with_params(query, data, params)

        # Convert to list of dicts with column names
        return [dict(zip(headers, row)) for row in data]

    @staticmethod
    def fetch_stock():
        """Fetch stock data from products table"""
        headers = []
        data = []

        # Get headers dynamically from the joined query
        connection.contogetheaders("SELECT p.*, cat.category_name, sup.name as supplier_name FROM products p LEFT JOIN categories cat ON p.category_id = cat.id LEFT JOIN suppliers sup ON p.supplier_id = sup.id WHERE 1=0", headers)

        # Get rows with joined data
        connection.contogetrows("SELECT p.*, cat.category_name, sup.name as supplier_name FROM products p LEFT JOIN categories cat ON p.category_id = cat.id LEFT JOIN suppliers sup ON p.supplier_id = sup.id", data)

        # Convert to list of dicts with column names
        return [dict(zip(headers, row)) for row in data]

    @staticmethod
    def fetch_all_transactions(from_date=None, to_date=None, account_number=None):
        """Fetch all accounting transactions with running balance"""
        headers = ['Date', 'JV ID', 'Reference', 'Account/Aux', 'Debit', 'Credit', 'Balance']
        data = []
        sql = """
            SELECT 
                CAST(t.transaction_date AS DATE) as Date,
                t.jv_id as JV_ID,
                t.reference_type + ' #' + ISNULL(CAST(t.reference_id AS VARCHAR), '') as Reference,
                COALESCE(CAST(ax.number AS VARCHAR(50)), CAST(l.account_number AS VARCHAR(50))) as Account_Aux,
                ISNULL(l.debit, 0) as Debit,
                ISNULL(l.credit, 0) as Credit,
                SUM(ISNULL(l.debit, 0) - ISNULL(l.credit, 0)) OVER (ORDER BY t.transaction_date, t.jv_id, l.line_id ROWS UNBOUNDED PRECEDING) as Balance
            FROM accounting_transactions t
            JOIN accounting_transaction_lines l ON CAST(t.jv_id AS VARCHAR(50)) = CAST(l.jv_id AS VARCHAR(50))
            LEFT JOIN auxiliary ax ON (
                l.auxiliary_id = CAST(ax.number AS VARCHAR(50))
                OR TRY_CAST(l.auxiliary_id AS INT) = ax.id
            )
        """
        params = []
        if account_number:
            sql += " WHERE (CAST(l.auxiliary_id AS VARCHAR(50)) = ? OR CAST(l.account_number AS VARCHAR(50)) = ? OR CAST(ax.number AS VARCHAR(50)) = ?)"
            params.extend([str(account_number), str(account_number), str(account_number)])
        if from_date:
            if 'WHERE' not in sql: sql += " WHERE"
            else: sql += " AND"
            sql += " CAST(t.transaction_date AS DATE) >= ?"
            params.append(from_date)
        if to_date:
            if 'WHERE' not in sql: sql += " WHERE"
            else: sql += " AND"
            sql += " CAST(t.transaction_date AS DATE) <= ?"
            params.append(to_date)
        sql += " ORDER BY t.transaction_date DESC, t.jv_id DESC, l.account_number"
        if params:
            connection.contogetrows_with_params(sql, data, tuple(params))
        else:
            connection.contogetrows(sql, data)
        return [dict(zip(headers, row)) for row in data]

    @staticmethod
    def fetch_transaction_report(reference_type=None, from_date=None, to_date=None):
        """Fetch transactions filtered by type (e.g. 'Sale', 'Payment')"""
        headers = ['Date', 'JV ID', 'Reference ID', 'Description', 'Total Debit', 'Total Credit']
        data = []
        sql = """
            SELECT 
                CAST(transaction_date AS DATE) as Date,
                jv_id as JV_ID,
                reference_id as Reference_ID,
                description as Description,
                SUM(debit) as Total_Debit,
                SUM(credit) as Total_Credit
            FROM accounting_transactions t
            JOIN accounting_transaction_lines l ON t.jv_id = l.jv_id
        """
        params = []
        if reference_type:
            sql += " WHERE reference_type = ?"
            params.append(reference_type)
        if from_date:
            if 'WHERE' not in sql: sql += " WHERE"
            else: sql += " AND"
            sql += " CAST(transaction_date AS DATE) >= ?"
            params.append(from_date)
        if to_date:
            if 'WHERE' not in sql: sql += " WHERE"
            else: sql += " AND"
            sql += " CAST(transaction_date AS DATE) <= ?"
            params.append(to_date)
        if 'WHERE' not in sql: sql += " WHERE 1=1"
        sql += " GROUP BY jv_id, transaction_date, reference_id, description ORDER BY transaction_date DESC, jv_id DESC"
        if params:
            connection.contogetrows_with_params(sql, data, tuple(params))
        else:
            connection.contogetrows(sql, data)
        return [dict(zip(headers, row)) for row in data]

    @staticmethod
    def fetch_user_discounts(from_date=None, to_date=None):
        """Fetch sales with discount tracing per user"""
        headers = []
        data = []
        
        sql = """
            SELECT s.sale_date, s.invoice_number, c.customer_name, u.username, 
                   s.subtotal, s.discount_amount, s.total_amount
            FROM sales s
            JOIN customers c ON s.customer_id = c.id
            LEFT JOIN users u ON s.user_id = u.id
            WHERE s.discount_amount > 0
        """
        params = []
        if from_date and to_date:
            sql += " AND s.sale_date BETWEEN ? AND ?"
            params = [from_date, to_date]
        
        sql += " ORDER BY s.sale_date DESC"
        
        connection.contogetheaders(sql + " AND 1=0", headers)
        connection.contogetrows_with_params(sql, data, params)
        
        return [dict(zip(headers, row)) for row in data]

    @staticmethod
    def fetch_statement_of_account(account_number, from_date=None, to_date=None):
        """Fetch detailed transactions for specific auxiliary/account from accounting tables"""
        headers = ['Date', 'Reference', 'Description', 'Account', 'Debit', 'Credit', 'Balance']
        data = []
        sql = """
            SELECT 
                CAST(t.transaction_date AS DATE) as Date,
                t.reference_type + ' #' + CAST(t.reference_id AS VARCHAR) as Reference,
                t.description as Description,
                COALESCE(l.auxiliary_id, l.account_number) as Account,
                ISNULL(l.debit, 0) as Debit,
                ISNULL(l.credit, 0) as Credit,
                SUM(ISNULL(l.debit, 0) - ISNULL(l.credit, 0)) OVER (ORDER BY t.jv_id, l.line_id ROWS UNBOUNDED PRECEDING) as Balance
            FROM accounting_transactions t
            JOIN accounting_transaction_lines l ON t.jv_id = l.jv_id
            WHERE l.auxiliary_id = ? OR l.account_number = ?
        """
        params = [account_number, account_number]
        if from_date:
            sql += " AND CAST(t.transaction_date AS DATE) >= ?"
            params.append(from_date)
        if to_date:
            sql += " AND CAST(t.transaction_date AS DATE) <= ?"
            params.append(to_date)
        sql += " ORDER BY t.transaction_date, t.jv_id, l.account_number"
        connection.contogetrows_with_params(sql, data, tuple(params))
        return [dict(zip(headers, row)) for row in data]

    @staticmethod
    def fetch_trial_balance(from_date=None, to_date=None):
        """Fetch proper trial balance from accounting tables: accounts with total debit/credit/net"""
        headers = ['Account Number', 'Account Name', 'Total Debit', 'Total Credit', 'Net Balance']
        data = []
        sql = """
            SELECT 
                AccountNum, AccountName,
                ISNULL(SUM(debit), 0) as [Total Debit],
                ISNULL(SUM(credit), 0) as [Total Credit],
                ISNULL(SUM(debit - credit), 0) as [Net Balance]
            FROM (
                SELECT 
                    COALESCE(CAST(a.number AS VARCHAR(50)), CAST(l.account_number AS VARCHAR(50))) as AccountNum,
                    COALESCE(CAST(a.account_name AS VARCHAR(255)), CAST(led.Name_en AS VARCHAR(255)), CAST(l.account_number AS VARCHAR(50))) as AccountName,
                    ISNULL(l.debit, 0) as debit,
                    ISNULL(l.credit, 0) as credit
                FROM accounting_transaction_lines l
                LEFT JOIN auxiliary a ON (
                    l.auxiliary_id = CAST(a.number AS VARCHAR(50))
                    OR TRY_CAST(l.auxiliary_id AS INT) = a.id
                )
                LEFT JOIN Ledger led ON CAST(l.account_number AS VARCHAR(50)) = CAST(led.AccountNumber AS VARCHAR(50))
        """
        params = []
        if from_date or to_date:
            sql += " INNER JOIN accounting_transactions t ON l.jv_id = t.jv_id"
            sql += " WHERE 1=1"
            if from_date:
                sql += " AND CAST(t.transaction_date AS DATE) >= ?"
                params.append(from_date)
            if to_date:
                sql += " AND CAST(t.transaction_date AS DATE) <= ?"
                params.append(to_date)
        
        sql += """
            ) as t
            GROUP BY AccountNum, AccountName
            HAVING ISNULL(SUM(debit), 0) <> 0 OR ISNULL(SUM(credit), 0) <> 0
            ORDER BY AccountNum
        """
        if params:
            connection.contogetrows_with_params(sql, data, tuple(params))
        else:
            connection.contogetrows(sql, data)
        return [dict(zip(headers, row)) for row in data]

    @staticmethod
    def fetch_financial_summary(from_date=None, to_date=None):
        """Financial summary for dashboard (revenue, expenses, profit)"""
        headers = ['metric', 'amount']
        data = []
        # Revenue
        sql_rev = """
            SELECT 'Total Revenue' as metric, ISNULL(SUM(total_amount), 0) as amount
            FROM sales WHERE 1=1
        """
        params = []
        if from_date and to_date:
            sql_rev += " AND sale_date BETWEEN ? AND ?"
            params = [from_date, to_date]
        connection.contogetrows_with_params(sql_rev, data, params if params else None)
        # Expenses stub - add if expenses table has total_amount
        sql_exp = "SELECT 'Total Expenses' as metric, 0.0 as amount"
        connection.contogetrows(sql_exp, data)
        # Profit = Revenue - Expenses (stub)
        sql_profit = "SELECT 'Net Profit' as metric, 0.0 as amount"
        connection.contogetrows(sql_profit, data)
        return data

    @staticmethod
    def fetch_account_details(code, from_date=None, to_date=None):
       # \"\"\"Fetch detailed transactions for account/aux matching code prefix (like statement)\"\"\"
        headers = ['Date', 'Reference', 'Description', 'Account', 'Debit', 'Credit', 'Balance']
        data = []
        sql = """
            SELECT 
                CAST(t.transaction_date AS DATE) as [Date],
                t.reference_type + ' #' + ISNULL(CAST(t.reference_id AS VARCHAR), '') as [Reference],
                t.description as [Description],
                COALESCE(l.auxiliary_id, l.account_number) as [Account],
                ISNULL(l.debit, 0) as [Debit],
                ISNULL(l.credit, 0) as [Credit],
                SUM(ISNULL(l.debit, 0) - ISNULL(l.credit, 0)) OVER (
                  PARTITION BY CASE WHEN l.auxiliary_id LIKE ? + '.%' THEN l.auxiliary_id ELSE l.account_number END
                  ORDER BY t.transaction_date, t.jv_id, l.line_id 
                  ROWS UNBOUNDED PRECEDING
                ) as [Balance]
            FROM accounting_transactions t
            JOIN accounting_transaction_lines l ON t.jv_id = l.jv_id
            WHERE (l.account_number = ? OR l.auxiliary_id LIKE ? + '.%')
        """
        params = [code, code, code]
        if from_date:
            sql += " AND CAST(t.transaction_date AS DATE) >= ?"
            params.append(from_date)
        if to_date:
            sql += " AND CAST(t.transaction_date AS DATE) <= ?"
            params.append(to_date)
        sql += " ORDER BY t.transaction_date, t.jv_id, l.account_number"
        
        connection.contogetrows_with_params(sql, data, tuple(params))
        return [dict(zip(headers, row)) for row in data]

    @staticmethod
    def export_csv(data, headers):
        """Export data to CSV bytes"""
        import io
        import csv
        output = io.BytesIO()
        text_output = io.TextIOWrapper(output, encoding='utf-8', newline='')
        writer = csv.writer(text_output)
        writer.writerow(headers)
        for row in data:
            writer.writerow([str(row.get(h.lower().replace(' ', '_').replace('-', '_'), '')) for h in headers])
        text_output.flush()
        output.seek(0)
        return output.read()

    @staticmethod
    def generate_pdf(title, headers, data):
        """Generate PDF report using platypus tables"""
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from io import BytesIO
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_p = Paragraph(title, styles['Title'])
        story.append(title_p)
        story.append(Spacer(1, 12))
        
        # Data table
        table_data = [headers] + [[str(row.get(h.lower().replace(' ', '_').replace('-', '_'), '')) for h in headers] for row in data[:100]]  # Limit rows
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(table)
        
        doc.build(story)
        buffer.seek(0)
        return buffer.read()


    @staticmethod
    def fetch_hierarchical_trial_balance(ledger_prefix, from_date=None, to_date=None, exclude_reference=None):
        """
        Fetch hierarchical trial balance for ledger prefix (tree based on Ledger.ParentId).
        Includes an optional exclude_reference filter (e.g. for Pre-Closing view).
        """
        data = []
        params = [ledger_prefix, ledger_prefix]

        cte_sql = """
        WITH account_tree AS (
            SELECT
                AccountNumber as code,
                Name_en as name,
                1 as level,
                Id,
                ParentId
            FROM Ledger
            WHERE
                (? <> '' AND AccountNumber = ?)
                OR
                (? = '' AND AccountNumber IN ('1','2','3','4','5','6','7'))
            UNION ALL
            SELECT
                l.AccountNumber,
                l.Name_en,
                at.level + 1,
                l.Id,
                l.ParentId
            FROM account_tree at
            JOIN Ledger l ON l.AccountNumber LIKE at.code + '%'
                           AND LEN(l.AccountNumber) = LEN(at.code) + 1
        )
        """
        main_sql = """
        SELECT
            at.code,
            at.name,
            at.level,
            at.ParentId,
            ISNULL(SUM(CASE WHEN atl.debit > 0 THEN atl.debit ELSE 0 END), 0) as total_debit,
            ISNULL(SUM(CASE WHEN atl.credit > 0 THEN atl.credit ELSE 0 END), 0) as total_credit,
            ISNULL(SUM(atl.debit - atl.credit), 0) as balance,
            COUNT(DISTINCT atl.jv_id) as txn_count
        FROM account_tree at
        LEFT JOIN (
            SELECT atl2.*, ax.number as aux_num
            FROM accounting_transaction_lines atl2
            LEFT JOIN auxiliary ax ON TRY_CAST(atl2.auxiliary_id AS INT) = ax.id
        ) atl ON (
            CAST(atl.account_number AS VARCHAR(50)) = CAST(at.code AS VARCHAR(50))
            OR CAST(atl.aux_num AS VARCHAR(50)) LIKE CAST(at.code AS VARCHAR(50)) + '.%'
        )
        LEFT JOIN accounting_transactions atxn ON CAST(atl.jv_id AS VARCHAR(50)) = CAST(atxn.jv_id AS VARCHAR(50))
        """
        
        if from_date:
            main_sql += " AND CAST(atxn.transaction_date AS DATE) >= ?"
            params.append(from_date)
        if to_date:
            main_sql += " AND CAST(atxn.transaction_date AS DATE) <= ?"
            params.append(to_date)
        if exclude_reference:
            main_sql += " AND atxn.reference_type NOT LIKE ? + '%'"
            params.append(exclude_reference)
            
        main_sql += """
        GROUP BY at.code, at.name, at.level
        ORDER BY at.code
        """
        
        # Execute flat tree query for Ledger accounts
        connection.contogetrows_with_params(cte_sql + main_sql, data, tuple(params))
        
        # Add Auxiliaries to the data list
        aux_sql = """
            SELECT a.number as code, a.account_name as name, 99 as level,
                   ISNULL(SUM(atl.debit), 0) as total_debit,
                   ISNULL(SUM(atl.credit), 0) as total_credit,
                   ISNULL(SUM(atl.debit - atl.credit), 0) as balance,
                   COUNT(DISTINCT atl.jv_id) as txn_count
            FROM auxiliary a
            LEFT JOIN accounting_transaction_lines atl ON atl.auxiliary_id = a.id
            LEFT JOIN accounting_transactions atxn ON atl.jv_id = atxn.jv_id
            WHERE 1=1
        """
        aux_params = []
        if from_date:
            aux_sql += " AND CAST(atxn.transaction_date AS DATE) >= ?"
            aux_params.append(from_date)
        if to_date:
            aux_sql += " AND CAST(atxn.transaction_date AS DATE) <= ?"
            aux_params.append(to_date)
        if exclude_reference:
            aux_sql += " AND atxn.reference_type NOT LIKE ? + '%'"
            aux_params.append(exclude_reference)
        
        aux_sql += " GROUP BY a.number, a.account_name"
        
        aux_data = []
        connection.contogetrows_with_params(aux_sql, aux_data, tuple(aux_params))
        data.extend(aux_data)

        # Match auxiliaryui.py's special synthesized "Cash/GL Account" rows (5300.*)
        # so Trial Balance Hierarchy uses the same naming ('Cash/GL Account').
        cash_gl_sql = """
            SELECT
                atl.account_number as code,
                'Cash/GL Account' as name,
                99 as level,
                NULL as parent_id,
                ISNULL(SUM(atl2.debit), 0) as total_debit,
                ISNULL(SUM(atl2.credit), 0) as total_credit,
                ISNULL(SUM(atl2.debit - atl2.credit), 0) as balance,
                COUNT(DISTINCT atl2.jv_id) as txn_count
            FROM accounting_transaction_lines atl
            JOIN accounting_transaction_lines atl2 ON atl2.account_number = atl.account_number
            LEFT JOIN accounting_transactions t ON atl2.jv_id = t.jv_id
            WHERE atl.account_number LIKE '5300.%'
        """
        cash_gl_params = []
        if from_date:
            cash_gl_sql += " AND CAST(t.transaction_date AS DATE) >= ?"
            cash_gl_params.append(from_date)
        if to_date:
            cash_gl_sql += " AND CAST(t.transaction_date AS DATE) <= ?"
            cash_gl_params.append(to_date)
        if exclude_reference:
            cash_gl_sql += " AND t.reference_type NOT LIKE ? + '%'"
            cash_gl_params.append(exclude_reference)

        cash_gl_sql += """
            GROUP BY atl.account_number
        """
        cash_gl_data = []
        connection.contogetrows_with_params(cash_gl_sql, cash_gl_data, tuple(cash_gl_params))
        data.extend(cash_gl_data)
        
        # Build flat dicts first
        tree_nodes = {}
        leaves_with_txns = {}

        # Build nodes (ledger + auxiliary)
        for row in data:
            # Main ledger query rows now include ParentId.
            # Expected shape for ledger rows:
            #   code, name, level, debit, credit, balance, txn_count
            # Expected shape for auxiliary rows:
            #   code, name, level(99), debit, credit, balance, txn_count
            #
            # Because earlier versions differ, handle both shapes defensively.
            if len(row) >= 8:
                code, name, level, parent_id, debit, credit, balance, txn_count = row[:8]
            else:
                code, name, level, debit, credit, balance, txn_count = row[:7]
                parent_id = None

            code = str(code)
            # Some synthesized accounts may come back with empty name.
            # Align with what auxiliaryui.py / ledger uses for display.
            if not name:
                if code == '5300' or code.startswith('5300.'):
                    name = 'Caise cash'
                elif code == '7111' or code.startswith('7111.'):
                    name = 'Sales manufactured goods'

            node = {
                'code': code,
                'name': name or f'Account {code}',
                'debit': float(debit),
                'credit': float(credit),
                'balance': float(balance),
                'level': int(level),
                'children': [],
                'transactions': [],
                'parent_id': str(parent_id) if parent_id is not None else None,
            }

            tree_nodes[code] = node
            if node['parent_id']:
                # We'll populate id_to_code based on Id, but we don't have ledger Id in this output.
                # So this will be filled only when available.
                pass

            # If leaf (has txns), fetch detailed transactions
            if txn_count > 0:
                txns = Reports._fetch_leaf_transactions(code, from_date, to_date)
                node['transactions'] = txns

        # --------------- IMPORTANT ---------------
        # Some accounts used by Business Track may not exist in Ledger master/tree
        # (or may not fit the ParentId chain). To make the hierarchy/audit report
        # complete, add "ghost" codes directly from accounting_transaction_lines
        # for the selected ledger_prefix.
        # -------------------------------------------
        # We add totals for codes found in transactions where the base matches ledger_prefix.
        ghost_params = []
        ghost_sql = """
            SELECT
                COALESCE(ax.number, l.account_number) as code,
                ISNULL(SUM(l.debit), 0) as total_debit,
                ISNULL(SUM(l.credit), 0) as total_credit
            FROM accounting_transaction_lines l
            LEFT JOIN auxiliary ax ON l.auxiliary_id = ax.id
            LEFT JOIN accounting_transactions t ON l.jv_id = t.jv_id
            WHERE 1=1
        """

        if ledger_prefix:
            ghost_sql += " AND (l.account_number LIKE ? + '%' OR COALESCE(ax.number, l.account_number) LIKE ? + '%')"
            ghost_params.extend([ledger_prefix, ledger_prefix])

        if from_date:
            ghost_sql += " AND CAST(t.transaction_date AS DATE) >= ?"
            ghost_params.append(from_date)
        if to_date:
            ghost_sql += " AND CAST(t.transaction_date AS DATE) <= ?"
            ghost_params.append(to_date)
        if exclude_reference:
            ghost_sql += " AND t.reference_type NOT LIKE ? + '%'"
            ghost_params.append(exclude_reference)

        ghost_sql += """
            GROUP BY COALESCE(ax.number, l.account_number)
        """

        ghost_rows = []
        connection.contogetrows_with_params(ghost_sql, ghost_rows, tuple(ghost_params))
        for g in ghost_rows:
            # Ensure tuple shape (code, debit, credit)
            if not g or len(g) < 3:
                continue
            g_code = str(g[0] or '')
            if not g_code:
                continue

            if g_code in tree_nodes:
                continue

            g_debit = float(g[1] or 0.0)
            g_credit = float(g[2] or 0.0)
            g_balance = g_debit - g_credit

            base_code = g_code.split('.')[0] if '.' in g_code else g_code
            # Root logic in this function uses level==1 only for single-digit roots.
            if len(base_code) == 1 and base_code in ('1','2','3','4','5','6','7'):
                g_level = 1
            else:
                g_level = 2

            tree_nodes[g_code] = {
                'code': g_code,
                'name': f'Account {g_code}',
                'debit': g_debit,
                'credit': g_credit,
                'balance': g_balance,
                'level': int(g_level),
                'children': [],
                'transactions': [],
                'parent_id': None,
            }

        # Build hierarchy using parent-child based on Ledger.ParentId where possible.
        root_nodes = []
        for code, node in tree_nodes.items():
            # Auxiliaries: attach to derived parent ledger by base code (before dot), fallback to root.
            if node['level'] == 99:
                parent_code = code.split('.')[0] if '.' in code else code[:-1]
                if parent_code in tree_nodes:
                    tree_nodes[parent_code]['children'].append(node)
                else:
                    root_nodes.append(node)
                continue

            # Ledger: if level==1 or explicitly matches prefix, treat as root.
            if node['level'] == 1 or (ledger_prefix and code == ledger_prefix):
                root_nodes.append(node)
                continue

            # Without ledger Id in returned rows, we can't reliably map ParentId->code.
            # Fallback: attach by trimming last digit only if that parent exists; otherwise root.
            parent_code = code[:-1] if len(code) > 1 else None
            if parent_code and parent_code in tree_nodes:
                tree_nodes[parent_code]['children'].append(node)
            else:
                root_nodes.append(node)

        return root_nodes

    @staticmethod
    def _fetch_leaf_transactions(code, from_date=None, to_date=None):
        """Fetch detailed transactions for leaf account"""
        headers = ['Date', 'Reference', 'Description', 'Account', 'Debit', 'Credit', 'Balance']
        data = []
        params = [code, code]
        sql = """
            SELECT 
                CAST(t.transaction_date AS DATE) as Date,
                t.reference_type + ' #' + ISNULL(CAST(t.reference_id AS VARCHAR), '') as Reference,
                t.description as Description,
                COALESCE(l.auxiliary_id, l.account_number) as Account,
                ISNULL(l.debit, 0) as Debit,
                ISNULL(l.credit, 0) as Credit,
                SUM(ISNULL(l.debit, 0) - ISNULL(l.credit, 0)) OVER (
                    ORDER BY t.transaction_date, t.jv_id, l.line_id 
                    ROWS UNBOUNDED PRECEDING
                ) as Balance
            FROM accounting_transactions t
            JOIN accounting_transaction_lines l ON t.jv_id = l.jv_id
            LEFT JOIN auxiliary ax ON l.auxiliary_id = ax.id
            WHERE l.account_number = ? OR ax.number LIKE ? + '.%'
        """
        if from_date:
            sql += " AND CAST(t.transaction_date AS DATE) >= ?"
            params.append(from_date)
        if to_date:
            sql += " AND CAST(t.transaction_date AS DATE) <= ?"
            params.append(to_date)
        sql += " ORDER BY t.transaction_date, t.jv_id, l.account_number"
        
        connection.contogetrows_with_params(sql, data, tuple(params))
        return [dict(zip(headers, row)) for row in data]

