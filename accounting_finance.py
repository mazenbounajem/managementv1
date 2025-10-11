from nicegui import ui
from connection import connection
from navigation_improvements import EnhancedNavigation

class AccountingFinanceUI:
    
    def __init__(self):
        with ui.header().classes('items-center justify-between'):
            ui.label('Accounting & Finance Dashboard').classes('text-2xl font-bold')
            ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).props('flat color=white')

        # Main content
        with ui.column().classes('w-full p-6 gap-6'):
            # Financial Overview Cards
            with ui.row().classes('w-full gap-4'):
                with ui.card().classes('w-1/3 p-4 bg-blue-50'):
                    ui.label('Total Revenue').classes('text-lg font-semibold text-blue-700')
                    self.revenue_label = ui.label('Loading...').classes('text-2xl font-bold text-blue-800')
                
                with ui.card().classes('w-1/3 p-4 bg-green-50'):
                    ui.label('Total Expenses').classes('text-lg font-semibold text-green-700')
                    self.expenses_label = ui.label('Loading...').classes('text-2xl font-bold text-green-800')
                
                with ui.card().classes('w-1/3 p-4 bg-purple-50'):
                    ui.label('Net Profit').classes('text-lg font-semibold text-purple-700')
                    self.profit_label = ui.label('Loading...').classes('text-2xl font-bold text-purple-800')
            
            # Quick Actions
            with ui.card().classes('w-full p-4'):
                ui.label('Quick Actions').classes('text-xl font-semibold mb-4')
                with ui.row().classes('w-full gap-3'):
                    ui.button('View Financial Reports', on_click=self.view_reports).props('icon=description')
                    ui.button('Generate Income Statement', on_click=self.generate_income_statement).props('icon=receipt')
                    ui.button('Cash Flow Analysis', on_click=self.cash_flow_analysis).props('icon=trending_up')
                    ui.button('Budget Planning', on_click=self.budget_planning).props('icon=account_balance')
            
            # Recent Transactions
            with ui.card().classes('w-full p-4'):
                ui.label('Recent Transactions').classes('text-xl font-semibold mb-4')
                self.transactions_table = ui.aggrid({
                    'columnDefs': [
                        {'headerName': 'Date', 'field': 'date', 'width': 100},
                        {'headerName': 'Type', 'field': 'type', 'width': 100},
                        {'headerName': 'Description', 'field': 'description', 'width': 200},
                        {'headerName': 'Amount', 'field': 'amount', 'width': 100},
                        {'headerName': 'Status', 'field': 'status', 'width': 100}
                    ],
                    'rowData': [],
                    'defaultColDef': {'flex': 1}
                }).classes('w-full h-64')
            
            # Financial Charts Section
            with ui.card().classes('w-full p-4'):
                ui.label('Financial Overview').classes('text-xl font-semibold mb-4')
                with ui.row().classes('w-full gap-4'):
                    with ui.column().classes('w-1/2'):
                        ui.label('Revenue vs Expenses').classes('text-lg font-medium mb-2')
                        # Placeholder for chart
                        ui.element('div').classes('w-full h-64 bg-gray-100 rounded flex items-center justify-center')
                        ui.label('Revenue vs Expenses Chart').classes('text-gray-500')
                    
                    with ui.column().classes('w-1/2'):
                        ui.label('Profit Trend').classes('text-lg font-medium mb-2')
                        # Placeholder for chart
                        ui.element('div').classes('w-full h-64 bg-gray-100 rounded flex items-center justify-center')
                        ui.label('Profit Trend Chart').classes('text-gray-500')
        
        # Load initial data
        self.load_financial_data()
        self.load_recent_transactions()

    def load_financial_data(self):
        try:
            # Get total revenue from sales
            revenue_data = []
            connection.contogetrows(
                "SELECT SUM(total_amount) FROM sales WHERE payment_status = 'completed'", 
                revenue_data
            )
            total_revenue = revenue_data[0][0] if revenue_data and revenue_data[0][0] else 0
            
            # Get total expenses
            expenses_data = []
            connection.contogetrows(
                "SELECT SUM(amount) FROM expenses WHERE payment_status = 'completed'", 
                expenses_data
            )
            total_expenses = expenses_data[0][0] if expenses_data and expenses_data[0][0] else 0
            
            # Calculate net profit
            net_profit = total_revenue - total_expenses
            
            # Update labels
            self.revenue_label.text = f"${total_revenue:,.2f}"
            self.expenses_label.text = f"${total_expenses:,.2f}"
            self.profit_label.text = f"${net_profit:,.2f}"
            
        except Exception as e:
            ui.notify(f'Error loading financial data: {str(e)}')

    def load_recent_transactions(self):
        try:
            # Combine recent sales and expenses
            transactions = []
            
            # Get recent sales
            sales_data = []
            connection.contogetrows(
                "SELECT sale_date, 'Sale' as type, customer_id, total_amount, payment_status FROM sales ORDER BY sale_date DESC LIMIT 10",
                sales_data
            )
            
            for sale in sales_data:
                transactions.append({
                    'date': str(sale[0]),
                    'type': sale[1],
                    'description': f"Sale to Customer #{sale[2]}",
                    'amount': f"${sale[3]:.2f}",
                    'status': sale[4]
                })
            
            # Get recent expenses
            expenses_data = []
            connection.contogetrows(
                "SELECT expense_date, 'Expense' as type, description, amount, payment_status FROM expenses ORDER BY expense_date DESC LIMIT 10",
                expenses_data
            )
            
            for expense in expenses_data:
                transactions.append({
                    'date': str(expense[0]),
                    'type': expense[1],
                    'description': expense[2],
                    'amount': f"${expense[3]:.2f}",
                    'status': expense[4]
                })
            
            # Sort by date and take top 10
            transactions.sort(key=lambda x: x['date'], reverse=True)
            transactions = transactions[:10]
            
            self.transactions_table.options['rowData'] = transactions
            self.transactions_table.update()
            
        except Exception as e:
            ui.notify(f'Error loading transactions: {str(e)}')

    def view_reports(self):
        try:
            ui.notify('Generating financial reports...')
            report_data = []
            connection.contogetrows("SELECT * FROM expenses", report_data)
            ui.notify(f'Report data fetched: {report_data}')
            if not report_data:
                ui.notify('No data found for financial reports.')
            else:
                # Process and format report_data as needed
                ui.notify('Financial reports generated successfully!')
            ui.notify('Exiting view_reports method.')
        except Exception as e:
            ui.notify(f'Error generating financial reports: {str(e)}')

    def generate_income_statement(self):
        try:
            # Logic to generate income statement
            income_statement_data = []
            connection.contogetrows("SELECT * FROM sales", income_statement_data)
            # Process and format income_statement_data as needed
            ui.notify('Income statement generated successfully!')
        except Exception as e:
            ui.notify(f'Error generating income statement: {str(e)}')

    def cash_flow_analysis(self):
        try:
            # Logic to perform cash flow analysis
            cash_flow_data = []
            connection.contogetrows("SELECT * FROM cash_flows", cash_flow_data)
            # Process and format cash_flow_data as needed
            ui.notify('Cash flow analysis completed!')
        except Exception as e:
            ui.notify(f'Error performing cash flow analysis: {str(e)}')

    def budget_planning(self):
        try:
            # Logic to generate budget planning report
            budget_data = []
            connection.contogetrows("SELECT * FROM budgets", budget_data)
            # Process and format budget_data as needed
            ui.notify('Budget planning report generated successfully!')
        except Exception as e:
            ui.notify(f'Error generating budget planning report: {str(e)}')
        try:
            ui.notify('Generating financial reports...')
            report_data = []
            connection.contogetrows("SELECT * FROM expenses", report_data)
            ui.notify(f'Report data fetched: {report_data}')
            # Process and format report_data as needed
            ui.notify('Financial reports generated successfully!')
        except Exception as e:
            ui.notify(f'Error generating financial reports: {str(e)}')

    def generate_income_statement(self):
        try:
            # Logic to generate income statement
            income_statement_data = []
            connection.contogetrows("SELECT * FROM sales", income_statement_data)
            # Process and format income_statement_data as needed
            ui.notify('Income statement generated successfully!')
        except Exception as e:
            ui.notify(f'Error generating income statement: {str(e)}')

    def cash_flow_analysis(self):
        try:
            # Logic to perform cash flow analysis
            cash_flow_data = []
            connection.contogetrows("SELECT * FROM cash_flows", cash_flow_data)
            # Process and format cash_flow_data as needed
            ui.notify('Cash flow analysis completed!')
        except Exception as e:
            ui.notify(f'Error performing cash flow analysis: {str(e)}')

    def budget_planning(self):
        try:
            # Logic to generate budget planning report
            budget_data = []
            connection.contogetrows("SELECT * FROM budgets", budget_data)
            # Process and format budget_data as needed
            ui.notify('Budget planning report generated successfully!')
        except Exception as e:
            ui.notify(f'Error generating budget planning report: {str(e)}')
        ui.notify('Generating financial reports...')
        # Logic to generate financial reports goes here
        # For now, just a placeholder notification
        # You can replace this with actual report generation logic
        ui.notify('Financial reports generated successfully!')

    def generate_income_statement(self):
        pass  # Placeholder for actual implementation

    def cash_flow_analysis(self):
        pass  # Placeholder for actual implementation

    def budget_planning(self):
        pass  # Placeholder for actual implementation
        ui.notify('Financial reports functionality coming soon!')

    def generate_income_statement(self):
        ui.notify('Income statement generation coming soon!')

    def cash_flow_analysis(self):
        ui.notify('Cash flow analysis coming soon!')

    def budget_planning(self):
        ui.notify('Budget planning functionality coming soon!')

@ui.page('/accounting')
def accounting_finance_page_route():
    AccountingFinanceUI()
