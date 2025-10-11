import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.pdfgen import canvas
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from connection import connection
from datetime import datetime, timedelta
import io

class InventoryReport:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1  # Center alignment
        )

    def get_inventory_data(self):
        """Get inventory data from database"""
        try:
            # Get current stock levels
            stock_query = """
            SELECT
                p.product_name,
                p.barcode,
                p.stock_quantity,
                p.min_stock_level,
                p.cost_price,
                p.price as selling_price,
                c.category_name,
                (p.stock_quantity * p.cost_price) as stock_value
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.is_active = 1
            ORDER BY p.stock_quantity ASC
            """
            stock_data = []
            connection.contogetrows(stock_query, stock_data)

            # Get low stock alerts
            low_stock_query = """
            SELECT
                p.product_name,
                p.barcode,
                p.stock_quantity,
                p.min_stock_level,
                s.name as supplier_name
            FROM products p
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            WHERE p.stock_quantity <= p.min_stock_level
            AND p.is_active = 1
            ORDER BY p.stock_quantity ASC
            """
            low_stock_data = []
            connection.contogetrows(low_stock_query, low_stock_data)

            # Get total stock value
            total_value_query = """
            SELECT
                SUM(p.stock_quantity * p.cost_price) as total_stock_value,
                SUM(p.stock_quantity * p.price) as total_selling_value,
                COUNT(*) as total_products
            FROM products p
            WHERE p.is_active = 1
            """
            total_value_data = []
            connection.contogetrows(total_value_query, total_value_data)
            total_stock_value = total_value_data[0][0] if total_value_data and total_value_data[0][0] else 0
            total_selling_value = total_value_data[0][1] if total_value_data and total_value_data[0][1] else 0
            total_products = total_value_data[0][2] if total_value_data and total_value_data[0][2] else 0

            # Get stock turnover data (simplified - sales in last 30 days vs average stock)
            turnover_query = """
            SELECT
                p.product_name,
                SUM(si.quantity) as sold_last_30_days,
                p.stock_quantity as current_stock,
                AVG(CAST(p.stock_quantity AS FLOAT)) as avg_stock_last_30_days
            FROM products p
            LEFT JOIN sale_items si ON p.id = si.product_id
            LEFT JOIN sales s ON si.sales_id = s.id
            WHERE s.sale_date >= DATEADD(DAY, -30, GETDATE())
            AND p.is_active = 1
            GROUP BY p.product_name, p.stock_quantity
            ORDER BY sold_last_30_days DESC
            """
            turnover_data = []
            connection.contogetrows(turnover_query, turnover_data)

            return {
                'stock_data': stock_data,
                'low_stock_data': low_stock_data,
                'total_stock_value': total_stock_value,
                'total_selling_value': total_selling_value,
                'total_products': total_products,
                'turnover_data': turnover_data
            }

        except Exception as e:
            print(f"Error getting inventory data: {e}")
            return None

    def create_stock_value_chart(self, stock_data):
        """Create stock value visualization"""
        try:
            if not stock_data:
                return None

            df = pd.DataFrame(stock_data)

            # Handle different column structures
            if len(df.columns) == 8:
                df.columns = ['product_name', 'barcode', 'stock_quantity',
                             'min_stock_level', 'cost_price', 'selling_price',
                             'category_name', 'stock_value']
            elif len(df.columns) == 1:
                # If only one column, create dummy data
                df.columns = ['stock_value']
                df['category_name'] = [f'Category {i+1}' for i in range(len(df))]
            else:
                print(f"Unexpected column count for stock data: {len(df.columns)}")
                return None

            # Group by category for stock value
            category_stock = df.groupby('category_name')['stock_value'].sum().sort_values(ascending=False)

            plt.figure(figsize=(12, 8))
            bars = plt.barh(category_stock.index, category_stock.values)
            plt.title('Stock Value by Category', fontsize=14, fontweight='bold')
            plt.xlabel('Stock Value ($)', fontsize=12)
            plt.ylabel('Category', fontsize=12)

            # Add value labels
            for bar, value in zip(bars, category_stock.values):
                plt.text(bar.get_width() + max(category_stock.values) * 0.01,
                        bar.get_y() + bar.get_height()/2,
                        f'${value:,.0f}',
                        ha='left', va='center', fontsize=10)

            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close()

            return buf

        except Exception as e:
            print(f"Error creating stock value chart: {e}")
            return None

    def create_stock_turnover_chart(self, turnover_data):
        """Create stock turnover analysis chart"""
        try:
            if not turnover_data:
                return None

            df = pd.DataFrame(turnover_data)

            # Handle different column structures
            if len(df.columns) == 4:
                df.columns = ['product_name', 'sold_last_30_days',
                             'current_stock', 'avg_stock_last_30_days']
            elif len(df.columns) == 1:
                # If only one column, create dummy data
                df.columns = ['sold_last_30_days']
                df['product_name'] = [f'Product {i+1}' for i in range(len(df))]
                df['current_stock'] = [1] * len(df)
                df['avg_stock_last_30_days'] = [1] * len(df)
            else:
                print(f"Unexpected column count for turnover data: {len(df.columns)}")
                return None

            # Calculate turnover ratio (sold / average stock)
            df['turnover_ratio'] = df['sold_last_30_days'] / df['avg_stock_last_30_days'].replace(0, 1)

            # Take top 10 products
            top_turnover = df.nlargest(10, 'turnover_ratio')

            plt.figure(figsize=(12, 8))
            bars = plt.barh(top_turnover['product_name'], top_turnover['turnover_ratio'])
            plt.title('Stock Turnover Ratio (Top 10 Products)', fontsize=14, fontweight='bold')
            plt.xlabel('Turnover Ratio (Sales / Avg Stock)', fontsize=12)
            plt.ylabel('Product Name', fontsize=12)

            # Add value labels
            for bar, ratio in zip(bars, top_turnover['turnover_ratio']):
                plt.text(bar.get_width() + max(top_turnover['turnover_ratio']) * 0.01,
                        bar.get_y() + bar.get_height()/2,
                        f'{ratio:.2f}',
                        ha='left', va='center', fontsize=10)

            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close()

            return buf

        except Exception as e:
            print(f"Error creating stock turnover chart: {e}")
            return None

    def generate_report(self, output_path="inventory_report.pdf"):
        """Generate the complete inventory report"""
        try:
            # Get data
            data = self.get_inventory_data()
            if not data:
                print("No data available for report generation")
                return False

            # Create PDF document
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            elements = []

            # Title
            title = Paragraph("Inventory Report", self.title_style)
            elements.append(title)
            elements.append(Spacer(1, 0.5*inch))

            # Report generation date
            date_style = ParagraphStyle('DateStyle', parent=self.styles['Normal'], fontSize=10, alignment=2)
            report_date = Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", date_style)
            elements.append(report_date)
            elements.append(Spacer(1, 0.3*inch))

            # Inventory Overview Cards
            overview_style = ParagraphStyle('CardStyle', parent=self.styles['Heading2'], fontSize=16, spaceAfter=10)
            elements.append(Paragraph("Inventory Overview", overview_style))

            overview_table_data = [
                ['Metric', 'Value'],
                ['Total Products', f"{data['total_products']:,}"],
                ['Total Stock Value (Cost)', f"${data['total_stock_value']:,.2f}"],
                ['Total Stock Value (Selling)', f"${data['total_selling_value']:,.2f}"],
                ['Low Stock Items', f"{len(data['low_stock_data'])}"]
            ]

            overview_table = Table(overview_table_data, colWidths=[3*inch, 2*inch])
            overview_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.blue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(overview_table)
            elements.append(Spacer(1, 0.5*inch))

            # Current Stock Levels Table
            if data['stock_data']:
                elements.append(Paragraph("Current Stock Levels", self.styles['Heading2']))

                # Show top 20 products by stock quantity (ascending - lowest first)
                stock_table_data = [['Product Name', 'Barcode', 'Current Stock', 'Min Level', 'Stock Value']]
                for i, stock in enumerate(data['stock_data'][:20]):  # Limit to 20 items
                    stock_table_data.append([
                        stock[0][:30] + '...' if len(stock[0]) > 30 else stock[0],  # Truncate long names
                        stock[1],
                        str(stock[2]),
                        str(stock[3]),
                        f"${stock[7]:,.2f}"
                    ])

                stock_table = Table(stock_table_data, colWidths=[2*inch, 1.5*inch, 1*inch, 1*inch, 1.5*inch])
                stock_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.green),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ALIGN', (2, 1), (4, -1), 'RIGHT')
                ]))
                elements.append(stock_table)
                elements.append(Spacer(1, 0.5*inch))

            # Low Stock Alerts
            if data['low_stock_data']:
                elements.append(Paragraph("Low Stock Alerts", self.styles['Heading2']))

                low_stock_table_data = [['Product Name', 'Barcode', 'Current Stock', 'Min Level', 'Supplier']]
                for stock in data['low_stock_data'][:15]:  # Limit to 15 items
                    low_stock_table_data.append([
                        stock[0][:25] + '...' if len(stock[0]) > 25 else stock[0],
                        stock[1],
                        str(stock[2]),
                        str(stock[3]),
                        stock[4] if stock[4] else 'N/A'
                    ])

                low_stock_table = Table(low_stock_table_data, colWidths=[2*inch, 1.5*inch, 1*inch, 1*inch, 2*inch])
                low_stock_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.red),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                elements.append(low_stock_table)
                elements.append(Spacer(1, 0.5*inch))

            # Stock Value by Category Chart
            if data['stock_data']:
                elements.append(Paragraph("Stock Value by Category", self.styles['Heading2']))
                chart_buf = self.create_stock_value_chart(data['stock_data'])
                if chart_buf:
                    img = Image(chart_buf)
                    img.drawHeight = 4*inch
                    img.drawWidth = 6*inch
                    elements.append(img)
                elements.append(Spacer(1, 0.5*inch))

            # Stock Turnover Analysis
            if data['turnover_data']:
                elements.append(Paragraph("Stock Turnover Analysis (Last 30 Days)", self.styles['Heading2']))
                chart_buf = self.create_stock_turnover_chart(data['turnover_data'])
                if chart_buf:
                    img = Image(chart_buf)
                    img.drawHeight = 4*inch
                    img.drawWidth = 6*inch
                    elements.append(img)
                elements.append(Spacer(1, 0.5*inch))

            # Build PDF
            doc.build(elements)
            print(f"Inventory Report generated successfully: {output_path}")
            return True

        except Exception as e:
            print(f"Error generating inventory report: {e}")
            return False

if __name__ == "__main__":
    # Ensure Reports directory exists
    os.makedirs("Reports", exist_ok=True)

    # Generate report
    report = InventoryReport()
    success = report.generate_report("Reports/inventory_report.pdf")

    if success:
        print("Inventory Report generated successfully!")
    else:
        print("Failed to generate inventory report.")
