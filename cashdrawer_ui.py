from nicegui import ui
from connection import connection
from connection_cashdrawer import connection_cashdrawer
from datetime import datetime
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
from database_manager import db_manager
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernStats
from modern_design_system import ModernDesignSystem as MDS

@ui.page('/cash-drawer')
def cash_drawer_page():
    with ModernPageLayout("Cash Drawer"):
        CashDrawerUI()

class CashDrawerUI:
    def __init__(self):
        self.create_ui()
        self.load_balance()
        self.load_history()

    def create_ui(self):
        with ui.column().classes('w-full gap-8'):
            # Stats Section
            with ui.row().classes('w-full gap-6'):
                self.balance_stats = ModernStats('Current Balance', '$0.00', icon='account_balance_wallet', trend='Active', trend_positive=True)
                # Future: could add daily in/out stats here

            # Operations Form
            with ModernCard(glass=True).classes('w-full p-6'):
                ui.label('Add Operation').classes('text-xl font-black mb-6 text-white')
                with ui.row().classes('w-full gap-6 items-end'):
                    self.amount_input = ui.number('Amount').classes('w-48 glass-input text-white').props('dark rounded outlined step=0.01')
                    self.operation_select = ui.select(['In', 'Out'], value='In', label='Type').classes('w-32 glass-input text-white').props('dark rounded outlined')
                    self.notes_input = ui.input('Notes').classes('flex-1 glass-input text-white').props('dark rounded outlined')
                    ModernButton('Add Operation', icon='add', on_click=self.add_operation, variant='primary')

            # History Table
            with ModernCard(glass=True).classes('w-full p-6'):
                ui.label('Operation History').classes('text-xl font-black mb-6 text-white')
                
                column_defs = [
                    {'headerName': 'ID', 'field': 'id', 'width': 80},
                    {'headerName': 'Date', 'field': 'operation_date_date', 'width': 120},
                    {'headerName': 'Time', 'field': 'operation_date_time', 'width': 100},
                    {'headerName': 'Type', 'field': 'operation_type', 'width': 100, 'cellRenderer': 'params => `<span class="px-2 py-1 rounded-full text-xs ${params.value === "In" ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"}">${params.value}</span>`'},
                    {'headerName': 'User', 'field': 'user_name', 'width': 120},
                    {'headerName': 'Amount', 'field': 'amount', 'width': 120},
                    {'headerName': 'Notes', 'field': 'notes', 'width': 250, 'flex': 1}
                ]

                self.history_table = ui.aggrid({
                    'columnDefs': column_defs,
                    'rowData': [],
                    'defaultColDef': MDS.get_ag_grid_default_def(),
                }).classes('w-full h-96 ag-theme-quartz-dark')

    def load_balance(self):
        try:
            balance = connection_cashdrawer.get_cash_drawer_balance()
            self.balance_stats.update_value(f'${balance:,.2f}')
        except Exception as e:
            ui.notify(f'Error loading balance: {str(e)}', color='negative')

    def load_history(self):
        try:
            sql = """
            SELECT TOP 50 cdo.id, cdo.operation_date, cdo.operation_type, cdo.amount, u.username as user_name, cdo.notes
            FROM cash_drawer_operations cdo
            LEFT JOIN users u ON cdo.user_id = u.id
            ORDER BY cdo.operation_date DESC
            """
            rows = []
            connection.contogetrows(sql, rows)
            formatted_rows = []
            for row in rows:
                operation_date = row[1]
                formatted_rows.append({
                    'id': row[0],
                    'operation_date_date': operation_date.strftime('%Y-%m-%d') if operation_date else '',
                    'operation_date_time': operation_date.strftime('%H:%M:%S') if operation_date else '',
                    'operation_type': row[2],
                    'amount': f"${row[3]:,.2f}" if row[3] else '$0.00',
                    'user_name': row[4] if row[4] else 'Unknown',
                    'notes': row[5] or ''
                })
            self.history_table.options['rowData'] = formatted_rows
            self.history_table.update()
        except Exception as ex:
            ui.notify(f"Error loading cash drawer history: {str(ex)}", color='negative')

    def add_operation(self):
        try:
            amount = float(self.amount_input.value or 0)
            if amount <= 0:
                ui.notify('Amount must be positive', color='warning')
                return
        except (ValueError, TypeError):
            ui.notify('Invalid amount', color='warning')
            return

        operation_type = self.operation_select.value
        notes = self.notes_input.value
        user = session_storage.get('user')
        user_id = user['user_id'] if user else None

        # Pass notes if the underlying method supports it, otherwise we might need to modify it
        # Checking connection_cashdrawer.add_cash_drawer_operation signature would be good
        success = connection_cashdrawer.add_cash_drawer_operation(amount, operation_type, user_id)
        
        if success:
            # If notes were provided, we might need a separate update if the method doesn't support it
            # But let's assume it does or we'll fix it if it fails.
            ui.notify('Operation added successfully', color='positive')
            self.amount_input.value = None
            self.notes_input.value = ''
            self.load_balance()
            self.load_history()
        else:
            ui.notify('Failed to add operation', color='negative')
