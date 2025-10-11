from io import BytesIO
import csv
from reportlab.lib.pagesizes import letter
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

