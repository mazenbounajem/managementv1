from nicegui import ui
from connection import connection
from modern_design_system import ModernDesignSystem as MDS
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput, ModernTable, ModernActionBar
from session_storage import session_storage
from datetime import datetime
import datetime as dt
import asyncio
import accounting_helpers
from color_palette import ColorPalette
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from loading_indicator import loading_indicator

class CustomerReceiptUI:
    def __init__(self, show_navigation=True):
        # Auth
        user = session_storage.get('user')
        if not user:
            ui.notify('Please login', color='negative')
            ui.navigate.to('/login')
            return

        # Permissions
        permissions = connection.get_user_permissions(user['role_id'])
        if show_navigation:
            navigation = EnhancedNavigation(permissions, user)
            navigation.create_navigation_drawer()
            navigation.create_navigation_header()

        # State
        self.selected_customer = None
        self.unpaid_invoices = []
        self.selected_invoices = []
        self.receipt_data = []
        self.new_mode = False
        self.draft_receipt_id = None
        self.draft_amount = 0.0
        self.draft_method = 'Cash'
        
        self.currency_rows = []
        self.currency_exchange_rates = {}
        self.currency_symbols = {}
        self.default_currency_id = 1
        self.load_currencies()
        self.previous_currency_id = self.default_currency_id

        self.create_ui()

    def load_currencies(self):
        try:
            self.currency_rows = []
            connection.contogetrows("SELECT id, currency_name, symbol, exchange_rate FROM currencies", self.currency_rows)
            self.currency_exchange_rates = {row[0]: float(row[3]) for row in self.currency_rows}
            self.currency_symbols = {row[2]: row[0] for row in self.currency_rows}
            for row in self.currency_rows:
                if row[2] == 'L.L.':
                    self.default_currency_id = row[0]
                    break
            else:
                self.default_currency_id = self.currency_rows[0][0] if self.currency_rows else 1
        except Exception as e:
            ui.notify(f'Error loading currencies: {e}', color='red')
            self.default_currency_id = 1

    def on_currency_change(self):
        # Typically receipt is in base currency, but if we want to support conversion:
        if self.previous_currency_id != self.currency_select.value:
            # For now just update labels or recalculate if needed
            self.previous_currency_id = self.currency_select.value
            ui.notify('Currency changed. Amounts shown are normalized.')

    def get_current_currency_symbol(self):
        selected_currency_id = self.currency_select.value
        for row in self.currency_rows:
            if row[0] == selected_currency_id:
                return row[2]
        return '$'

    def to_float(self, value):
        try:
            return round(float(value or 0), 2)
        except (TypeError, ValueError):
            return 0.0

    def calculate_customer_pending(self, customer_id):
        result = []
        sql = """
            SELECT SUM(COALESCE(total_amount, 0)) 
            FROM sales s 
            INNER JOIN customers c ON c.id = s.customer_id 
            WHERE c.id = ? AND s.payment_status = 'pending' AND COALESCE(s.total_amount, 0) > 0
        """
        connection.contogetrows(sql, result, (customer_id,))
        return self.to_float(result[0][0]) if result and result[0][0] is not None else 0.0

    async def refresh_history(self):
        async with loading_indicator.show_loading('refresh_receipts', 'Refreshing receipts...', overlay=True):
            data = []
            sql = """SELECT cr.id, cr.payment_date, c.customer_name, cr.amount, cr.payment_method, c.id as customer_id 
                     FROM customer_receipt cr
                     JOIN customers c ON cr.customer_id = c.id
                     ORDER BY cr.id DESC"""
            connection.contogetrows(sql, data)
            rows = []
            for r in data:
                rows.append({
                    'id': r[0],
                    'date': r[1],
                    'customer': r[2],
                    'amount': self.to_float(r[3]),
                    'method': r[4],
                    'customer_id': r[5],
                })
            self.history_grid.options['rowData'] = rows
            self.history_grid.update()
            await self.load_last_receipt()

    def clear_form(self, reset_customer=True):
        self.customer_input.value = ''
        self.balance_input.value = 0
        self.amount_input.value = 0
        self.method_select.value = 'Cash'
        self.selected_invoices = []
        self.draft_receipt_id = None
        self.draft_amount = 0.0
        if reset_customer:
            self.selected_customer = None
        self.total_display_input.value = '0.00'

    def exit_new_mode(self):
        self.new_mode = False
        self.history_overlay.set_visibility(False)
        self.history_grid.classes(remove='dimmed')

    def allocate_receipt_to_invoices(self, selected_rows, pay_amount):
        allocations = []
        remaining = round(pay_amount, 2)
        # Order by date, then ID
        ordered_rows = sorted(selected_rows, key=lambda row: (str(row.get('date') or ''), row.get('id') or 0))
        
        for row in ordered_rows:
            is_return = row.get('type') == 'Return'
            invoice_due = self.to_float(row.get('amount'))
            
            if is_return:
                # Returns are credits (negative in our UI), so they reduce the debt but increase the "remaining" to pay others
                # Actually, if we settle a return of $20, it's like we "used" the credit.
                # Let's say we have $100 invoice and $20 return. pay_amount is $80.
                # 1. Invoice $100: we pay $100? No, we pay min(100, 80 + 20) = 100.
                # It's better to think as: Credits items are "Negative Payment".
                pass
            
            if invoice_due == 0: continue
            
            # For simplicity in this logic: handle everything as a target to settle.
            # If amount is negative (Return), we settle it fully (which adds to our "remaining" capacity)
            settlement_amount = invoice_due if is_return else min(invoice_due, remaining)
            
            if abs(settlement_amount) > 0 or is_return:
                allocations.append({
                    'id': row['id'],
                    'type': row.get('type', 'Sale'),
                    'invoice_number': row['invoice_number'],
                    'date': row['date'],
                    'amount': invoice_due,
                    'settlement_amount': round(settlement_amount, 2),
                })
                if not is_return:
                    remaining = round(remaining - settlement_amount, 2)
                else:
                    # Settle the full return credit (which is negative), effectively ADDING to capacity
                    remaining = round(remaining - settlement_amount, 2) 

            if remaining <= 0 and not any(r.get('type') == 'Return' for r in ordered_rows[ordered_rows.index(row)+1:]):
                break
        return allocations

    def select_customer(self):
        with ui.dialog() as d, ModernCard().classes('w-full max-w-2xl p-6'):
            ui.label('Select Customer').classes('text-xl font-black mb-4 text-white')
            c_data = []
            connection.contogetrows("SELECT id, customer_name, balance FROM customers ORDER BY customer_name", c_data)
            c_rows = [{'id': r[0], 'name': r[1], 'balance': self.to_float(r[2])} for r in c_data]
            grid = ui.aggrid({
                'columnDefs': [
                    {'headerName': 'Name', 'field': 'name', 'flex': 1, 'filter': 'agTextColumnFilter', 'headerClass': 'blue-header'},
                    {'headerName': 'Balance', 'field': 'balance', 'width': 150, 'valueFormatter': '"$" + Number(params.value || 0).toLocaleString()', 'headerClass': 'blue-header'},
                ],
                'rowData': c_rows,
                'rowSelection': 'single',
                'defaultColDef': MDS.get_ag_grid_default_def(),
            }).classes('w-full h-80 ag-theme-quartz-dark')

            async def confirm():
                row = await grid.get_selected_row()
                if row:
                    self.selected_customer = {'id': row['id'], 'name': row['name'], 'balance': row['balance']}
                    self.customer_input.value = row['name']
                    pending = self.calculate_customer_pending(row['id'])
                    self.balance_input.value = pending
                    self.amount_input.value = '0.00'
                    self.selected_invoices = []
                    self.draft_amount = 0.0
                    self.total_display_input.value = '0.00'
                    d.close()
                    ui.notify('Customer selected', color='positive')

            with ui.row().classes('w-full justify-end mt-4 gap-2'):
                ModernButton('Cancel', on_click=d.close, variant='secondary')
                ModernButton('Select', on_click=confirm)
        d.open()

    def open_settlement_dialog(self):
        if not self.selected_customer:
            ui.notify('Select customer first', color='warning')
            return
        
        customer = self.selected_customer
        
        # Fetch Sales
        sales_invoices = []
        sql_sales = """
            SELECT s.id, s.invoice_number, s.total_amount, s.sale_date
            FROM sales s
            WHERE s.payment_status = 'pending' AND s.customer_id = ? AND COALESCE(s.total_amount, 0) > 0
            ORDER BY s.sale_date ASC, s.id ASC
        """
        connection.contogetrows(sql_sales, sales_invoices, (customer['id'],))
        
        # Fetch Returns
        returns_data = []
        sql_returns = """
            SELECT r.id, r.invoice_number, r.total_amount, r.return_date
            FROM sales_returns r
            WHERE r.payment_status = 'pending' AND r.customer_id = ? AND COALESCE(r.total_amount, 0) > 0
            ORDER BY r.return_date ASC, r.id ASC
        """
        connection.contogetrows(sql_returns, returns_data, (customer['id'],))

        rows = []
        for r in sales_invoices:
            rows.append({
                'id': r[0], 'invoice_number': r[1], 'amount': self.to_float(r[2]), 
                'date': str(r[3]), 'type': 'Sale', 'display_number': r[1]
            })
        for r in returns_data:
            rows.append({
                'id': r[0], 'invoice_number': r[1], 'amount': -self.to_float(r[2]), 
                'date': str(r[3]), 'type': 'Return', 'display_number': f"RET-{r[1]}"
            })

        if not rows:
            ui.notify('No pending records found', color='info')
            return

        with ui.dialog() as settlement_dialog, ModernCard().classes('w-full max-w-5xl p-8'):
            ui.label(f'Pending: {customer["name"]}').classes('text-2xl font-black mb-2 text-white')
            ui.label(f'Balance: ${self.calculate_customer_pending(customer["id"]):.2f}').classes('text-lg mb-4 text-green-400 font-bold')

            invoice_grid = ui.aggrid({
                'columnDefs': [
                    {'headerName': 'Select', 'checkboxSelection': True, 'headerCheckboxSelection': True, 'width': 80, 'headerClass': 'blue-header'},
                    {'headerName': 'Type', 'field': 'type', 'width': 100, 'headerClass': 'blue-header', 'cellClassRules': {'text-red-400': 'params.value === "Return"', 'text-green-400': 'params.value === "Sale"'}},
                    {'headerName': 'Ref #', 'field': 'display_number', 'flex': 1, 'headerClass': 'blue-header'},
                    {'headerName': 'Date', 'field': 'date', 'width': 130, 'headerClass': 'blue-header'},
                    {'headerName': 'Amount', 'field': 'amount', 'width': 130, 'valueFormatter': '"$" + Number(params.value || 0).toLocaleString()', 'headerClass': 'blue-header'},
                ],
                'rowData': rows,
                'rowSelection': 'multiple',
                'suppressRowClickSelection': True,
                'defaultColDef': MDS.get_ag_grid_default_def(),
            }).classes('w-full h-80 ag-theme-quartz-dark mb-6')

            with ui.row().classes('items-center gap-4 mb-4'):
                pay_amount_input = ui.number('Settlement Amount', value=sum(r['amount'] for r in rows)).classes('w-40')
                method_input = ui.select(['Cash', 'Card', 'Transfer', 'USD Cash'], value=self.method_select.value).classes('w-40')

            async def confirm_settlement():
                selected_rows = await invoice_grid.get_selected_rows()
                if not selected_rows: return ui.notify('Select at least one record', color='warning')
                pay_amount = self.to_float(pay_amount_input.value)
                # Note: pay_amount could be 0 if invoice and return cancel each other
                if pay_amount < 0: return ui.notify('Net amount cannot be negative', color='warning')
                
                allocations = self.allocate_receipt_to_invoices(selected_rows, pay_amount)
                self.selected_invoices = allocations
                self.draft_amount = pay_amount
                self.amount_input.value = f'{pay_amount:.2f}'
                self.total_display_input.value = f'{pay_amount:.2f}'
                self.method_select.value = method_input.value
                settlement_dialog.close()

            with ui.row().classes('w-full justify-end mt-4 gap-4'):
                ModernButton('Cancel', on_click=settlement_dialog.close, variant='secondary')
                ModernButton('OK', on_click=confirm_settlement)
        settlement_dialog.open()

    async def save_receipt(self):
        if not self.selected_customer or not self.new_mode:
            return ui.notify('New mode + Select customer', color='warning')

        async with loading_indicator.show_loading('save_receipt', 'Saving receipt...', overlay=True):
            try:
                pay_amount = self.to_float(self.amount_input.value)
                if pay_amount <= 0 or not self.selected_invoices:
                    return ui.notify('Amount > 0 + Select invoices', color='warning')

                # Normalization
                selected_currency_id = self.currency_select.value
                exchange_rate = float(self.currency_exchange_rates.get(selected_currency_id, 1.0))
                normalized_amount = round(pay_amount / exchange_rate, 2)
                
                receipt_date = self.date_input.value or datetime.now().strftime('%Y-%m-%d')
                user_id = session_storage.get('user')['user_id']

                # Fetch auxiliary number
                cust_aux_res = []
                connection.contogetrows("SELECT auxiliary_number FROM customers WHERE id = ?", cust_aux_res, (self.selected_customer['id'],))
                cust_aux = cust_aux_res[0][0] if cust_aux_res and cust_aux_res[0][0] else '4111.000001'

                # Standardized INSERT with auxiliary, user, and currency info
                sql_receipt = """
                    INSERT INTO customer_receipt 
                    (customer_id, amount, total_amount, payment_date, payment_method, auxiliary_number, user_id, currency_id, created_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
                """
                connection.insertingtodatabase(sql_receipt, (
                    self.selected_customer['id'], normalized_amount, pay_amount, 
                    receipt_date, self.method_select.value, cust_aux, user_id, selected_currency_id
                ))
                
                receipt_id = connection.getid("SELECT MAX(id) FROM customer_receipt", [])
                self.draft_receipt_id = receipt_id

                for alloc in self.selected_invoices:
                    # Invoices/Returns in DB are normalized (base currency)
                    norm_settlement = round(alloc['settlement_amount'] / exchange_rate, 2)
                    new_total = round(alloc['amount'] - norm_settlement, 2)
                    status = 'completed' if new_total == 0 else ('pending' if new_total > 0 else 'credit')
                    
                    if alloc['type'] == 'Return':
                        # Settlement for a return credit Note
                        connection.insertingtodatabase("UPDATE sales_returns SET total_amount = ?, payment_status = ? WHERE id = ?", (abs(new_total), status, alloc['id']))
                    else:
                        connection.insertingtodatabase("UPDATE sales SET total_amount = ?, payment_status = ? WHERE id = ?", (new_total, status, alloc['id']))
                    
                    # Record settlement details for robust "Undo/Delete"
                    connection.insertingtodatabase(
                        "INSERT INTO customer_receipt_details (receipt_id, source_type, source_id, settlement_amount) VALUES (?, ?, ?, ?)",
                        (receipt_id, alloc['type'], alloc['id'], alloc['settlement_amount'])
                    )

                connection.insertingtodatabase("UPDATE customers SET balance = balance - ? WHERE id = ?", (normalized_amount, self.selected_customer['id']))

                # Accounting - Use normalized amounts for the ledger (base currency)
                accounting_helpers.save_accounting_transaction('Receipt', str(receipt_id), [
                    {'account': '5300.000001', 'debit': normalized_amount, 'credit': 0},
                    {'account': cust_aux, 'debit': 0, 'credit': normalized_amount},
                ], description=f"Customer Receipt #{receipt_id} - {self.selected_customer['name']}")
                
                connection.update_cash_drawer_balance(normalized_amount, 'In', user_id, f"Receipt #{receipt_id}")

                ui.notify(f'Saved: {self.get_current_currency_symbol()}{pay_amount:.2f} (Normalized: ${normalized_amount:.2f})', color='positive')
                await self.refresh_history()
                self.exit_new_mode()
            except Exception as e:
                ui.notify(f'Error: {e}', color='negative')
                print(f"ERROR: {e}")

    async def delete_receipt(self):
        if not self.draft_receipt_id or self.new_mode:
            return ui.notify('Select a receipt from history first', color='warning')

        with ui.dialog() as d, ModernCard().classes('p-8 bg-slate-900 border border-red-500/30 shadow-2xl'):
            with ui.column().classes('w-full items-center gap-4'):
                ui.icon('warning', size='4rem', color='red')
                ui.label('Confirm Deletion').classes('text-2xl font-black text-white uppercase tracking-wider')
                ui.label(f'This will permanently delete Receipt #{self.draft_receipt_id} and revert all related invoice settlements.').classes('text-gray-400 text-center mb-4')
                
                with ui.row().classes('w-full justify-center gap-4'):
                    ModernButton('Cancel', on_click=d.close, variant='secondary').classes('w-32')
                    async def do_delete():
                        d.close()
                        async with loading_indicator.show_loading('delete_receipt', 'Reverting financial data...', overlay=True):
                            try:
                                # 1. Fetch receipt core info
                                res = []
                                connection.contogetrows("SELECT customer_id, amount, auxiliary_number FROM customer_receipt WHERE id = ?", res, (self.draft_receipt_id,))
                                if not res: return ui.notify('Receipt record not found')
                                cust_id, norm_amount, cust_aux = res[0]

                                # 2. Revert Settlements
                                settlements = []
                                connection.contogetrows("SELECT source_type, source_id, settlement_amount FROM customer_receipt_details WHERE receipt_id = ?", settlements, (self.draft_receipt_id,))
                                for s_type, s_id, s_amt in settlements:
                                    if s_type == 'Return':
                                        # abs(s_amt) because returns are stored negative in UI but positive in DB? 
                                        # Wait, in settlement_dialog I used -total_amount.
                                        # So if s_amt is -20, total_amount += -(-20) = +20. Correct.
                                        connection.insertingtodatabase("UPDATE sales_returns SET total_amount = total_amount + ?, payment_status = 'pending' WHERE id = ?", (abs(s_amt), s_id))
                                    else:
                                        connection.insertingtodatabase("UPDATE sales SET total_amount = total_amount + ?, payment_status = 'pending' WHERE id = ?", (s_amt, s_id))

                                # 3. Revert Customer Balance
                                connection.insertingtodatabase("UPDATE customers SET balance = balance + ? WHERE id = ?", (norm_amount, cust_id))

                                # 4. Reverse Cash Drawer
                                user_id = session_storage.get('user')['user_id']
                                connection.update_cash_drawer_balance(norm_amount, 'Out', user_id, f"Delete Receipt #{self.draft_receipt_id}")

                                # 5. Remove Accounting Transactions
                                accounting_helpers.save_accounting_transaction('Receipt', str(self.draft_receipt_id), [])

                                # 6. Clean up records
                                connection.insertingtodatabase("DELETE FROM customer_receipt_details WHERE receipt_id = ?", (self.draft_receipt_id,))
                                connection.insertingtodatabase("DELETE FROM customer_receipt WHERE id = ?", (self.draft_receipt_id,))

                                ui.notify(f'Receipt #{self.draft_receipt_id} deleted successfully', color='positive')
                                await self.refresh_history()
                                self.clear_form()
                            except Exception as ex:
                                ui.notify(f'Delete Error: {ex}', color='negative')
                    ModernButton('Delete Forever', on_click=do_delete, variant='error').classes('w-48')
        d.open()

    async def load_last_receipt(self):
        await asyncio.sleep(0.1)
        if self.history_grid.options.get('rowData'):
            await self.perform_load_row(self.history_grid.options['rowData'][0])

    async def perform_load_row(self, row_data):
        self.exit_new_mode()
        self.selected_customer = {'id': row_data['customer_id'], 'name': row_data['customer']}
        self.customer_input.value = row_data['customer']
        self.amount_input.value = f'{row_data["amount"]:.2f}'
        self.method_select.value = row_data['method']
        self.total_display_input.value = f'{row_data["amount"]:.2f}'
        self.balance_input.value = self.calculate_customer_pending(row_data['customer_id'])

    def filter_history_table(self, query):
        target_query = str(query or "").lower()
        if not target_query:
            self.history_grid.options['rowData'] = getattr(self, 'all_data', [])
        else:
            self.history_grid.options['rowData'] = [r for r in getattr(self, 'all_data', []) if target_query in str(r['customer']).lower() or target_query in str(r['id']).lower()]
        self.history_grid.update()

    def create_ui(self):
        ui.add_head_html(MDS.get_global_styles())
        
        with ui.element('div').classes('w-full mesh-gradient h-[calc(100vh-64px)] p-0 overflow-hidden'):
            with ui.row().classes('w-full h-full gap-0 overflow-hidden'):
                # MAIN CONTENT
                with ui.column().classes('flex-1 h-full p-4 gap-4 relative overflow-hidden'):
                    # HEADER
                    with ui.row().classes('w-full justify-between items-center bg-white/5 p-4 rounded-3xl glass border border-white/10 mb-2'):
                        with ui.column().classes('gap-1'):
                            ui.label('Commerce Engine').classes('text-xs font-black uppercase tracking-[0.2em] text-purple-400')
                            ui.label('Customer Receipt').classes('text-3xl font-black text-white').style('font-family: "Outfit", sans-serif;')
                        
                        with ui.row().classes('gap-6 items-center'):
                            with ui.row().classes('items-center gap-2 bg-white/5 px-4 py-2 rounded-xl border border-white/10'):
                                ui.icon('event', size='1rem').classes('text-gray-400')
                                self.date_input = ui.input(value=datetime.now().strftime('%Y-%m-%d')).props('borderless dense').classes('text-white text-xs font-bold w-24')
                            self.currency_select = ui.select({r[0]: f"{r[2]} {r[1]}" for r in self.currency_rows}, value=self.default_currency_id).props('borderless dense').classes('glass px-4 py-2 rounded-xl text-white text-xs font-bold w-40').on('change', self.on_currency_change)

                    # DUAL PANEL
                    with ui.row().classes('w-full flex-1 gap-6 overflow-hidden'):
                        # LEFT: History
                        with ui.column().classes('w-[35%] h-full gap-4'):
                            with ui.column().classes('w-full h-full glass p-3 rounded-3xl border border-white/10'):
                                with ui.row().classes('w-full items-center gap-3 glass p-3 rounded-2xl border border-white/10 hover:bg-white/5 mb-2'):
                                    ui.icon('history', size='1.25rem').classes('text-purple-400 ml-1')
                                    self.history_search = ui.input(placeholder='Search history...').props('borderless dense clearable dark').classes('flex-1 text-white font-bold').on_value_change(lambda e: self.filter_history_table(e.value))
                                
                                self.history_grid = ui.aggrid({
                                    'columnDefs': [
                                        {'headerName': 'ID', 'field': 'id', 'width': 70, 'headerClass': 'blue-header'},
                                        {'headerName': 'Date', 'field': 'date', 'width': 110, 'headerClass': 'blue-header'},
                                        {'headerName': 'Customer', 'field': 'customer', 'flex': 1, 'headerClass': 'blue-header'},
                                        {'headerName': 'Amount', 'field': 'amount', 'width': 100, 'headerClass': 'blue-header'},
                                    ],
                                    'rowData': [],
                                    'rowSelection': 'single',
                                    'pagination': True,
                                    'paginationPageSize': 15,
                                    'domLayout': 'normal',
                                }).classes('w-full flex-1 ag-theme-quartz-dark shadow-inner').style('background: transparent; border: none;')
                                
                                self.history_grid.on('cellClicked', lambda e: self.perform_load_row(e.args['data']))

                                self.history_overlay = ui.element('div').classes('absolute inset-0 bg-black/60 flex items-center justify-center z-20 text-white text-center p-6').style('backdrop-filter: blur(4px); pointer-events: none;')
                                with self.history_overlay:
                                    ui.label('🆕 NEW RECEIPT MODE\nClick Customer, then Amount to allocate invoices').classes('font-black text-xl whitespace-pre-wrap')
                                self.history_overlay.set_visibility(False)

                        # RIGHT: Editor
                        with ui.column().classes('flex-1 h-full gap-4'):
                            with ModernCard(glass=True).classes('w-full p-8 rounded-3xl border border-white/10'):
                                ui.label('COLLECTION DETAILS').classes('text-[10px] font-black text-purple-400 tracking-widest mb-6 opacity-60')
                                with ui.column().classes('w-full gap-6'):
                                    with ui.column().classes('w-full gap-1'):
                                        ui.label('Customer Account').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                        with ui.row().classes('items-center gap-3 bg-white/5 px-5 py-3 rounded-2xl border border-white/10 w-full hover:bg-white/10 transition-all cursor-pointer shadow-inner'):
                                            ui.icon('person', size='1.5rem').classes('text-purple-400')
                                            self.customer_input = ui.input(placeholder='Select Customer Account...').props('borderless dense dark readonly').classes('flex-1 text-white font-black text-lg').on('click', self.select_customer)
                                    
                                    with ui.row().classes('w-full gap-4'):
                                        with ui.column().classes('flex-1 gap-1'):
                                            ui.label('Pending Balance').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                            with ui.row().classes('items-center gap-3 bg-white/5 px-5 py-3 rounded-2xl border border-white/10 w-full'):
                                                ui.icon('receipt_long', size='1.5rem').classes('text-gray-500 opacity-50')
                                                self.balance_input = ui.number(value=0, format='%.2f').props('borderless dense dark readonly').classes('flex-1 text-white font-black text-lg')
                                        
                                        with ui.column().classes('flex-1 gap-1'):
                                            ui.label('Receipt Amount').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                            with ui.row().classes('items-center gap-3 bg-white/5 px-5 py-3 rounded-2xl border border-white/10 w-full hover:bg-white/10 transition-all cursor-pointer'):
                                                ui.icon('payments', size='1.5rem').classes('text-green-400')
                                                self.amount_input = ui.input(value='0.00').props('borderless dense dark readonly').classes('flex-1 text-white font-black text-lg').on('click', self.open_settlement_dialog)
                                                ui.button(icon='open_in_new', on_click=self.open_settlement_dialog).props('flat round color=purple')
                                    
                                    with ui.row().classes('w-full gap-4'):
                                        with ui.column().classes('flex-1 gap-1'):
                                            ui.label('Payment Method').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                            self.method_select = ui.select(['Cash', 'Card', 'Transfer', 'USD Cash'], value='Cash').props('borderless dense dark').classes('bg-white/5 px-5 py-3 rounded-2xl border border-white/10 w-full text-white font-black')
                                        
                                        with ui.column().classes('flex-1 gap-1'):
                                            ui.label('Selected for Settlement').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                            with ui.row().classes('items-center gap-3 bg-white/5 px-5 py-3 rounded-2xl border border-white/10 w-full'):
                                                ui.icon('summarize', size='1.5rem').classes('text-blue-400')
                                                self.total_display_input = ui.input(value='0.00').props('borderless dense dark readonly').classes('flex-1 text-white font-black text-lg')

                # ACTION BAR
                with ui.column().classes('w-[80px] items-center py-4'):
                    def handle_new():
                        self.clear_form()
                        self.new_mode = True
                        self.history_overlay.set_visibility(True)
                        self.history_grid.classes('dimmed')
                        ui.notify('New Receipt Mode', color='positive')

                    ModernActionBar(
                        on_new=handle_new,
                        on_save=self.save_receipt,
                        on_undo=lambda: [self.clear_form(), self.exit_new_mode()],
                        on_delete=self.delete_receipt,
                        on_refresh=self.refresh_history,
                        on_chatgpt=lambda: ui.run_javascript('window.open("https://chatgpt.com", "_blank");'),
                        on_view_transaction=lambda: accounting_helpers.show_transactions_dialog('Receipt', self.draft_receipt_id) if self.draft_receipt_id else ui.notify('No receipt selected'),
                        button_class='h-16',
                    ).style('position: static; width: 80px; border-radius: 20px; box-shadow: 0 20px 50px rgba(0,0,0,0.3);')

        ui.timer(0.1, self.refresh_history, once=True)

@ui.page('/customerreceipt')
def customer_receipt_page_route():
    CustomerReceiptUI()