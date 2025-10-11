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

class SalesPerformanceReport:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1  # Center alignment
        )

    def get_sales_data(self):
        """Get sales data from database"""
        try:
            # Get total sales
            total_sales_query = """
            SELECT SUM(total_amount) as total_sales,
                   COUNT(*) as total_orders
            FROM sales
            WHERE payment_status = 'completed'
            """
            total_data = []
            connection.contogetrows(total_sales_query, total_data)
            total_sales = total_data[0][0] if total_data and total_data[0][0] else 0
            total_orders = total_data[0][1] if total_data and total_data[0][1] else 0

            # Get monthly sales trend (last 12 months)
            monthly_query = """
            SELECT
                YEAR(sale_date) as year,
                MONTH(sale_date) as month,
                SUM(total_amount) as monthly_total
            FROM sales
            WHERE payment_status = 'completed'
            AND sale_date >= DATEADD(MONTH, -12, GETDATE())
            GROUP BY YEAR(sale_date), MONTH(sale_date)
            ORDER BY year, month
            """
            monthly_data = []
            connection.contogetrows(monthly_query, monthly_data)

            # Get top products
            top_products_query = """
            SELECT TOP 10
                p.product_name,
                SUM(si.quantity) as total_quantity,
                SUM(si.quantity * si.unit_price) as total_revenue
            FROM sale_items si
            JOIN products p ON si.product_id = p.id
            JOIN sales s ON si.sales_id = s.id
            WHERE s.payment_status = 'completed'
            GROUP BY p.product_name
            ORDER BY total_revenue DESC
            """
            top_products_data = []
            connection.contogetrows(top_products_query, top_products_data)

            # Get sales by category
            category_query = """
            SELECT
                c.category_name,
                SUM(si.quantity * si.unit_price) as category_revenue,
                SUM(si.quantity) as category_quantity
            FROM sale_items si
            JOIN products p ON si.product_id = p.id
            JOIN categories c ON p.category_id = c.id
            JOIN sales s ON si.sales_id = s.id
            WHERE s.payment_status = 'completed'
            GROUP BY c.category_name
            ORDER BY category_revenue DESC
            """
            category_data = []
            connection.contogetrows(category_query, category_data)

            # Get customer analysis
            customer_query = """
            SELECT TOP 10
                cu.customer_name,
                COUNT(s.id) as order_count,
                SUM(s.total_amount) as total_spent
            FROM customers cu
            JOIN sales s ON cu.id = s.customer_id
            WHERE s.payment_status = 'completed'
            GROUP BY cu.customer_name
            ORDER BY total_spent DESC
            """
            customer_data = []
            connection.contogetrows(customer_query, customer_data)

            return {
                'total_sales': total_sales,
                'total_orders': total_orders,
                'monthly_data': monthly_data,
                'top_products': top_products_data,
                'category_data': category_data,
                'customer_data': customer_data
            }

        except Exception as e:
            print(f"Error getting sales data: {e}")
            return None

    def create_monthly_trend_chart(self, monthly_data):
        """Create monthly sales trend chart"""
        try:
            if not monthly_data:
                return None

            # Convert to DataFrame for easier plotting
            df = pd.DataFrame(monthly_data)

            # Handle different column structures
            if len(df.columns) == 3:
                df.columns = ['year', 'month', 'monthly_total']
            elif len(df.columns) == 1:
                # If only one column, assume it's the monthly_total and create dummy year/month
                df.columns = ['monthly_total']
                df['year'] = datetime.now().year
                df['month'] = range(1, len(df) + 1)
            else:
                print(f"Unexpected column count for monthly data: {len(df.columns)}")
                return None

            # Create month-year labels
            df['month_year'] = df.apply(lambda row: f"{int(row['year'])}-{int(row['month']):02d}", axis=1)

            plt.figure(figsize=(10, 6))
            plt.plot(df['month_year'], df['monthly_total'], marker='o', linewidth=2, markersize=6)
            plt.title('Monthly Sales Trend (Last 12 Months)', fontsize=14, fontweight='bold')
            plt.xlabel('Month-Year', fontsize=12)
            plt.ylabel('Sales Amount ($)', fontsize=12)
            plt.xticks(rotation=45)
            plt.grid(True, alpha=0.3)
            plt.tight_layout()

            # Save to bytes buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close()

            return buf

        except Exception as e:
            print(f"Error creating monthly trend chart: {e}")
            return None

    def create_top_products_chart(self, top_products_data):
        """Create top products bar chart"""
        try:
            if not top_products_data:
                return None

            df = pd.DataFrame(top_products_data)

            # Handle different column structures
            if len(df.columns) == 3:
                df.columns = ['product_name', 'total_quantity', 'total_revenue']
            elif len(df.columns) == 1:
                # If only one column, create dummy data
                df.columns = ['total_revenue']
                df['product_name'] = [f'Product {i+1}' for i in range(len(df))]
                df['total_quantity'] = [1] * len(df)
            else:
                print(f"Unexpected column count for top products data: {len(df.columns)}")
                return None

            plt.figure(figsize=(12, 8))
            bars = plt.barh(df['product_name'], df['total_revenue'])
            plt.title('Top 10 Products by Revenue', fontsize=14, fontweight='bold')
            plt.xlabel('Revenue ($)', fontsize=12)
            plt.ylabel('Product Name', fontsize=12)

            # Add value labels on bars
            for bar, revenue in zip(bars, df['total_revenue']):
                plt.text(bar.get_width() + max(df['total_revenue']) * 0.01,
                        bar.get_y() + bar.get_height()/2,
                        f'${revenue:,.0f}',
                        ha='left', va='center', fontsize=10)

            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close()

            return buf

        except Exception as e:
            print(f"Error creating top products chart: {e}")
            return None

    def create_category_pie_chart(self, category_data):
        """Create sales by category pie chart"""
        try:
            if not category_data:
                return None

            df = pd.DataFrame(category_data)

            # Handle different column structures
            if len(df.columns) == 3:
                df.columns = ['category_name', 'category_revenue', 'category_quantity']
            elif len(df.columns) == 1:
                # If only one column, create dummy data
                df.columns = ['category_revenue']
                df['category_name'] = [f'Category {i+1}' for i in range(len(df))]
                df['category_quantity'] = [1] * len(df)
            else:
                print(f"Unexpected column count for category data: {len(df.columns)}")
                return None

            plt.figure(figsize=(10, 8))
            plt.pie(df['category_revenue'], labels=df['category_name'], autopct='%1.1f%%', startangle=90)
            plt.title('Sales Distribution by Category', fontsize=14, fontweight='bold')
            plt.axis('equal')

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close()

            return buf

        except Exception as e:
            print(f"Error creating category pie chart: {e}")
            return None

    def generate_report(self, output_path="sales_performance_report.pdf"):
        """Generate the complete sales performance report"""
        try:
            # Get data
            data = self.get_sales_data()
            if not data:
                print("No data available for report generation")
                return False

            # Create PDF document
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            elements = []

            # Title
            title = Paragraph("Sales Performance Report", self.title_style)
            elements.append(title)
            elements.append(Spacer(1, 0.5*inch))

            # Report generation date
            date_style = ParagraphStyle('DateStyle', parent=self.styles['Normal'], fontSize=10, alignment=2)
            report_date = Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", date_style)
            elements.append(report_date)
            elements.append(Spacer(1, 0.3*inch))

            # Total Sales Card
            total_sales_style = ParagraphStyle('CardStyle', parent=self.styles['Heading2'], fontSize=16, spaceAfter=10)
            elements.append(Paragraph("Total Sales Overview", total_sales_style))

            total_sales_table_data = [
                ['Metric', 'Value'],
                ['Total Sales Amount', f"${data['total_sales']:,.2f}"],
                ['Total Orders', f"{data['total_orders']:,}"],
                ['Average Order Value', f"${data['total_sales']/data['total_orders']:,.2f}" if data['total_orders'] > 0 else "$0.00"]
            ]

            total_sales_table = Table(total_sales_table_data, colWidths=[3*inch, 2*inch])
            total_sales_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.blue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(total_sales_table)
            elements.append(Spacer(1, 0.5*inch))

            # Monthly Sales Trend Chart
            if data['monthly_data']:
                elements.append(Paragraph("Monthly Sales Trend", self.styles['Heading2']))
                chart_buf = self.create_monthly_trend_chart(data['monthly_data'])
                if chart_buf:
                    img = Image(chart_buf)
                    img.drawHeight = 3*inch
                    img.drawWidth = 6*inch
                    elements.append(img)
                elements.append(Spacer(1, 0.5*inch))

            # Top Products Chart
            if data['top_products']:
                elements.append(Paragraph("Top 10 Products by Revenue", self.styles['Heading2']))
                chart_buf = self.create_top_products_chart(data['top_products'])
                if chart_buf:
                    img = Image(chart_buf)
                    img.drawHeight = 4*inch
                    img.drawWidth = 6*inch
                    elements.append(img)
                elements.append(Spacer(1, 0.5*inch))

            # Sales by Category Pie Chart
            if data['category_data']:
                elements.append(Paragraph("Sales Distribution by Category", self.styles['Heading2']))
                chart_buf = self.create_category_pie_chart(data['category_data'])
                if chart_buf:
                    img = Image(chart_buf)
                    img.drawHeight = 4*inch
                    img.drawWidth = 6*inch
                    elements.append(img)
                elements.append(Spacer(1, 0.5*inch))

            # Customer Analysis Table
            if data['customer_data']:
                elements.append(Paragraph("Top 10 Customers by Total Spent", self.styles['Heading2']))

                customer_table_data = [['Customer Name', 'Order Count', 'Total Spent']]
                for customer in data['customer_data']:
                    customer_table_data.append([
                        customer[0],
                        str(customer[1]),
                        f"${customer[2]:,.2f}"
                    ])

                customer_table = Table(customer_table_data, colWidths=[3*inch, 1.5*inch, 2*inch])
                customer_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.green),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ALIGN', (1, 1), (-1, -1), 'RIGHT')
                ]))
                elements.append(customer_table)

            # Build PDF
            doc.build(elements)
            print(f"Sales Performance Report generated successfully: {output_path}")
            return True

        except Exception as e:
            print(f"Error generating sales performance report: {e}")
            return False

if __name__ == "__main__":
    # Ensure Reports directory exists
    os.makedirs("Reports", exist_ok=True)

    # Generate report
    report = SalesPerformanceReport()
    success = report.generate_report("Reports/sales_performance_report.pdf")

    if success:
        print("Report generated successfully!")
    else:
        print("Failed to generate report.")
