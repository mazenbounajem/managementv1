from nicegui import ui
from connection import connection
from datetime import datetime
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage

class CustomerPayment:
    def __init__(self):
        self.input_refs = {}
        self.selected_customer = None
        self.customer_input = None
        self.balance_ll_input = None
        self.balance_usd_input = None
        self.balance_eur_input = None
        self.payment_amount_input = None
        self.payment_currency_select = None
        self.table = None
        self.currency_rows = []
        self.currency_exchange_rates = {}
        self.currency_symbols = {}

        self.load_currencies()
        self.setup_ui()

    def load_currencies(self):
        try:
            self.currency_rows = []
            connection.contogetrows("SELECT id, currency_name, symbol, exchange_rate FROM currencies", self.currency_rows)
            self.currency_exchange_rates = {row[0]: float(row[3]) for row in self.currency_rows}
            self.currency_symbols = {row[2]: row[0] for row in self.currency_rows}
        except Exception as e:
            ui.notify(f'Error loading currencies: {e}', color='red')

    def setup_ui(self):
        # Main content area with splitter layout
        with ui.element('div').classes('flex w-full h-screen'):
            # Left drawer for action buttons
            with ui.column().classes('w-48 p-4 bg-gray-100 flex-shrink-0'):
                ui.label('Actions').classes('text-lg font-bold mb-4')
                ui.button('Process Payment', icon='payment', on_click=self.process_payment).classes('bg-green-500 text-white w-full mb-2')
                ui.button('Refresh', icon='refresh', on_click=self.refresh_table).classes('bg-purple-500 text-white w-full mb-2')

            # Main content area
            with ui.column().classes('flex-1 p-4 overflow-y-auto'):
                ui.label('Customer Payment Settlement').classes('text-2xl font-bold mb-4')

                # Customer selection and balance display
                with ui.row().classes('w-full mb-4'):
                    self.customer_input = ui.input('Customer', placeholder='Select Customer').classes('w-1/4 mr-2')
                    self.customer_input.on('click', lambda: self.customer_dialog.open())

                    self.balance_ll_input = ui.input('Balance LL', value='0.00', readonly=True).classes('w-1/5 mr-2')
                    self.balance_usd_input = ui.input('Balance USD', value='0.00', readonly=True).classes('w-1/5 mr-2')
                    self.balance_eur_input = ui.input('Balance EUR', value='0.00', readonly=True).classes('w-1/5 mr-2')

                # Payment details
                with ui.row().classes('w-full mb-4'):
                    self.payment_amount_input = ui.input('Payment Amount', value='0.00').classes('w-1/4 mr-2')
                    self.payment_currency_select = ui.select(
                        options=['L.L.', '$', '€'],
                        value='L.L.',
                        label='Payment Currency'
                    ).classes('w-1/4 mr-2')

                    ui.button('Calculate Exchange', icon='calculate', on_click=self.calculate_exchange).classes('w-1/4 mr-2 bg-blue-500 text-white')

                # Payment breakdown display
                self.payment_breakdown_label = ui.label('Payment Breakdown:').classes('text-lg font-bold mb-2')

                # Customer dialog
                self.customer_dialog = ui.dialog()
                with self.customer_dialog, ui.card().classes('w-full max-w-4xl'):
                    ui.label('Select Customer').classes('text-xl font-bold mb-4')

                    headers = []
                    connection.contogetheaders("SELECT id, customer_name, phone, balance_ll, balance_usd, balance_eur FROM customers", headers)
                    columns = [{'name': header, 'label': header.title(), 'field': header, 'sortable': True} for header in headers]

                    data = []
                    connection.contogetrows("SELECT id, customer_name, phone, balance_ll, balance_usd, balance_eur FROM customers", data)
                    rows = []
                    for row in data:
                        row_dict = {}
                        for i, header in enumerate(headers):
                            row_dict[header] = row[i]
                        rows.append(row_dict)

                    table = ui.table(columns=columns, rows=rows, pagination=5).classes('w-full')
                    ui.input('Search').bind_value(table, 'filter').classes('text-xs')

                    def on_row_click(row_data):
                        selected_row = row_data.args[1]
                        self.customer_input.value = selected_row['customer_name']
                        self.balance_ll_input.value = f"{selected_row['balance_ll']:.2f}"
                        self.balance_usd_input.value = f"{selected_row['balance_usd']:.2f}"
                        self.balance_eur_input.value = f"{selected_row['balance_eur']:.2f}"
                        self.selected_customer = selected_row
                        self.customer_dialog.close()

                    table.on('rowClick', on_row_click)

                # Payment history table
                ui.label('Payment History').classes('text-xl font-bold mb-2')

                column_defs = [
                    {'headerName': 'ID', 'field': 'id', 'sortable': True, 'filter': True, 'width': 80},
                    {'headerName': 'Date', 'field': 'payment_date', 'sortable': True, 'filter': True, 'width': 150},
                    {'headerName': 'Customer', 'field': 'customer_name', 'sortable': True, 'filter': True, 'width': 200},
                    {'headerName': 'Amount', 'field': 'amount', 'sortable': True, 'filter': True, 'width': 120},
                    {'headerName': 'Currency', 'field': 'currency', 'sortable': True, 'filter': True, 'width': 100},
                    {'headerName': 'Method', 'field': 'payment_method', 'sortable': True, 'filter': True, 'width': 100}
                ]

                self.table = ui.aggrid({
                    'columnDefs': column_defs,
                    'rowData': [],
                    'defaultColDef': {'flex': 1, 'minWidth': 100, 'sortable': True, 'filter': True},
                    'rowSelection': 'single',
                    'domLayout': 'normal',
                    'pagination': True,
                    'paginationPageSize': 10
                }).classes('w-full ag-theme-quartz-custom').style('height: 300px;')

                self.refresh_table()

    def calculate_exchange(self):
        """Calculate payment breakdown in different currencies"""
        try:
            payment_amount = float(self.payment_amount_input.value or 0)
            payment_currency = self.payment_currency_select.value

            if payment_amount <= 0:
                ui.notify('Please enter a valid payment amount', color='warning')
                return

            # Get exchange rates
            ll_rate = next((row[3] for row in self.currency_rows if row[2] == 'L.L.'), 1)
            usd_rate = next((row[3] for row in self.currency_rows if row[2] == '$'), 1)
            eur_rate = next((row[3] for row in self.currency_rows if row[2] == '€'), 1)

            breakdown_text = f"Payment Breakdown for {payment_currency}{payment_amount:.2f}:\n"

            if payment_currency == 'L.L.':
                usd_equivalent = payment_amount / usd_rate
                eur_equivalent = payment_amount / eur_rate
                breakdown_text += f"USD: ${usd_equivalent:.2f} | EUR: €{eur_equivalent:.2f}"
            elif payment_currency == '$':
                ll_equivalent = payment_amount * usd_rate
                eur_equivalent = (payment_amount * usd_rate) / eur_rate
                breakdown_text += f"LL: {ll_equivalent:.2f} | EUR: €{eur_equivalent:.2f}"
            elif payment_currency == '€':
                ll_equivalent = payment_amount * eur_rate
                usd_equivalent = (payment_amount * eur_rate) / usd_rate
                breakdown_text += f"LL: {ll_equivalent:.2f} | USD: ${usd_equivalent:.2f}"

            self.payment_breakdown_label.set_text(breakdown_text)
            ui.notify('Exchange rates calculated', color='info')

        except Exception as e:
            ui.notify(f'Error calculating exchange: {str(e)}', color='red')

    def process_payment(self):
        """Process customer payment and update balances"""
        if not self.selected_customer:
            ui.notify('Please select a customer first', color='red')
            return

        try:
            payment_amount = float(self.payment_amount_input.value or 0)
            payment_currency = self.payment_currency_select.value

            if payment_amount <= 0:
                ui.notify('Please enter a valid payment amount', color='red')
                return

            # Get current balances
            current_ll = float(self.balance_ll_input.value or 0)
            current_usd = float(self.balance_usd_input.value or 0)
            current_eur = float(self.balance_eur_input.value or 0)

            # Convert payment to all currencies for balance updates
            ll_rate = next((row[3] for row in self.currency_rows if row[2] == 'L.L.'), 1)
            usd_rate = next((row[3] for row in self.currency_rows if row[2] == '$'), 1)
            eur_rate = next((row[3] for row in self.currency_rows if row[2] == '€'), 1)

            if payment_currency == 'L.L.':
                ll_payment = payment_amount
                usd_payment = payment_amount / usd_rate
                eur_payment = payment_amount / eur_rate
            elif payment_currency == '$':
                ll_payment = payment_amount * usd_rate
                usd_payment = payment_amount
                eur_payment = (payment_amount * usd_rate) / eur_rate
            elif payment_currency == '€':
                ll_payment = payment_amount * eur_rate
                usd_payment = (payment_amount * eur_rate) / usd_rate
                eur_payment = payment_amount

            # Update customer balances (reduce outstanding balances)
            new_ll_balance = max(0, current_ll - ll_payment)
            new_usd_balance = max(0, current_usd - usd_payment)
            new_eur_balance = max(0, current_eur - eur_payment)

            # Update database
            update_sql = """
            UPDATE customers
            SET balance_ll = ?, balance_usd = ?, balance_eur = ?
            WHERE id = ?
            """
            connection.insertingtodatabase(update_sql, (new_ll_balance, new_usd_balance, new_eur_balance, self.selected_customer['id']))

            # Insert payment record
            payment_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            insert_payment_sql = """
            INSERT INTO customer_payments (customer_id, payment_date, amount, currency, payment_method, notes, created_at)
            VALUES (?, ?, ?, ?, 'Account Settlement', 'Multi-currency payment settlement', ?)
            """
            connection.insertingtodatabase(insert_payment_sql, (
                self.selected_customer['id'],
                payment_date,
                payment_amount,
                payment_currency,
                payment_date
            ))

            # Update UI
            self.balance_ll_input.value = f"{new_ll_balance:.2f}"
            self.balance_usd_input.value = f"{new_usd_balance:.2f}"
            self.balance_eur_input.value = f"{new_eur_balance:.2f}"

            ui.notify(f'Payment of {payment_currency}{payment_amount:.2f} processed successfully!', color='green')
            self.refresh_table()

        except Exception as e:
            ui.notify(f'Error processing payment: {str(e)}', color='red')

    def refresh_table(self):
        """Refresh payment history table"""
        sql = """
        SELECT
            cp.id,
            cp.payment_date,
            c.customer_name,
            cp.amount,
            cp.currency,
            cp.payment_method
        FROM customer_payments cp
        INNER JOIN customers c ON cp.customer_id = c.id
        ORDER BY cp.created_at DESC
        """

        payment_data = []
        connection.contogetrows(sql, payment_data)

        payments = []
        for row in payment_data:
            payment_dict = {
                'id': row[0],
                'payment_date': str(row[1]) if row[1] else '',
                'customer_name': row[2],
                'amount': row[3],
                'currency': row[4],
                'payment_method': row[5]
            }
            payments.append(payment_dict)

        if self.table:
            self.table.options['rowData'] = payments
            self.table.update()

# Register the page route
@ui.page('/customerpayment')
def customer_payment_page_route():
    uiAggridTheme.addingtheme()

    # Check if user is logged in
    user = session_storage.get('user')
    if not user:
        ui.notify('Please login to access this page', color='red')
        ui.run_javascript('window.location.href = "/login"')
        return

    # Get user permissions
    permissions = connection.get_user_permissions(user['role_id'])
    allowed_pages = {page for page, can_access in permissions.items() if can_access}

    # Create enhanced navigation instance
    navigation = EnhancedNavigation(permissions, user)
    navigation.create_navigation_drawer()
    navigation.create_navigation_header()

    CustomerPayment()
