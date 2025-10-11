from nicegui import ui
from connection import connection
from connection_cashdrawer import connection_cashdrawer
from datetime import datetime
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
from database_manager import db_manager

class CashDrawerUI:
    def __init__(self):
        user = session_storage.get('user')
        permissions = connection.get_user_permissions(user['role_id'])
        allowed_pages = {page for page, can_access in permissions.items() if can_access}

        navigation = EnhancedNavigation(permissions, user)
        navigation.create_navigation_drawer()
        navigation.create_navigation_header()

        ui.label('Cash Drawer').classes('text-2xl font-bold mb-4')

        self.balance_label = ui.label('Current Balance: $0.00').classes('text-lg mb-4')

        with ui.row().classes('mb-4 gap-4 items-center'):
            self.amount_input = ui.input('Amount').props('type=number min=0 step=0.01').classes('w-1/4')
            self.operation_select = ui.select(['In', 'Out'], value='In').classes('w-1/4')
            ui.button('Add Operation', on_click=self.add_operation).props('color=primary')

        self.history_table = ui.aggrid({
            'columnDefs': [
                {'headerName': 'ID', 'field': 'id', 'sortable': True, 'filter': True, 'resizable': True},
                {'headerName': 'Date', 'field': 'operation_date_date', 'sortable': True, 'filter': True, 'resizable': True},
                {'headerName': 'Time', 'field': 'operation_date_time', 'sortable': True, 'filter': True, 'resizable': True},
                {'headerName': 'Type', 'field': 'operation_type', 'sortable': True, 'filter': True, 'resizable': True},
                {'headerName': 'User Name', 'field': 'user_name', 'sortable': True, 'filter': True, 'resizable': True},
                {'headerName': 'Amount', 'field': 'amount', 'sortable': True, 'filter': True, 'resizable': True},
                {'headerName': 'Notes', 'field': 'notes', 'sortable': True, 'filter': True, 'resizable': True}
            ],
            'rowData': []
        }).classes('w-full')

        self.load_balance()
        self.load_history()

    def load_balance(self):
        balance = connection_cashdrawer.get_cash_drawer_balance()
        self.balance_label.set_text(f'Current Balance: ${balance:.2f}')

    def load_history(self):
        try:
            sql = """
            SELECT cdo.id, cdo.operation_date, cdo.operation_type, cdo.amount, u.username as user_name, cdo.notes
            FROM [POSDb].[dbo].[cash_drawer_operations] cdo
            LEFT JOIN [POSDb].[dbo].[users] u ON cdo.user_id = u.id
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
                    'amount': f"${row[3]:.2f}" if row[3] else '$0.00',
                    'user_name': row[4] if row[4] else 'Unknown',
                    'notes': row[5] if row[5] else ''
                })
            self.history_table.options['rowData'] = formatted_rows
            self.history_table.update()
        except Exception as ex:
            print(f"Error loading cash drawer history: {str(ex)}")
            self.history_table.options['rowData'] = []
            self.history_table.update()

    def add_operation(self):
        try:
            amount = float(self.amount_input.value)
            if amount <= 0:
                ui.notify('Amount must be positive', color='red')
                return
        except (ValueError, TypeError):
            ui.notify('Invalid amount', color='red')
            return

        operation_type = self.operation_select.value
        user = session_storage.get('user')
        user_id = user['user_id'] if user else None

        success = connection_cashdrawer.add_cash_drawer_operation(amount, operation_type, user_id)
        if success:
            ui.notify('Operation added successfully', color='green')
            self.amount_input.set_value('')
            self.load_balance()
            self.load_history()
        else:
            ui.notify('Failed to add operation', color='red')

@ui.page('/cash-drawer')
def cash_drawer_page():
    # Check if user is logged in
    user = session_storage.get('user')
    if not user:
        ui.notify('Please login to access this page', color='red')
        # Use timer to defer redirect to avoid AssertionError on startup
        ui.timer(0.01, lambda: ui.run_javascript('window.location.href = "/"'), once=True)
        return

    # Check if user has permission to access cash drawer page
    if not connection.check_page_permission(user['role_id'], 'cash-drawer'):
        ui.notify('You do not have permission to access this page', color='red')
        # Use timer to defer redirect to avoid AssertionError on startup
        ui.timer(0.01, lambda: ui.run_javascript('window.location.href = "/dashboard"'), once=True)
        return

    CashDrawerUI()
