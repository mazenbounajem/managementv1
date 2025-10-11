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

class FinancialReport:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1  # Center alignment
        )

    def get_financial_data(self):
        """Get financial data from database"""
        try:
            # Get revenue and expenses data
            revenue_query = """
            SELECT
                YEAR(sale_date) as year,
                MONTH(sale_date) as month,
                SUM(total_amount) as monthly_revenue
            FROM sales
            WHERE payment_status = 'completed'
            GROUP BY YEAR(sale_date), MONTH(sale_date)
            ORDER BY year, month
            """
            revenue_data = []
            connection.contogetrows(revenue_query, revenue_data)

            expenses_query = """
            SELECT
                YEAR(expense_date) as year,
                MONTH(expense_date) as month,
                SUM(amount) as monthly_expenses
            FROM expenses
            WHERE payment_status = 'completed'
            GROUP BY YEAR(expense_date), MONTH(expense_date)
            ORDER BY year, month
            """
            expenses_data = []
            connection.contogetrows(expenses_query, expenses_data)

            # Get total revenue and expenses
            total_revenue_query = """
            SELECT SUM(total_amount) as total_revenue
            FROM sales
            WHERE payment_status = 'completed'
            """
            total_revenue_data = []
            connection.contogetrows(total_revenue_query, total_revenue_data)
            total_revenue = total_revenue_data[0][0] if total_revenue_data and total_revenue_data[0][0] else 0

            total_expenses_query = """
            SELECT SUM(amount) as total_expenses
            FROM expenses
            WHERE payment_status = 'completed'
            """
            total_expenses_data = []
            connection.contogetrows(total_expenses_query, total_expenses_data)
            total_expenses = total_expenses_data[0][0] if total_expenses_data and total_expenses_data[0][0] else 0

            # Calculate net profit
            net_profit = total_revenue - total_expenses

            # Get expense breakdown by type
            expense_breakdown_query = """
            SELECT
                expense_type,
                SUM(amount) as total_amount
            FROM expenses
            WHERE payment_status = 'completed'
            GROUP BY expense_type
            ORDER BY total_amount DESC
            """
            expense_breakdown_data = []
            connection.contogetrows(expense_breakdown_query, expense_breakdown_data)

            # Get profit margins by product category
            profit_margin_query = """
            SELECT
                c.category_name,
                SUM((si.unit_price - p.cost_price) * si.quantity) as gross_profit,
                SUM(si.unit_price * si.quantity) as total_revenue
            FROM sale_items si
            JOIN products p ON si.product_id = p.id
            JOIN categories c ON p.category_id = c.id
            JOIN sales s ON si.sales_id = s.id
            WHERE s.payment_status = 'completed'
            GROUP BY c.category_name
            ORDER BY gross_profit DESC
            """
            profit_margin_data = []
            connection.contogetrows(profit_margin_query, profit_margin_data)

            return {
                'revenue_data': revenue_data,
                'expenses_data': expenses_data,
                'total_revenue': total_revenue,
                'total_expenses': total_expenses,
                'net_profit': net_profit,
                'expense_breakdown': expense_breakdown_data,
                'profit_margin_data': profit_margin_data
            }

        except Exception as e:
            print(f"Error getting financial data: {e}")
            return None

    def create_revenue_expenses_chart(self, revenue_data, expenses_data):
        """Create revenue vs expenses line chart"""
        try:
            if not revenue_data and not expenses_data:
                return None

            # Convert to DataFrames
            revenue_df = pd.DataFrame(revenue_data)
            expenses_df = pd.DataFrame(expenses_data)

            # Handle different column structures for revenue
            if len(revenue_df.columns) == 3:
                revenue_df.columns = ['year', 'month', 'monthly_revenue']
            elif len(revenue_df.columns) == 1:
                # If only one column, assume it's monthly_revenue and create dummy year/month
                revenue_df.columns = ['monthly_revenue']
                revenue_df['year'] = datetime.now().year
                revenue_df['month'] = range(1, len(revenue_df) + 1)

            # Handle different column structures for expenses
            if len(expenses_df.columns) == 3:
                expenses_df.columns = ['year', 'month', 'monthly_expenses']
            elif len(expenses_df.columns) == 1:
                # If only one column, assume it's monthly_expenses and create dummy year/month
                expenses_df.columns = ['monthly_expenses']
                expenses_df['year'] = datetime.now().year
                expenses_df['month'] = range(1, len(expenses_df) + 1)

            # Create month-year labels
            if not revenue_df.empty:
                revenue_df['month_year'] = revenue_df.apply(lambda row: f"{int(row['year'])}-{int(row['month']):02d}", axis=1)
            if not expenses_df.empty:
                expenses_df['month_year'] = expenses_df.apply(lambda row: f"{int(row['year'])}-{int(row['month']):02d}", axis=1)

            plt.figure(figsize=(12, 8))

            if not revenue_df.empty:
                plt.plot(revenue_df['month_year'], revenue_df['monthly_revenue'],
                        marker='o', linewidth=2, markersize=6, label='Revenue', color='green')

            if not expenses_df.empty:
                plt.plot(expenses_df['month_year'], expenses_df['monthly_expenses'],
                        marker='s', linewidth=2, markersize=6, label='Expenses', color='red')

            plt.title('Revenue vs Expenses Trend', fontsize=14, fontweight='bold')
            plt.xlabel('Month-Year', fontsize=12)
            plt.ylabel('Amount ($)', fontsize=12)
            plt.xticks(rotation=45)
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close()

            return buf

        except Exception as e:
            print(f"Error creating revenue expenses chart: {e}")
            return None

    def create_expense_breakdown_chart(self, expense_breakdown_data):
        """Create expense breakdown pie chart"""
        try:
            if not expense_breakdown_data:
                return None

            df = pd.DataFrame(expense_breakdown_data)

            # Handle different column structures
            if len(df.columns) == 2:
                df.columns = ['expense_type', 'total_amount']
            elif len(df.columns) == 1:
                # If only one column, create dummy data
                df.columns = ['total_amount']
                df['expense_type'] = [f'Expense {i+1}' for i in range(len(df))]
            else:
                print(f"Unexpected column count for expense breakdown data: {len(df.columns)}")
                return None

            plt.figure(figsize=(10, 8))
            plt.pie(df['total_amount'], labels=df['expense_type'], autopct='%1.1f%%', startangle=90)
            plt.title('Expense Breakdown by Type', fontsize=14, fontweight='bold')
            plt.axis('equal')

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close()

            return buf

        except Exception as e:
            print(f"Error creating expense breakdown chart: {e}")
            return None

    def create_profit_margin_chart(self, profit_margin_data):
        """Create profit margin by category chart"""
        try:
            if not profit_margin_data:
                return None

            df = pd.DataFrame(profit_margin_data)

            # Handle different column structures
            if len(df.columns) == 3:
                df.columns = ['category_name', 'gross_profit', 'total_revenue']
            elif len(df.columns) == 1:
                # If only one column, create dummy data
                df.columns = ['gross_profit']
                df['category_name'] = [f'Category {i+1}' for i in range(len(df))]
                df['total_revenue'] = [1] * len(df)  # Avoid division by zero
            else:
                print(f"Unexpected column count for profit margin data: {len(df.columns)}")
                return None

            # Calculate profit margin percentage
            df['profit_margin'] = (df['gross_profit'] / df['total_revenue']) * 100

            plt.figure(figsize=(12, 8))
            bars = plt.barh(df['category_name'], df['profit_margin'])
            plt.title('Profit Margin by Category (%)', fontsize=14, fontweight='bold')
            plt.xlabel('Profit Margin (%)', fontsize=12)
            plt.ylabel('Category', fontsize=12)

            # Add value labels
            for bar, margin in zip(bars, df['profit_margin']):
                plt.text(bar.get_width() + 0.5,
                        bar.get_y() + bar.get_height()/2,
                        f'{margin:.1f}%',
                        ha='left', va='center', fontsize=10)

            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close()

            return buf

        except Exception as e:
            print(f"Error creating profit margin chart: {e}")
            return None

    def generate_report(self, output_path="financial_report.pdf"):
        """Generate the complete financial report"""
        try:
            # Get data
            data = self.get_financial_data()
            if not data:
                print("No data available for report generation")
                return False

            # Create PDF document
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            elements = []

            # Title
            title = Paragraph("Financial Report", self.title_style)
            elements.append(title)
            elements.append(Spacer(1, 0.5*inch))

            # Report generation date
            date_style = ParagraphStyle('DateStyle', parent=self.styles['Normal'], fontSize=10, alignment=2)
            report_date = Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", date_style)
            elements.append(report_date)
            elements.append(Spacer(1, 0.3*inch))

            # Financial Overview Cards
            overview_style = ParagraphStyle('CardStyle', parent=self.styles['Heading2'], fontSize=16, spaceAfter=10)
            elements.append(Paragraph("Financial Overview", overview_style))

            overview_table_data = [
                ['Metric', 'Value'],
                ['Total Revenue', f"${data['total_revenue']:,.2f}"],
                ['Total Expenses', f"${data['total_expenses']:,.2f}"],
                ['Net Profit', f"${data['net_profit']:,.2f}"],
                ['Profit Margin', f"{(data['net_profit']/data['total_revenue']*100):.1f}%" if data['total_revenue'] > 0 else "0.0%"]
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

            # Revenue vs Expenses Chart
            if data['revenue_data'] or data['expenses_data']:
                elements.append(Paragraph("Revenue vs Expenses Trend", self.styles['Heading2']))
                chart_buf = self.create_revenue_expenses_chart(data['revenue_data'], data['expenses_data'])
                if chart_buf:
                    img = Image(chart_buf)
                    img.drawHeight = 4*inch
                    img.drawWidth = 6*inch
                    elements.append(img)
                elements.append(Spacer(1, 0.5*inch))

            # Expense Breakdown Pie Chart
            if data['expense_breakdown']:
                elements.append(Paragraph("Expense Breakdown by Type", self.styles['Heading2']))
                chart_buf = self.create_expense_breakdown_chart(data['expense_breakdown'])
                if chart_buf:
                    img = Image(chart_buf)
                    img.drawHeight = 4*inch
                    img.drawWidth = 6*inch
                    elements.append(img)
                elements.append(Spacer(1, 0.5*inch))

            # Profit Margin by Category
            if data['profit_margin_data']:
                elements.append(Paragraph("Profit Margin by Category", self.styles['Heading2']))
                chart_buf = self.create_profit_margin_chart(data['profit_margin_data'])
                if chart_buf:
                    img = Image(chart_buf)
                    img.drawHeight = 4*inch
                    img.drawWidth = 6*inch
                    elements.append(img)
                elements.append(Spacer(1, 0.5*inch))

            # Detailed Expense Breakdown Table
            if data['expense_breakdown']:
                elements.append(Paragraph("Detailed Expense Breakdown", self.styles['Heading2']))

                expense_table_data = [['Expense Type', 'Total Amount', 'Percentage']]
                total_expenses = sum(expense[1] for expense in data['expense_breakdown'])

                for expense in data['expense_breakdown']:
                    percentage = (expense[1] / total_expenses * 100) if total_expenses > 0 else 0
                    expense_table_data.append([
                        expense[0],
                        f"${expense[1]:,.2f}",
                        f"{percentage:.1f}%"
                    ])

                expense_table = Table(expense_table_data, colWidths=[2.5*inch, 2*inch, 1.5*inch])
                expense_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.red),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ALIGN', (1, 1), (2, -1), 'RIGHT')
                ]))
                elements.append(expense_table)

            # Build PDF
            doc.build(elements)
            print(f"Financial Report generated successfully: {output_path}")
            return True

        except Exception as e:
            print(f"Error generating financial report: {e}")
            return False

if __name__ == "__main__":
    # Ensure Reports directory exists
    os.makedirs("Reports", exist_ok=True)

    # Generate report
    report = FinancialReport()
    success = report.generate_report("Reports/financial_report.pdf")

    if success:
        print("Financial Report generated successfully!")
    else:
        print("Failed to generate financial report.")
