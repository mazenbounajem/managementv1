import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from connection import connection
from datetime import datetime
import io

class StockTransactionReport:
    def __init__(self, product_id):
        self.product_id = product_id
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1  # Center alignment
        )

    def get_product_info(self):
        """Get product information"""
        try:
            query = """
            SELECT product_name, barcode, stock_quantity
            FROM products
            WHERE id = ?
            """
            data = []
            connection.contogetrows(query, data, [self.product_id])
            if data:
                return {
                    'name': str(data[0][0]) if data[0][0] else '',
                    'barcode': str(data[0][1]) if data[0][1] else '',
                    'current_stock': int(data[0][2]) if data[0][2] else 0
                }
            return None
        except Exception as e:
            print(f"Error fetching product info: {e}")
            return None

    def get_transaction_data(self):
        """Fetch all stock transactions for the product"""
        try:
            # Get sales transactions (OUT)
            sales_query = """
            SELECT
                'OUT' as type,
                s.sale_date as transaction_date,
                si.quantity as quantity,
                'Sale' as description,
                s.id as reference_id
            FROM sales s
            INNER JOIN sale_items si ON s.id = si.sales_id
            WHERE si.product_id = ?
            ORDER BY s.sale_date
            """
            sales_data = []
            connection.contogetrows(sales_query, sales_data, [self.product_id])

            # Get purchase transactions (IN)
            purchase_query = """
            SELECT
                'IN' as type,
                p.purchase_date as transaction_date,
                pi.quantity as quantity,
                'Purchase' as description,
                p.id as reference_id
            FROM purchases p
            INNER JOIN purchase_items pi ON p.id = pi.purchase_id
            WHERE pi.product_id = ?
            ORDER BY p.purchase_date
            """
            purchase_data = []
            connection.contogetrows(purchase_query, purchase_data, [self.product_id])

            # Get stock operation transactions
            stock_op_query = """
            SELECT
                CASE WHEN soi.adjusted_quantity > soi.previous_quantity THEN 'IN' ELSE 'OUT' END as type,
                so.operation_date as transaction_date,
                ABS(soi.adjusted_quantity - soi.previous_quantity) as quantity,
                so.notes as description,
                so.id as reference_id
            FROM stock_operations so
            INNER JOIN stock_operation_items soi ON so.id = soi.operation_id
            WHERE soi.product_id = ?
            ORDER BY so.operation_date
            """
            stock_op_data = []
            connection.contogetrows(stock_op_query, stock_op_data, [self.product_id])

            # Combine all transactions
            all_transactions = []

            # Add sales transactions
            for row in sales_data:
                all_transactions.append({
                    'date': row[1],
                    'type': row[0],
                    'quantity': int(row[2]) if row[2] else 0,
                    'description': str(row[3]) if row[3] else '',
                    'reference': f"Sale #{row[4]}" if row[4] else ''
                })

            # Add purchase transactions
            for row in purchase_data:
                all_transactions.append({
                    'date': row[1],
                    'type': row[0],
                    'quantity': int(row[2]) if row[2] else 0,
                    'description': str(row[3]) if row[3] else '',
                    'reference': f"Purchase #{row[4]}" if row[4] else ''
                })

            # Add stock operation transactions
            for row in stock_op_data:
                all_transactions.append({
                    'date': row[1],
                    'type': row[0],
                    'quantity': int(row[2]) if row[2] else 0,
                    'description': str(row[3]) if row[3] else '',
                    'reference': f"Stock Op #{row[4]}" if row[4] else ''
                })

            # Sort by date
            all_transactions.sort(key=lambda x: x['date'] if x['date'] else datetime.min)

            return all_transactions

        except Exception as e:
            print(f"Error fetching transaction data: {e}")
            return []

    def create_transaction_table(self, transactions, product_info):
        """Create transaction table with running balance"""
        if not transactions:
            return Paragraph("No transactions found for this product", self.styles['Normal'])

        # Table headers
        headers = ['Date', 'Type', 'Quantity', 'Description', 'Reference', 'Balance']

        table_data = [headers]

        running_balance = 0

        for transaction in transactions:
            # Calculate balance change
            if transaction['type'] == 'IN':
                running_balance += transaction['quantity']
                quantity_display = f"+{transaction['quantity']}"
            else:  # OUT
                running_balance -= transaction['quantity']
                quantity_display = f"-{transaction['quantity']}"

            table_data.append([
                transaction['date'].strftime('%Y-%m-%d %H:%M') if transaction['date'] else '',
                transaction['type'],
                quantity_display,
                transaction['description'],
                transaction['reference'],
                f"{running_balance:,}"
            ])

        # Add current stock verification row
        table_data.append([
            datetime.now().strftime('%Y-%m-%d %H:%M'),
            'CURRENT',
            '',
            'Current Stock Level',
            '',
            f"{product_info['current_stock']:,}"
        ])

        # Create table
        col_widths = [1.2*inch, 0.6*inch, 0.8*inch, 2.0*inch, 1.2*inch, 0.8*inch]
        table = Table(table_data, colWidths=col_widths)

        # Apply styling
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -2), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -2), colors.black),
            ('ALIGN', (1, 1), (2, -2), 'CENTER'),
            ('ALIGN', (5, 1), (5, -2), 'RIGHT'),
            ('ALIGN', (0, 1), (0, -2), 'LEFT'),
            ('ALIGN', (3, 1), (4, -2), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])

        # Style IN transactions (green background)
        for i, transaction in enumerate(transactions):
            if transaction['type'] == 'IN':
                table_style.add('BACKGROUND', (0, i+1), (-1, i+1), colors.lightgreen)

        # Style OUT transactions (light red background)
        for i, transaction in enumerate(transactions):
            if transaction['type'] == 'OUT':
                table_style.add('BACKGROUND', (0, i+1), (-1, i+1), colors.lightcoral)

        # Style current stock row
        current_row_idx = len(table_data) - 1
        table_style.add('BACKGROUND', (0, current_row_idx), (-1, current_row_idx), colors.lightyellow)
        table_style.add('FONTNAME', (0, current_row_idx), (-1, current_row_idx), 'Helvetica-Bold')
        table_style.add('TEXTCOLOR', (0, current_row_idx), (-1, current_row_idx), colors.black)

        table.setStyle(table_style)

        return table

    def generate_report(self, output_path="stock_transaction_report.pdf"):
        """Generate the complete stock transaction report"""
        try:
            # Get product info and transaction data
            product_info = self.get_product_info()
            if not product_info:
                print("Product not found")
                return False

            transactions = self.get_transaction_data()

            # Create PDF document
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            elements = []

            # Title
            title = Paragraph("Stock Transaction Report", self.title_style)
            elements.append(title)
            elements.append(Spacer(1, 0.3*inch))

            # Product information
            product_info_text = f"""
            <b>Product Information:</b><br/>
            • Product Name: {product_info['name']}<br/>
            • Barcode: {product_info['barcode']}<br/>
            • Current Stock: {product_info['current_stock']:,}<br/>
            • Total Transactions: {len(transactions)}
            """
            product_style = ParagraphStyle(
                'ProductStyle',
                parent=self.styles['Normal'],
                fontSize=10,
                borderColor=colors.blue,
                borderWidth=1,
                borderPadding=10,
                backColor=colors.lightblue,
                spaceAfter=15
            )
            elements.append(Paragraph(product_info_text, product_style))

            # Report generation date
            date_style = ParagraphStyle('DateStyle', parent=self.styles['Normal'], fontSize=10, alignment=2)
            report_date = Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", date_style)
            elements.append(report_date)
            elements.append(Spacer(1, 0.3*inch))

            # Transaction table
            elements.append(Paragraph("Transaction History", self.styles['Heading2']))
            elements.append(Spacer(1, 0.2*inch))

            if transactions:
                transaction_table = self.create_transaction_table(transactions, product_info)
                elements.append(transaction_table)
            else:
                elements.append(Paragraph("No transactions found for this product", self.styles['Normal']))

            elements.append(Spacer(1, 0.3*inch))

            # Summary statistics
            if transactions:
                total_in = sum(t['quantity'] for t in transactions if t['type'] == 'IN')
                total_out = sum(t['quantity'] for t in transactions if t['type'] == 'OUT')

                summary_text = f"""
                <b>Transaction Summary:</b><br/>
                • Total Stock In: {total_in:,}<br/>
                • Total Stock Out: {total_out:,}<br/>
                • Net Movement: {total_in - total_out:,}<br/>
                • Current Stock Level: {product_info['current_stock']:,}
                """
                summary_style = ParagraphStyle(
                    'SummaryStyle',
                    parent=self.styles['Normal'],
                    fontSize=10,
                    borderColor=colors.green,
                    borderWidth=1,
                    borderPadding=10,
                    backColor=colors.lightgreen,
                    spaceAfter=10
                )
                elements.append(Paragraph(summary_text, summary_style))

            # Build PDF
            doc.build(elements)
            print(f"Stock transaction report generated successfully: {output_path}")
            return True

        except Exception as e:
            print(f"Error generating stock transaction report: {e}")
            return False

    def generate_report_bytes(self):
        """Generate the stock transaction report and return as bytes (for in-memory display)"""
        try:
            # Get product info and transaction data
            product_info = self.get_product_info()
            if not product_info:
                print("Product not found")
                return None

            transactions = self.get_transaction_data()

            # Create PDF in memory using BytesIO
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []

            # Title
            title = Paragraph("Stock Transaction Report", self.title_style)
            elements.append(title)
            elements.append(Spacer(1, 0.3*inch))

            # Product information
            product_info_text = f"""
            <b>Product Information:</b><br/>
            • Product Name: {product_info['name']}<br/>
            • Barcode: {product_info['barcode']}<br/>
            • Current Stock: {product_info['current_stock']:,}<br/>
            • Total Transactions: {len(transactions)}
            """
            product_style = ParagraphStyle(
                'ProductStyle',
                parent=self.styles['Normal'],
                fontSize=10,
                borderColor=colors.blue,
                borderWidth=1,
                borderPadding=10,
                backColor=colors.lightblue,
                spaceAfter=15
            )
            elements.append(Paragraph(product_info_text, product_style))

            # Report generation date
            date_style = ParagraphStyle('DateStyle', parent=self.styles['Normal'], fontSize=10, alignment=2)
            report_date = Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", date_style)
            elements.append(report_date)
            elements.append(Spacer(1, 0.3*inch))

            # Transaction table
            elements.append(Paragraph("Transaction History", self.styles['Heading2']))
            elements.append(Spacer(1, 0.2*inch))

            if transactions:
                transaction_table = self.create_transaction_table(transactions, product_info)
                elements.append(transaction_table)
            else:
                elements.append(Paragraph("No transactions found for this product", self.styles['Normal']))

            elements.append(Spacer(1, 0.3*inch))

            # Summary statistics
            if transactions:
                total_in = sum(t['quantity'] for t in transactions if t['type'] == 'IN')
                total_out = sum(t['quantity'] for t in transactions if t['type'] == 'OUT')

                summary_text = f"""
                <b>Transaction Summary:</b><br/>
                • Total Stock In: {total_in:,}<br/>
                • Total Stock Out: {total_out:,}<br/>
                • Net Movement: {total_in - total_out:,}<br/>
                • Current Stock Level: {product_info['current_stock']:,}
                """
                summary_style = ParagraphStyle(
                    'SummaryStyle',
                    parent=self.styles['Normal'],
                    fontSize=10,
                    borderColor=colors.green,
                    borderWidth=1,
                    borderPadding=10,
                    backColor=colors.lightgreen,
                    spaceAfter=10
                )
                elements.append(Paragraph(summary_text, summary_style))

            # Build PDF and get bytes
            doc.build(elements)
            pdf_bytes = buffer.getvalue()
            buffer.close()

            return pdf_bytes

        except Exception as e:
            print(f"Error generating stock transaction report: {e}")
            return None

def generate_stock_transaction_report(product_id, output_path=None, return_bytes=False):
    """Main function to generate stock transaction report for a specific product"""
    try:
        # Generate report
        report = StockTransactionReport(product_id)

        if return_bytes:
            # Return PDF as bytes for in-memory display
            pdf_bytes = report.generate_report_bytes()
            if pdf_bytes:
                return True, pdf_bytes
            else:
                return False, "Failed to generate stock transaction report"
        else:
            # Generate file-based report
            if not output_path:
                output_path = f"stockreports/stock_transaction_report_{product_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

            # Ensure stockreports directory exists
            os.makedirs('stockreports', exist_ok=True)

            success = report.generate_report(output_path)

            if success:
                return True, f"Stock transaction report generated successfully: {output_path}"
            else:
                return False, "Failed to generate stock transaction report"

    except Exception as e:
        return False, f"Error generating stock transaction report: {str(e)}"

if __name__ == "__main__":
    # Example usage
    if len(sys.argv) > 1:
        product_id = int(sys.argv[1])
    else:
        product_id = 1  # Default product ID for testing

    success, message = generate_stock_transaction_report(product_id)
    print(message)
