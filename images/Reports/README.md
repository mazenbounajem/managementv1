# Business Reports Generator

This folder contains Python scripts to generate comprehensive business reports using ReportLab and matplotlib. The reports are designed to provide valuable insights into your business operations.

## Available Reports

### 1. Sales Performance Report (`sales_performance_report.py`)
- **Total Sales Amount**: Overall revenue from completed sales
- **Total Orders**: Number of completed orders
- **Average Order Value**: Revenue per order
- **Monthly Sales Trend**: Line chart showing sales over the last 12 months
- **Top 10 Products by Revenue**: Bar chart of best-selling products
- **Sales Distribution by Category**: Pie chart of sales by product category
- **Top 10 Customers**: Table of highest-spending customers

### 2. Inventory Report (`inventory_report.py`)
- **Total Products**: Count of active products
- **Total Stock Value**: Value of inventory at cost and selling price
- **Low Stock Alerts**: Products below minimum stock level
- **Current Stock Levels**: Detailed table of all products
- **Stock Value by Category**: Bar chart of inventory value distribution
- **Stock Turnover Analysis**: Turnover ratios for top products

### 3. Financial Report (`financial_report.py`)
- **Total Revenue**: Overall income from sales
- **Total Expenses**: Overall business expenses
- **Net Profit**: Revenue minus expenses
- **Profit Margin**: Overall profitability percentage
- **Revenue vs Expenses Trend**: Line chart comparing income and costs
- **Expense Breakdown by Type**: Pie chart of expense categories
- **Profit Margin by Category**: Profitability analysis by product category

## Prerequisites

Make sure you have the required Python packages installed:

```bash
pip install -r requirements.txt
```

Required packages:
- reportlab (for PDF generation)
- matplotlib (for charts)
- pandas (for data manipulation)
- pyodbc (for database connection)

## Usage

### Generate Individual Reports

#### Sales Performance Report
```bash
python Reports/sales_performance_report.py
```

#### Inventory Report
```bash
python Reports/inventory_report.py
```

#### Financial Report
```bash
python Reports/financial_report.py
```

### Generate All Reports at Once

```bash
python Reports/generate_all_reports.py
```

This will generate all three reports and provide a summary of the generation process.

## Output

All reports are saved as PDF files in the `Reports/` folder:
- `sales_performance_report.pdf`
- `inventory_report.pdf`
- `financial_report.pdf`

## Features

- **Professional Layout**: Clean, professional PDF reports with proper formatting
- **Visual Charts**: Interactive charts and graphs for better data visualization
- **Comprehensive Data**: Detailed tables and summaries
- **Error Handling**: Robust error handling with informative messages
- **Database Integration**: Direct connection to your business database
- **Customizable**: Easy to modify queries and layouts

## Database Requirements

The reports expect the following database tables:
- `sales` (with columns: id, sale_date, total_amount, payment_status, customer_id)
- `sale_items` (with columns: id, sales_id, product_id, quantity, unit_price)
- `products` (with columns: id, product_name, barcode, stock_quantity, min_stock_level, cost_price, selling_price, category_id, supplier_id, is_active)
- `categories` (with columns: id, category_name)
- `customers` (with columns: id, customer_name)
- `suppliers` (with columns: id, supplier_name)
- `expenses` (with columns: id, expense_date, amount, payment_status, expense_type_id)
- `expense_types` (with columns: id, expense_type_name)

## Customization

You can customize the reports by:
1. Modifying the SQL queries in each report script
2. Adjusting chart parameters and styling
3. Changing the report layout and formatting
4. Adding additional data fields or calculations

## Troubleshooting

- **Database Connection Issues**: Ensure your database connection is properly configured in `connection.py`
- **Missing Data**: Reports will handle missing data gracefully and show appropriate messages
- **Chart Generation Errors**: Make sure matplotlib is properly installed and configured
- **PDF Generation Errors**: Ensure ReportLab is installed and there are no permission issues writing to the Reports folder

## Support

If you encounter any issues or need help customizing the reports, please check:
1. Database connection settings
2. Required Python packages are installed
3. File permissions for the Reports folder
4. Database schema matches the expected structure
