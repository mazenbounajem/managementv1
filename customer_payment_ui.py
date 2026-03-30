from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput, ModernActionBar
from modern_design_system import ModernDesignSystem as MDS

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
        with ui.row().classes('w-full gap-6 items-start'):
            # Left Column: Payment History
            with ui.column().classes('w-1/3 gap-4'):
                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Recent Settlements').classes('text-lg font-black mb-4 text-white uppercase tracking-widest opacity-70')
                    
                    self.table = ui.aggrid({
                        'columnDefs': [
                            {'headerName': 'Date', 'field': 'payment_date', 'width': 120},
                            {'headerName': 'Customer', 'field': 'customer_name', 'flex': 1},
                            {'headerName': 'Amount', 'field': 'amount', 'width': 90},
                            {'headerName': 'Currency', 'field': 'currency', 'width': 90},
                        ],
                        'rowData': [],
                        'defaultColDef': MDS.get_ag_grid_default_def(),
                        'rowSelection': 'single',
                    }).classes('w-full h-[600px] ag-theme-quartz-dark shadow-inner')
                    self.refresh_table()

            # Center Column: Payment Processing
            with ui.column().classes('flex-1 gap-4'):
                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Settlement Processor').classes('text-xl font-black mb-6 text-white uppercase tracking-widest')
                    
                    # Selection Area
                    with ui.row().classes('w-full gap-4 items-center mb-6'):
                        self.customer_input = ui.input('Target Customer').classes('flex-1 glass-input').props('dark rounded outlined readonly')
                        self.customer_input.on('click', lambda: self.customer_dialog.open())
                        ModernButton('Browse', icon='search', on_click=lambda: self.customer_dialog.open(), variant='primary').classes('h-14')

                    # Balance Display
                    with ui.row().classes('w-full gap-4 mb-8 bg-white/5 p-4 rounded-2xl'):
                        with ui.column().classes('flex-1 items-center'):
                            ui.label('Balance LL').classes('text-[10px] uppercase text-white/40 font-bold')
                            self.balance_ll_label = ui.label('0.00').classes('text-lg font-black text-white')
                        with ui.column().classes('flex-1 items-center border-x border-white/10'):
                            ui.label('Balance USD').classes('text-[10px] uppercase text-white/40 font-bold')
                            self.balance_usd_label = ui.label('$0.00').classes('text-lg font-black text-white')
                        with ui.column().classes('flex-1 items-center'):
                            ui.label('Balance EUR').classes('text-[10px] uppercase text-white/40 font-bold')
                            self.balance_eur_label = ui.label('€0.00').classes('text-lg font-black text-white')

                    # Payment Inputs
                    with ui.row().classes('w-full gap-4 items-start'):
                        with ui.column().classes('flex-1 gap-4'):
                            self.payment_amount_input = ui.number('Payment Amount', value=0.0).classes('w-full glass-input').props('dark rounded outlined')
                            self.payment_currency_select = ui.select(
                                options=['L.L.', '$', '€'],
                                value='L.L.',
                                label='Settlement Currency'
                            ).classes('w-full glass-input').props('dark rounded outlined')
                            
                        with ui.column().classes('flex-1 gap-4 justify-center h-full pt-6'):
                            ModernButton('Calculate Exchange', icon='calculate', on_click=self.calculate_exchange, variant='outline').classes('w-full h-14 border-white/20 text-white')
                            self.payment_breakdown_label = ui.label('').classes('text-xs font-bold text-primary italic px-2')

                # Customer dialog
                self.customer_dialog = ui.dialog()
                with self.customer_dialog:
                    with ModernCard(glass=True).classes('w-[800px] p-8'):
                        ui.label('Select Target Customer').classes('text-2xl font-black mb-6 text-white')
                        
                        data = []
                        connection.contogetrows("SELECT id, customer_name, phone, balance_ll, balance_usd, balance_eur FROM customers", data)
                        rows = []
                        for r in data:
                            rows.append({'id': r[0], 'customer_name': r[1], 'phone': r[2], 'balance_ll': r[3], 'balance_usd': r[4], 'balance_eur': r[5]})

                        table = ui.aggrid({
                            'columnDefs': [
                                {'headerName': 'Name', 'field': 'customer_name', 'flex': 1},
                                {'headerName': 'Phone', 'field': 'phone', 'width': 120},
                                {'headerName': 'LL', 'field': 'balance_ll', 'width': 100},
                                {'headerName': 'USD', 'field': 'balance_usd', 'width': 100},
                                {'headerName': 'EUR', 'field': 'balance_eur', 'width': 100},
                            ],
                            'rowData': rows,
                            'defaultColDef': MDS.get_ag_grid_default_def(),
                            'rowSelection': 'single',
                        }).classes('w-full h-96 ag-theme-quartz-dark')

                        async def handle_customer_selection():
                            selected = await table.get_selected_row()
                            if selected:
                                self.customer_input.value = selected['customer_name']
                                self.balance_ll_label.set_text(f"{selected['balance_ll']:.2f}")
                                self.balance_usd_label.set_text(f"${selected['balance_usd']:.2f}")
                                self.balance_eur_label.set_text(f"€{selected['balance_eur']:.2f}")
                                self.selected_customer = selected
                                self.customer_dialog.close()

                        table.on('cellDoubleClicked', handle_customer_selection)
                        ModernButton('Confirm Selection', on_click=handle_customer_selection, variant='primary').classes('w-full mt-6')

            # Right Column: Action Bar
            with ui.column().classes('w-80px items-center'):
                ModernActionBar(
                    on_new=lambda: ui.notify('Clear form feature coming soon'),
                    on_save=self.process_payment,
                    on_refresh=self.refresh_table,
                    on_chatgpt=lambda: ui.open('https://chatgpt.com', new_tab=True),
                    button_class='h-16',
                    classes=' '
                ).style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

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
            self.balance_ll_label.set_text(f"{new_ll_balance:.2f}")
            self.balance_usd_label.set_text(f"${new_usd_balance:.2f}")
            self.balance_eur_label.set_text(f"€{new_eur_balance:.2f}")

            ui.notify(f'Payment processed successfully!', color='green')
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

    with ModernPageLayout("Settlement"):
        CustomerPayment()
