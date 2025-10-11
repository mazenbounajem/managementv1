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

class CategoryInventoryReport:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1  # Center alignment
        )

    def get_product_data(self):
        """Fetch individual product data with category"""
        try:
            query = """
            SELECT
                p.product_name,
                p.barcode,
                p.stock_quantity,
                p.price,
                p.cost_price,
                c.category_name,
                (p.price - COALESCE(p.cost_price, 0)) as profit,
                (COALESCE(p.stock_quantity, 0) * p.price) as stock_value,
                (COALESCE(p.stock_quantity, 0) * COALESCE(p.cost_price, 0)) as cost_value
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE c.category_name IS NOT NULL AND c.category_name != ''
            ORDER BY c.category_name, p.product_name
            """
            data = []
            connection.contogetrows(query, data)
            return data
        except Exception as e:
            print(f"Error fetching product data: {e}")
            return []

    def create_category_table(self, data):
        """Create detailed product inventory table grouped by category"""
        if not data:
            return Paragraph("No product data available", self.styles['Normal'])

        from reportlab.platypus import Table, TableStyle

        # Group products by category
        category_groups = {}
        overall_totals = {'products': 0, 'stock': 0, 'cost_value': 0.0, 'stock_value': 0.0, 'profit': 0.0}

        for row in data:
            if len(row) >= 9:
                product_name = str(row[0]) if row[0] else ''
                barcode = str(row[1]) if row[1] else ''
                stock_quantity = int(row[2]) if row[2] else 0
                price = float(row[3]) if row[3] else 0.0
                cost_price = float(row[4]) if row[4] else 0.0
                category_name = str(row[5]) if row[5] else 'Uncategorized'
                profit = float(row[6]) if row[6] else 0.0
                stock_value = float(row[7]) if row[7] else 0.0
                cost_value = float(row[8]) if row[8] else 0.0

                if category_name not in category_groups:
                    category_groups[category_name] = {'products': [], 'totals': {'products': 0, 'stock': 0, 'cost_value': 0.0, 'stock_value': 0.0, 'profit': 0.0}}

                category_groups[category_name]['products'].append({
                    'name': product_name,
                    'barcode': barcode,
                    'stock': stock_quantity,
                    'cost_price': cost_price,
                    'price': price,
                    'profit': profit,
                    'stock_value': stock_value,
                    'cost_value': cost_value
                })

                category_groups[category_name]['totals']['products'] += 1
                category_groups[category_name]['totals']['stock'] += stock_quantity
                category_groups[category_name]['totals']['cost_value'] += cost_value
                category_groups[category_name]['totals']['stock_value'] += stock_value
                category_groups[category_name]['totals']['profit'] += profit * stock_quantity  # Total profit based on stock

                overall_totals['products'] += 1
                overall_totals['stock'] += stock_quantity
                overall_totals['cost_value'] += cost_value
                overall_totals['stock_value'] += stock_value
                overall_totals['profit'] += profit * stock_quantity

        # Create elements list for multiple tables
        elements = []

        # Product table headers
        headers = ['Product Name', 'Barcode', 'Stock Qty', 'Cost Price', 'Price', 'Profit', 'Stock Value', 'Cost Value']

        for category_name, category_data in category_groups.items():
            # Category header
            category_header = Paragraph(f"<b>Category: {category_name}</b>", self.styles['Heading3'])
            elements.append(category_header)
            elements.append(Spacer(1, 10))

            # Prepare table data for this category
            table_data = [headers]

            for product in category_data['products']:
                table_data.append([
                    product['name'],
                    product['barcode'],
                    f"{product['stock']:,}",
                    f"${product['cost_price']:.2f}",
                    f"${product['price']:.2f}",
                    f"${product['profit']:.2f}",
                    f"${product['stock_value']:.2f}",
                    f"${product['cost_value']:.2f}"
                ])

            # Add category subtotal
            totals = category_data['totals']
            table_data.append([
                f"Subtotal ({category_name})",
                "-",
                f"{totals['stock']:,}",
                "-",
                "-",
                f"${totals['profit']:.2f}",
                f"${totals['stock_value']:.2f}",
                f"${totals['cost_value']:.2f}"
            ])

            # Create table
            col_widths = [1.5*inch, 1.2*inch, 0.8*inch, 0.9*inch, 0.8*inch, 0.9*inch, 1.0*inch, 1.0*inch]
            table = Table(table_data, colWidths=col_widths)

            # Apply styling
            table_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
                ('ALIGN', (0, 1), (1, -1), 'LEFT'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ])

            # Style the subtotal row
            if len(table_data) > 1:
                subtotal_row_idx = len(table_data) - 1
                table_style.add('BACKGROUND', (0, subtotal_row_idx), (-1, subtotal_row_idx), colors.lightgrey)
                table_style.add('FONTNAME', (0, subtotal_row_idx), (-1, subtotal_row_idx), 'Helvetica-Bold')
                table_style.add('TEXTCOLOR', (0, subtotal_row_idx), (-1, subtotal_row_idx), colors.black)

            table.setStyle(table_style)
            elements.append(table)
            elements.append(Spacer(1, 15))

        # Overall totals table
        totals_table_data = [
            ['Overall Totals', '', f"{overall_totals['products']:,}", '', '', f"${overall_totals['profit']:.2f}", f"${overall_totals['stock_value']:.2f}", f"${overall_totals['cost_value']:.2f}"]
        ]
        totals_table = Table(totals_table_data, colWidths=col_widths)
        totals_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ])
        totals_table.setStyle(totals_style)
        elements.append(totals_table)

        return elements

    def create_category_pie_chart(self, data):
        """Create category distribution pie chart"""
        try:
            if not data:
                return None

            # Convert to DataFrame for easier processing
            df = pd.DataFrame(data)

            # Handle different column structures
            if len(df.columns) >= 9:
                df.columns = ['product_name', 'barcode', 'stock_quantity', 'price', 'cost_price',
                             'category_name', 'profit', 'stock_value', 'cost_value']
            else:
                print(f"Unexpected column count for pie chart data: {len(df.columns)}")
                return None

            # Aggregate by category
            category_totals = df.groupby('category_name')['stock_value'].sum().reset_index()
            category_totals = category_totals[category_totals['stock_value'] > 0]

            # Sort and limit to top 10
            category_totals = category_totals.sort_values('stock_value', ascending=False).head(10)

            if category_totals.empty:
                return None

            plt.figure(figsize=(10, 8))
            plt.pie(category_totals['stock_value'], labels=category_totals['category_name'],
                   autopct='%1.1f%%', startangle=90)
            plt.title('Inventory Value Distribution by Category', fontsize=14, fontweight='bold')
            plt.axis('equal')

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close()

            return buf

        except Exception as e:
            print(f"Error creating category pie chart: {e}")
            return None

    def create_category_bar_chart(self, data):
        """Create category comparison bar chart"""
        try:
            if not data:
                return None

            # Convert to DataFrame for easier processing
            df = pd.DataFrame(data)

            # Handle different column structures
            if len(df.columns) >= 9:
                df.columns = ['product_name', 'barcode', 'stock_quantity', 'price', 'cost_price',
                             'category_name', 'profit', 'stock_value', 'cost_value']
            else:
                print(f"Unexpected column count for bar chart data: {len(df.columns)}")
                return None

            # Aggregate by category
            category_summary = df.groupby('category_name').agg({
                'stock_quantity': 'sum',
                'stock_value': 'sum'
            }).reset_index()

            # Sort and limit to top 10
            category_summary = category_summary.sort_values('stock_value', ascending=False).head(10)

            if category_summary.empty:
                return None

            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

            # Stock levels bar chart
            bars1 = ax1.bar(category_summary['category_name'], category_summary['stock_quantity'],
                           color='skyblue', alpha=0.7)
            ax1.set_title('Stock Levels by Category', fontsize=12, fontweight='bold')
            ax1.set_ylabel('Total Stock Quantity', fontsize=10)
            ax1.tick_params(axis='x', rotation=45)

            # Add value labels on bars
            for bar, stock in zip(bars1, category_summary['stock_quantity']):
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height + max(category_summary['stock_quantity']) * 0.01,
                        f'{int(stock):,}', ha='center', va='bottom', fontsize=8)

            # Value bar chart
            bars2 = ax2.bar(category_summary['category_name'], category_summary['stock_value'],
                           color='lightgreen', alpha=0.7)
            ax2.set_title('Inventory Value by Category', fontsize=12, fontweight='bold')
            ax2.set_ylabel('Total Value ($)', fontsize=10)
            ax2.tick_params(axis='x', rotation=45)

            # Add value labels on bars
            for bar, value in zip(bars2, category_summary['stock_value']):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height + max(category_summary['stock_value']) * 0.01,
                        f'${value:,.0f}', ha='center', va='bottom', fontsize=8)

            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close()

            return buf

        except Exception as e:
            print(f"Error creating category bar chart: {e}")
            return None

    def generate_report(self, output_path="category_inventory_report.pdf"):
        """Generate the complete category inventory report"""
        try:
            # Get data
            data = self.get_product_data()
            if not data:
                print("No data available for report generation")
                return False

            # Create PDF document
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            elements = []

            # Title
            title = Paragraph("Category-wise Inventory Report", self.title_style)
            elements.append(title)
            elements.append(Spacer(1, 0.5*inch))

            # Report generation date
            date_style = ParagraphStyle('DateStyle', parent=self.styles['Normal'], fontSize=10, alignment=2)
            report_date = Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", date_style)
            elements.append(report_date)
            elements.append(Spacer(1, 0.3*inch))

            # Product table
            elements.append(Paragraph("Product Inventory Table by Category", self.styles['Heading2']))
            product_tables = self.create_category_table(data)
            elements.extend(product_tables)
            elements.append(Spacer(1, 0.5*inch))

            # Category pie chart
            if data:
                elements.append(Paragraph("Inventory Value Distribution by Category", self.styles['Heading2']))
                pie_buf = self.create_category_pie_chart(data)
                if pie_buf:
                    img = Image(pie_buf)
                    img.drawHeight = 4*inch
                    img.drawWidth = 6*inch
                    elements.append(img)
                elements.append(Spacer(1, 0.5*inch))

            # Category bar charts
            if data:
                elements.append(Paragraph("Category Comparison Charts", self.styles['Heading2']))
                bar_buf = self.create_category_bar_chart(data)
                if bar_buf:
                    img = Image(bar_buf)
                    img.drawHeight = 5*inch
                    img.drawWidth = 7*inch
                    elements.append(img)
                elements.append(Spacer(1, 0.5*inch))

            # Insights
            insights = """
            <b>Key Insights:</b><br/>
            • Categories are sorted by total inventory value (highest to lowest)<br/>
            • Monitor categories with high out-of-stock percentages<br/>
            • Focus restocking efforts on high-value categories<br/>
            • Consider category-wise purchasing strategies<br/>
            • Use this data for assortment planning and space allocation
            """
            insights_style = ParagraphStyle(
                'InsightsStyle',
                parent=self.styles['Normal'],
                fontSize=10,
                borderColor=colors.green,
                borderWidth=1,
                borderPadding=10,
                backColor=colors.lightgreen,
                spaceAfter=10
            )
            elements.append(Paragraph(insights, insights_style))

            # Build PDF
            doc.build(elements)
            print(f"Category inventory report generated successfully: {output_path}")
            return True

        except Exception as e:
            print(f"Error generating category inventory report: {e}")
            return False

def generate_category_inventory_report():
    """Main function to generate category inventory report"""
    try:
        # Ensure stockreports directory exists
        os.makedirs('stockreports', exist_ok=True)

        # Generate report
        report = CategoryInventoryReport()
        filename = f"stockreports/category_inventory_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        success = report.generate_report(filename)

        if success:
            return True, f"Category inventory report generated successfully: {filename}"
        else:
            return False, "Failed to generate category inventory report"

    except Exception as e:
        return False, f"Error generating category inventory report: {str(e)}"

if __name__ == "__main__":
   # success, message = generate_category_inventory_report()
   # print(message)
    os.makedirs("stockreports", exist_ok=True)

    # Generate report
    stockreports = CategoryInventoryReport()
    success = stockreports.generate_report("stockreports/categoryreport.pdf")

    if success:
        print("Financial Report generated successfully!")
    else:
        print("Failed to generate financial report.")
