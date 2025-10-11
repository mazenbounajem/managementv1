import os
import sys
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
import matplotlib.pyplot as plt
from io import BytesIO

# Add the parent directory to the path to import connection
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from connection import connection

class LowStockAlertReport:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        self.alert_style = ParagraphStyle(
            'AlertStyle',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.red,
            spaceAfter=20,
            alignment=1
        )

    def get_low_stock_data(self):
        """Fetch low stock items from database"""
        try:
            query = """
            SELECT
                p.product_name,
                p.category,
                COALESCE(SUM(s.quantity), 0) as current_stock,
                p.min_stock_level,
                p.max_stock_level,
                p.unit_price,
                p.supplier_name,
                CASE
                    WHEN COALESCE(SUM(s.quantity), 0) = 0 THEN 'Out of Stock'
                    WHEN COALESCE(SUM(s.quantity), 0) <= p.min_stock_level THEN 'Low Stock'
                    WHEN COALESCE(SUM(s.quantity), 0) <= p.min_stock_level * 1.5 THEN 'Warning'
                    ELSE 'Normal'
                END as stock_status
            FROM products p
            LEFT JOIN stock s ON p.id = s.product_id
            GROUP BY p.id, p.product_name, p.category, p.min_stock_level, p.max_stock_level, p.unit_price, p.supplier_name
            HAVING (COALESCE(SUM(s.quantity), 0) <= p.min_stock_level AND p.min_stock_level > 0)
                OR COALESCE(SUM(s.quantity), 0) = 0
            ORDER BY
                CASE
                    WHEN COALESCE(SUM(s.quantity), 0) = 0 THEN 1
                    WHEN COALESCE(SUM(s.quantity), 0) <= p.min_stock_level THEN 2
                    ELSE 3
                END,
                COALESCE(SUM(s.quantity), 0) ASC
            """
            data = []
            connection.contogetrows(query, data)
            return data
        except Exception as e:
            print(f"Error fetching low stock data: {e}")
            return []

    def create_alerts_table(self, data):
        """Create low stock alerts table"""
        if not data:
            return Paragraph("🎉 No low stock alerts at this time!", self.styles['Normal'])

        # Table headers
        headers = ['Product Name', 'Category', 'Current Stock', 'Min Level', 'Status', 'Supplier', 'Action Required']

        # Prepare table data
        table_data = [headers]

        for row in data:
            if len(row) >= 8:
                product_name = str(row[0]) if row[0] else ''
                category = str(row[1]) if row[1] else ''
                current_stock = int(row[2]) if row[2] else 0
                min_level = int(row[3]) if row[3] else 0
                max_level = int(row[4]) if row[4] else 0
                unit_price = float(row[5]) if row[5] else 0.0
                supplier = str(row[6]) if row[6] else ''
                status = str(row[7]) if row[7] else ''

                # Determine action required
                if current_stock == 0:
                    action = "URGENT: Restock Immediately"
                elif current_stock <= min_level:
                    action = "Reorder Soon"
                else:
                    action = "Monitor Closely"

                table_data.append([
                    product_name,
                    category,
                    f"{current_stock:,}",
                    f"{min_level:,}",
                    status,
                    supplier,
                    action
                ])

        # Create table
        table = Table(table_data, colWidths=[1.5*inch, 1*inch, 0.8*inch, 0.7*inch, 0.8*inch, 1.2*inch, 1.2*inch])

        # Apply conditional formatting
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkred),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (2, 1), (4, -1), 'CENTER'),
            ('ALIGN', (0, 1), (1, -1), 'LEFT'),
            ('ALIGN', (5, 1), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])

        # Apply status-based coloring
        for i, row in enumerate(data):
            if len(row) >= 8:
                status = str(row[7]) if row[7] else ''
                if status == 'Out of Stock':
                    table_style.add('BACKGROUND', (0, i+1), (-1, i+1), colors.lightcoral)
                    table_style.add('TEXTCOLOR', (0, i+1), (-1, i+1), colors.black)
                elif status == 'Low Stock':
                    table_style.add('BACKGROUND', (0, i+1), (-1, i+1), colors.lightyellow)
                    table_style.add('TEXTCOLOR', (0, i+1), (-1, i+1), colors.black)

        table.setStyle(table_style)
        return table

    def create_summary_stats(self, data):
        """Create summary statistics"""
        if not data:
            return Paragraph("No low stock items to summarize", self.styles['Normal'])

        out_of_stock = sum(1 for row in data if len(row) >= 8 and (int(row[2]) if row[2] else 0) == 0)
        low_stock = sum(1 for row in data if len(row) >= 8 and (int(row[2]) if row[2] else 0) <= (int(row[3]) if row[3] else 0) and (int(row[2]) if row[2] else 0) > 0)
        total_items = len(data)

        summary_text = f"""
        <b>🚨 Low Stock Alert Summary</b><br/>
        <br/>
        Total Items Requiring Attention: <b>{total_items:,}</b><br/>
        Out of Stock Items: <b style="color:red">{out_of_stock:,}</b><br/>
        Low Stock Items: <b style="color:orange">{low_stock:,}</b><br/>
        """

        summary_style = ParagraphStyle(
            'SummaryStyle',
            parent=self.styles['Normal'],
            fontSize=12,
            borderColor=colors.red,
            borderWidth=2,
            borderPadding=15,
            borderRadius=5,
            backColor=colors.mistyrose,
            spaceAfter=20
        )

        return Paragraph(summary_text, summary_style)

    def generate_report(self, filename="low_stock_alert_report.pdf"):
        """Generate the complete low stock alert report"""
        doc = SimpleDocTemplate(filename, pagesize=A4)
        elements = []

        # Title
        title = Paragraph("🚨 Low Stock Alert Report", self.title_style)
        elements.append(title)
        elements.append(Spacer(1, 12))

        # Alert message
        alert_msg = Paragraph("⚠️  Items requiring immediate attention are highlighted below", self.alert_style)
        elements.append(alert_msg)
        elements.append(Spacer(1, 12))

        # Report generation date
        date_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        date_para = Paragraph(f"Generated on: {date_str}", self.styles['Normal'])
        elements.append(date_para)
        elements.append(Spacer(1, 20))

        # Get data
        data = self.get_low_stock_data()

        # Summary statistics
        summary = self.create_summary_stats(data)
        elements.append(summary)
        elements.append(Spacer(1, 20))

        # Low stock alerts table
        elements.append(Paragraph("📋 Items Requiring Attention", self.styles['Heading2']))
        alerts_table = self.create_alerts_table(data)
        elements.append(alerts_table)
        elements.append(Spacer(1, 20))

        # Recommendations
        recommendations = """
        <b>💡 Recommendations:</b><br/>
        • Review supplier lead times for critical items<br/>
        • Consider setting up automatic reorder points<br/>
        • Evaluate demand patterns for frequently low-stock items<br/>
        • Contact suppliers for out-of-stock items immediately<br/>
        • Consider alternative suppliers for critical components
        """
        rec_style = ParagraphStyle(
            'RecStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            borderColor=colors.blue,
            borderWidth=1,
            borderPadding=10,
            backColor=colors.lightcyan,
            spaceAfter=10
        )
        elements.append(Paragraph(recommendations, rec_style))

        # Build the PDF
        doc.build(elements)
        print(f"Low stock alert report generated: {filename}")

def generate_low_stock_alert_report():
    """Main function to generate low stock alert report"""
    try:
        # Ensure stockreports directory exists
        os.makedirs('stockreports', exist_ok=True)

        # Generate report
        report = LowStockAlertReport()
        filename = f"stockreports/low_stock_alert_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        report.generate_report(filename)

        return True, f"Low stock alert report generated successfully: {filename}"
    except Exception as e:
        return False, f"Error generating low stock alert report: {str(e)}"

if __name__ == "__main__":
    success, message = generate_low_stock_alert_report()
    print(message)
