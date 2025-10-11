import os
import sys
from datetime import datetime, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.linecharts import HorizontalLineChart
import matplotlib.pyplot as plt
from io import BytesIO
import pandas as pd

# Add the parent directory to the path to import connection
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from connection import connection

class StockMovementReport:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1  # Center alignment
        )

    def get_stock_movement_data(self, days=30):
        """Fetch stock movement data from database"""
        try:
            # Get daily stock movements
            movement_query = """
            SELECT
                CAST(s.transaction_date AS DATE) as movement_date,
                s.transaction_type,
                SUM(s.quantity) as total_quantity,
                COUNT(DISTINCT s.product_id) as products_affected
            FROM stock s
            WHERE s.transaction_date >= DATEADD(DAY, -{days}, GETDATE())
            GROUP BY CAST(s.transaction_date AS DATE), s.transaction_type
            ORDER BY movement_date, s.transaction_type
            """.format(days=days)

            movement_data = []
            connection.contogetrows(movement_query, movement_data)

            # Get product-wise movements
            product_movement_query = """
            SELECT
                p.product_name,
                SUM(CASE WHEN s.transaction_type = 'IN' THEN s.quantity ELSE 0 END) as stock_in,
                SUM(CASE WHEN s.transaction_type = 'OUT' THEN s.quantity ELSE 0 END) as stock_out,
                COALESCE(SUM(s.quantity), 0) as net_change
            FROM products p
            LEFT JOIN stock s ON p.id = s.product_id
            WHERE s.transaction_date >= DATEADD(DAY, -{days}, GETDATE())
            GROUP BY p.id, p.product_name
            HAVING (SUM(CASE WHEN s.transaction_type = 'IN' THEN s.quantity ELSE 0 END) > 0
                   OR SUM(CASE WHEN s.transaction_type = 'OUT' THEN s.quantity ELSE 0 END) > 0)
            ORDER BY ABS(COALESCE(SUM(s.quantity), 0)) DESC
            """.format(days=days)

            product_movement_data = []
            connection.contogetrows(product_movement_query, product_movement_data)

            return movement_data, product_movement_data
        except Exception as e:
            print(f"Error fetching stock movement data: {e}")
            return [], []

    def create_movement_table(self, movement_data):
        """Create stock movement summary table"""
        if not movement_data:
            return Paragraph("No stock movement data available", self.styles['Normal'])

        # Group data by date
        daily_summary = {}
        for row in movement_data:
            if len(row) >= 4:
                date = str(row[0]) if row[0] else ''
                trans_type = str(row[1]) if row[1] else ''
                quantity = int(row[2]) if row[2] else 0
                products = int(row[3]) if row[3] else 0

                if date not in daily_summary:
                    daily_summary[date] = {'IN': 0, 'OUT': 0, 'products': 0}

                if trans_type == 'IN':
                    daily_summary[date]['IN'] += quantity
                elif trans_type == 'OUT':
                    daily_summary[date]['OUT'] += quantity
                daily_summary[date]['products'] = max(daily_summary[date]['products'], products)

        # Table headers
        headers = ['Date', 'Stock In', 'Stock Out', 'Net Change', 'Products Affected']

        # Prepare table data
        table_data = [headers]

        for date in sorted(daily_summary.keys(), reverse=True):
            data = daily_summary[date]
            net_change = data['IN'] - data['OUT']
            table_data.append([
                date,
                f"{data['IN']:,}",
                f"{data['OUT']:,}",
                f"{net_change:+,}",
                f"{data['products']:,}"
            ])

        # Create table
        table = Table(table_data, colWidths=[1.2*inch, 1*inch, 1*inch, 1*inch, 1.2*inch])

        # Apply styling
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])

        # Color code net change
        for i, date in enumerate(sorted(daily_summary.keys(), reverse=True)):
            data = daily_summary[date]
            net_change = data['IN'] - data['OUT']
            if net_change > 0:
                table_style.add('TEXTCOLOR', (3, i+1), (3, i+1), colors.green)
            elif net_change < 0:
                table_style.add('TEXTCOLOR', (3, i+1), (3, i+1), colors.red)

        table.setStyle(table_style)
        return table

    def create_product_movement_table(self, product_movement_data):
        """Create product-wise movement table"""
        if not product_movement_data:
            return Paragraph("No product movement data available", self.styles['Normal'])

        # Table headers
        headers = ['Product Name', 'Stock In', 'Stock Out', 'Net Change']

        # Prepare table data
        table_data = [headers]

        for row in product_movement_data:
            if len(row) >= 4:
                product_name = str(row[0]) if row[0] else ''
                stock_in = int(row[1]) if row[1] else 0
                stock_out = int(row[2]) if row[2] else 0
                net_change = int(row[3]) if row[3] else 0

                table_data.append([
                    product_name,
                    f"{stock_in:,}",
                    f"{stock_out:,}",
                    f"{net_change:+,}"
                ])

        # Create table
        table = Table(table_data, colWidths=[2.5*inch, 1*inch, 1*inch, 1*inch])

        # Apply styling
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])

        # Color code net change
        for i, row in enumerate(product_movement_data):
            if len(row) >= 4:
                net_change = int(row[3]) if row[3] else 0
                if net_change > 0:
                    table_style.add('TEXTCOLOR', (3, i+1), (3, i+1), colors.green)
                elif net_change < 0:
                    table_style.add('TEXTCOLOR', (3, i+1), (3, i+1), colors.red)

        table.setStyle(table_style)
        return table

    def create_movement_chart(self, movement_data):
        """Create stock movement trend chart"""
        if not movement_data:
            return Paragraph("No movement data available for chart", self.styles['Normal'])

        # Prepare data for chart
        dates = []
        stock_in = []
        stock_out = []

        # Group by date
        daily_data = {}
        for row in movement_data:
            if len(row) >= 3:
                date = str(row[0]) if row[0] else ''
                trans_type = str(row[1]) if row[1] else ''
                quantity = int(row[2]) if row[2] else 0

                if date not in daily_data:
                    daily_data[date] = {'IN': 0, 'OUT': 0}

                if trans_type == 'IN':
                    daily_data[date]['IN'] += quantity
                elif trans_type == 'OUT':
                    daily_data[date]['OUT'] += quantity

        # Sort dates and prepare chart data
        for date in sorted(daily_data.keys()):
            dates.append(date)
            stock_in.append(daily_data[date]['IN'])
            stock_out.append(daily_data[date]['OUT'])

        # Create matplotlib chart
        fig, ax = plt.subplots(figsize=(12, 6))

        ax.plot(dates, stock_in, 'g-o', label='Stock In', linewidth=2, markersize=6)
        ax.plot(dates, stock_out, 'r-s', label='Stock Out', linewidth=2, markersize=6)

        ax.set_title('Stock Movement Trend (Last 30 Days)', fontsize=14, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Quantity', fontsize=12)
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        # Save to BytesIO and create ReportLab Image
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)

        img = Image(buf)
        img.drawHeight = 4 * inch
        img.drawWidth = 8 * inch

        return img

    def generate_report(self, filename="stock_movement_report.pdf"):
        """Generate the complete stock movement report"""
        doc = SimpleDocTemplate(filename, pagesize=A4)
        elements = []

        # Title
        title = Paragraph("📈 Stock Movement Report", self.title_style)
        elements.append(title)
        elements.append(Spacer(1, 12))

        # Report generation date
        date_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        date_para = Paragraph(f"Generated on: {date_str} (Last 30 days)", self.styles['Normal'])
        elements.append(date_para)
        elements.append(Spacer(1, 20))

        # Get data
        movement_data, product_movement_data = self.get_stock_movement_data()

        # Daily movement table
        elements.append(Paragraph("📅 Daily Stock Movement Summary", self.styles['Heading2']))
        movement_table = self.create_movement_table(movement_data)
        elements.append(movement_table)
        elements.append(Spacer(1, 20))

        # Movement trend chart
        elements.append(Paragraph("📊 Stock Movement Trend", self.styles['Heading2']))
        movement_chart = self.create_movement_chart(movement_data)
        elements.append(movement_chart)
        elements.append(Spacer(1, 20))

        # Product-wise movement table
        elements.append(Paragraph("📦 Product-wise Movement", self.styles['Heading2']))
        product_table = self.create_product_movement_table(product_movement_data)
        elements.append(product_table)
        elements.append(Spacer(1, 20))

        # Summary insights
        insights = """
        <b>💡 Key Insights:</b><br/>
        • Green values indicate positive net change (more stock in than out)<br/>
        • Red values indicate negative net change (more stock out than in)<br/>
        • Monitor products with consistently negative net changes<br/>
        • High stock-in days may indicate bulk purchases or restocking<br/>
        • High stock-out days may indicate peak sales periods
        """
        insights_style = ParagraphStyle(
            'InsightsStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            borderColor=colors.blue,
            borderWidth=1,
            borderPadding=10,
            backColor=colors.lightcyan,
            spaceAfter=10
        )
        elements.append(Paragraph(insights, insights_style))

        # Build the PDF
        doc.build(elements)
        print(f"Stock movement report generated: {filename}")

def generate_stock_movement_report():
    """Main function to generate stock movement report"""
    try:
        # Ensure stockreports directory exists
        os.makedirs('stockreports', exist_ok=True)

        # Generate report
        report = StockMovementReport()
        filename = f"stockreports/stock_movement_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        report.generate_report(filename)

        return True, f"Stock movement report generated successfully: {filename}"
    except Exception as e:
        return False, f"Error generating stock movement report: {str(e)}"

if __name__ == "__main__":
    success, message = generate_stock_movement_report()
    print(message)
