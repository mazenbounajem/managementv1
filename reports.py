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
        """Fetch detailed transactions for a specific auxiliary account from all sources"""
        headers = ['Date', 'Reference', 'Description', 'Debit', 'Credit']
        data = []
        
        # Sources: Journal Vouchers, Sales Payments (Customer accounts), Purchase Payments (Supplier accounts)
        sql = """
            SELECT date, ref as [Reference], descr as [Description], debit, credit FROM (
                SELECT jvh.date, jvh.voucher_number as ref, jvl.remark as descr, 
                       jvl.debit, jvl.credit
                FROM journal_voucher_lines jvl
                JOIN journal_voucher_header jvh ON jvl.header_id = jvh.id
                WHERE jvl.account = ?
                
                UNION ALL
                
                SELECT sp.sale_date, sp.invoice_number, 'Sale Payment' + ISNULL(' (' + sp.notes + ')', ''), 
                       sp.debit, sp.credit
                FROM sales_payment sp
                JOIN customers c ON sp.customer_id = c.id
                WHERE c.auxiliary_number = ?
                
                UNION ALL
                
                SELECT pp.purchase_date, pp.purchase_invoice_number, 'Purchase Payment' + ISNULL(' (' + pp.notes + ')', ''), 
                       pp.debit, pp.credit
                FROM purchase_payment pp
                JOIN suppliers s ON pp.supplier_id = s.id
                WHERE s.auxiliary_number = ?
            ) t
        """
        params = [account_number, account_number, account_number]
        
        if from_date and to_date:
            sql += " WHERE date BETWEEN ? AND ?"
            params.extend([from_date, to_date])
            
        sql += " ORDER BY date ASC"
        
        connection.contogetrows_with_params(sql, data, params)
        
        return [dict(zip(headers, row)) for row in data]

    @staticmethod
    def fetch_trial_balance():
        """Fetch summary of all account balances from all ledger sources"""
        headers = ['Account Number', 'Account Name', 'Total Debit', 'Total Credit', 'Net Balance']
        data = []
        
        sql = """
            SELECT number, account_name, SUM(debit) as total_debit, SUM(credit) as total_credit, 
                   SUM(debit) - SUM(credit) as net_balance
            FROM (
                -- Journal Vouchers
                SELECT a.number, a.account_name, ISNULL(jvl.debit, 0) as debit, ISNULL(jvl.credit, 0) as credit
                FROM auxiliary a
                JOIN journal_voucher_lines jvl ON a.number = jvl.account
                
                UNION ALL
                
                -- Sales Payments
                SELECT c.auxiliary_number, c.customer_name, ISNULL(sp.debit, 0), ISNULL(sp.credit, 0)
                FROM sales_payment sp
                JOIN customers c ON sp.customer_id = c.id
                WHERE c.auxiliary_number IS NOT NULL
                
                UNION ALL
                
                -- Purchase Payments
                SELECT s.auxiliary_number, s.name, ISNULL(pp.debit, 0), ISNULL(pp.credit, 0)
                FROM purchase_payment pp
                JOIN suppliers s ON pp.supplier_id = s.id
                WHERE s.auxiliary_number IS NOT NULL
            ) t
            GROUP BY number, account_name
            HAVING SUM(debit) <> 0 OR SUM(credit) <> 0
        """
        
        connection.contogetrows(sql, data)
        
        return [dict(zip(headers, row)) for row in data]

import io

def export_csv(data, headers):
    output = io.BytesIO()
    # Use TextIOWrapper to write strings to BytesIO
    text_output = io.TextIOWrapper(output, encoding='utf-8', newline='')
    writer = csv.writer(text_output)
    writer.writerow(headers)
    for row in data:
        # Convert header back to snake_case to match data keys
        writer.writerow([row.get(h.lower().replace(' ', '_'), '') for h in headers])
    text_output.flush()
    output.seek(0)
    return output.read()

class ReportPDFGenerator:
    def __init__(self, title):
        self.title = title
        self.buffer = BytesIO()
        self.canvas = canvas.Canvas(self.buffer, pagesize=letter)
        self.width, self.height = letter

    def generate(self, headers, data):
        self.canvas.setFont("Helvetica-Bold", 16)
        self.canvas.drawString(72, self.height - 72, self.title)
        self.canvas.setFont("Helvetica", 12)
        y = self.height - 100
        # Draw headers
        x = 72
        for header in headers:
            self.canvas.drawString(x, y, header)
            x += 100
        y -= 20
        # Draw rows
        for row in data:
            x = 72
            for header in headers:
                value = row.get(header.lower().replace(' ', '_'), '')
                self.canvas.drawString(x, y, str(value))
                x += 100
            y -= 20
            if y < 72:
                self.canvas.showPage()
                y = self.height - 72
        self.canvas.showPage()
        self.canvas.save()
        self.buffer.seek(0)
        return self.buffer.getvalue()

