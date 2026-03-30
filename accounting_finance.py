from nicegui import ui
from connection import connection
from navigation_improvements import EnhancedNavigation
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernStats
from modern_design_system import ModernDesignSystem as MDS

def accounting_finance_content(standalone=False):
    """Content method for accounting that can be used in tabs"""
    if standalone:
        with ModernPageLayout("Accounting & Finance", standalone=standalone):
            AccountingFinanceUI(standalone=False)
    else:
        AccountingFinanceUI(standalone=False)

@ui.page('/accounting')
def accounting_finance_page_route():
    accounting_finance_content(standalone=True)

class AccountingFinanceUI:
    def __init__(self, standalone=True):
        self.standalone = standalone
        self.revenue_stats = None
        self.expenses_stats = None
        self.profit_stats = None
        self.transactions_table = None
        self.create_ui()
        self.load_financial_data()
        self.load_recent_transactions()

    def create_ui(self):
        # Wrap content in ModernPageLayout only if standalone, otherwise just render the content
        if self.standalone:
            layout_container = ModernPageLayout("Accounting & Finance", standalone=True)
            layout_container.__enter__()
        
        try:
            with ui.column().classes('w-full gap-8 p-4'):
                # Stats Section
                with ui.row().classes('w-full gap-6'):
                    self.revenue_stats = ModernStats('Total Revenue', '$0.00', icon='trending_up', trend='+0%', trend_positive=True)
                    self.expenses_stats = ModernStats('Total Expenses', '$0.00', icon='payments', trend='+0%', trend_positive=False)
                    self.profit_stats = ModernStats('Net Profit', '$0.00', icon='account_balance_wallet', trend='+0%', trend_positive=True)

                # Quick Actions
                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Quick Actions').classes('text-xl font-black mb-6 text-white')
                    with ui.row().classes('w-full gap-4'):
                        ModernButton('Financial Reports', icon='description', on_click=self.view_reports, variant='primary').classes('flex-1')
                        ModernButton('Income Statement', icon='receipt', on_click=self.generate_income_statement, variant='success').classes('flex-1')
                        ModernButton('Cash Flow', icon='trending_up', on_click=self.cash_flow_analysis, variant='secondary').classes('flex-1')
                        ModernButton('Budget Planning', icon='account_balance', on_click=self.budget_planning, variant='outline').classes('flex-1 text-white border-white/20')

                # Transactions and Charts
                with ui.row().classes('w-full gap-8'):
                    # Recent Transactions
                    with ModernCard(glass=True).classes('flex-1 p-6'):
                        ui.label('Recent Transactions').classes('text-xl font-black mb-6 text-white')
                        self.transactions_table = ui.aggrid({
                            'columnDefs': [
                                {'headerName': 'Date', 'field': 'date', 'width': 120},
                                {'headerName': 'Type', 'field': 'type', 'width': 100},
                                {'headerName': 'Description', 'field': 'description', 'width': 220},
                                {'headerName': 'Amount', 'field': 'amount', 'width': 120},
                                {'headerName': 'Status', 'field': 'status', 'width': 120, 'cellRenderer': 'params => `<span class="px-2 py-1 rounded-full text-xs ${params.value === "completed" ? "bg-green-500/20 text-green-400" : "bg-yellow-500/20 text-yellow-400"}">${params.value}</span>`'}
                            ],
                            'rowData': [],
                            'defaultColDef': MDS.get_ag_grid_default_def(),
                        }).classes('w-full h-[400px] ag-theme-quartz-dark')

                    # Charts Placeholder/Section
                    with ui.column().classes('w-[400px] gap-8'):
                        with ModernCard(glass=True).classes('w-full p-6'):
                            ui.label('Revenue Mix').classes('text-lg font-black mb-4 text-white')
                            with ui.column().classes('w-full h-48 items-center justify-center rounded-xl bg-white/5 border border-white/10'):
                                ui.icon('pie_chart', size='48px').classes('text-white/20')
                                ui.label('Revenue Distribution').classes('text-white/40 text-sm mt-2')

                        with ModernCard(glass=True).classes('w-full p-6'):
                            ui.label('Monthly Trend').classes('text-lg font-black mb-4 text-white')
                            with ui.column().classes('w-full h-48 items-center justify-center rounded-xl bg-white/5 border border-white/10'):
                                ui.icon('show_chart', size='48px').classes('text-white/20')
                                ui.label('Growth Trend').classes('text-white/40 text-sm mt-2')
        finally:
            if self.standalone:
                layout_container.__exit__(None, None, None)

    def load_financial_data(self):
        try:
            revenue_data = []
            connection.contogetrows("SELECT SUM(total_amount) FROM sales WHERE payment_status = 'completed'", revenue_data)
            total_revenue = float(revenue_data[0][0]) if revenue_data and revenue_data[0][0] else 0.0
            
            expenses_data = []
            connection.contogetrows("SELECT SUM(amount) FROM expenses WHERE payment_status = 'completed'", expenses_data)
            total_expenses = float(expenses_data[0][0]) if expenses_data and expenses_data[0][0] else 0.0
            
            net_profit = total_revenue - total_expenses
            
            self.revenue_stats.update_value(f"${total_revenue:,.2f}")
            self.expenses_stats.update_value(f"${total_expenses:,.2f}")
            self.profit_stats.update_value(f"${net_profit:,.2f}")
            
        except Exception as e:
            ui.notify(f'Error loading financial data: {str(e)}', color='negative')

    def load_recent_transactions(self):
        try:
            transactions = []
            
            # Recent sales
            sales_data = []
            connection.contogetrows("SELECT TOP 10 sale_date, 'Sale' as type, customer_id, total_amount, payment_status FROM sales ORDER BY sale_date DESC", sales_data)
            
            for sale in sales_data:
                transactions.append({
                    'date': str(sale[0]),
                    'type': sale[1],
                    'description': f"Sale to Customer #{sale[2]}",
                    'amount': f"${sale[3]:.2f}",
                    'status': sale[4]
                })
            
            # Recent expenses
            expenses_data = []
            connection.contogetrows("SELECT TOP 10 expense_date, 'Expense' as type, description, amount, payment_status FROM expenses ORDER BY expense_date DESC", expenses_data)
            
            for expense in expenses_data:
                transactions.append({
                    'date': str(expense[0]),
                    'type': expense[1],
                    'description': expense[2],
                    'amount': f"${expense[3]:.2f}",
                    'status': expense[4]
                })
            
            transactions.sort(key=lambda x: x['date'], reverse=True)
            self.transactions_table.options['rowData'] = transactions[:15]
            self.transactions_table.update()
            
        except Exception as e:
            ui.notify(f'Error loading transactions: {str(e)}', color='negative')

    def view_reports(self):
        ui.notify('Redirecting to Financial Reports...', color='info')
        ui.navigate.to('/reports')

    def generate_income_statement(self):
        ui.notify('Generating Income Statement...', color='info')

    def cash_flow_analysis(self):
        ui.notify('Launching Cash Flow Analysis...', color='info')

    def budget_planning(self):
        ui.notify('Opening Budget Planning...', color='info')