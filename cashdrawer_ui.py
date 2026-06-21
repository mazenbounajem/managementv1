from nicegui import ui
from connection import connection
from connection_cashdrawer import connection_cashdrawer
from datetime import datetime
from session_storage import session_storage
from database_manager import db_manager
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernStats

def cash_drawer_content(standalone=False):
    """Content method for cash drawer that can be used in tabs"""
    if standalone:
        with ModernPageLayout("Cash Drawer", standalone=standalone):
            CashDrawerUI(standalone=False)
    else:
        CashDrawerUI(standalone=False)

@ui.page('/cash-drawer')
def cash_drawer_page():
    cash_drawer_content(standalone=True)

class CashDrawerUI:
    def __init__(self, standalone=True):
        self.standalone = standalone
        self.balance_stats = None
        self.amount_input = None
        self.operation_select = None
        self.notes_input = None
        self.history_table = None
        self.create_ui()
        self.load_balance()
        self.load_history()

    def create_ui(self):
        # Wrap content in ModernPageLayout only if standalone, otherwise just render the content
        if self.standalone:
            layout_container = ModernPageLayout("Cash Drawer", standalone=True)
            layout_container.__enter__()
        
        try:
            with ui.row().classes('w-full gap-6 items-start animate-fade-in'):
                # Main Content
                with ui.column().classes('flex-1 gap-8'):
                    # Stats Section
                    with ui.row().classes('w-full gap-6'):
                        self.balance_stats = ModernStats('Current Balance', '$0.00', icon='account_balance_wallet', trend='Active', trend_positive=True)

                    # Operations Form
                    with ModernCard(glass=True).classes('w-full p-6'):
                        ui.label('Add Operation').classes('text-xl font-black mb-6 text-white')
                        with ui.row().classes('w-full gap-6 items-end'):
                            self.amount_input = ui.number('Amount').classes('w-48 glass-input text-white').props('dark rounded outlined step=0.01')
                            self.operation_select = ui.select(['In', 'Out'], value='In', label='Type').classes('w-32 glass-input text-white').props('dark rounded outlined')
                            self.notes_input = ui.input('Notes').classes('flex-1 glass-input text-white').props('dark rounded outlined')
                            ModernButton('Quick Add', icon='add', on_click=self.add_operation, variant='primary')

                    # History Table
                    with ModernCard(glass=True).classes('w-full p-6'):
                        ui.label('Operation History').classes('text-xl font-black mb-6 text-white')

                        columns = [
                            {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left'},
                            {'name': 'operation_date_date', 'label': 'Date', 'field': 'operation_date_date', 'align': 'left'},
                            {'name': 'operation_date_time', 'label': 'Time', 'field': 'operation_date_time', 'align': 'left'},
                            {'name': 'operation_type', 'label': 'Type', 'field': 'operation_type', 'align': 'left'},
                            {'name': 'user_name', 'label': 'User', 'field': 'user_name', 'align': 'left'},
                            {'name': 'amount', 'label': 'Amount', 'field': 'amount', 'align': 'right'},
                            {'name': 'notes', 'label': 'Notes', 'field': 'notes', 'align': 'left'},
                        ]

                        self.history_table = ui.table(
                            columns=columns,
                            rows=[],
                        ).classes('w-full h-96').props('virtual-scroll flat bordered dense hide-pagination :pagination="{rowsPerPage: 0}"')
                
                # Action Bar
                with ui.column().classes('w-80px items-center'):
                    from modern_ui_components import ModernActionBar
                    ModernActionBar(
                        on_new=lambda: [self.amount_input.set_value(None), self.notes_input.set_value('')],
                        on_save=self.add_operation,
                        on_refresh=lambda: [self.load_balance(), self.load_history()],
                        on_chatgpt=lambda: ui.run_javascript('window.open("https://chatgpt.com", "_blank");'),
                        button_class='h-16',
                        classes=' '
                    ).style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')
        finally:
            if self.standalone:
                layout_container.__exit__(None, None, None)

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
            self.history_table.rows = formatted_rows
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

        success = connection_cashdrawer.add_cash_drawer_operation(amount, operation_type, user_id)
        
        if success:
            ui.notify('Operation added successfully', color='positive')
            self.amount_input.value = None
            self.notes_input.value = ''
            # Force a second UI refresh cycle to ensure stats card re-renders
            self.load_history()
            ui.timer(0.05, self.load_balance, once=True)
        else:
            ui.notify('Failed to add operation', color='negative')