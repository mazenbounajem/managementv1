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

        self._ensure_customer_receipt_details_table()

        # Ensure reference column exists
        try:
            connection.insertingtodatabase("ALTER TABLE customer_receipt ADD reference NVARCHAR(100) NULL")
        except Exception:
            pass

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
        self._selected_row_index = None
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
        if self.previous_currency_id != self.currency_select.value:
            self.previous_currency_id = self.currency_select.value
            ui.notify('Currency changed. Amounts shown are normalized.')
        if hasattr(self, 'customer_currency_label'):
            try:
                self.customer_currency_label.text = self.get_current_currency_symbol() + ' ' + str(self.currency_select.value)
            except Exception:
                pass

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
            SELECT
                ISNULL((SELECT SUM(COALESCE(total_amount, 0)) FROM sales WHERE customer_id = ? AND payment_status = 'pending' AND COALESCE(total_amount, 0) > 0), 0)
                -
                ISNULL((SELECT SUM(COALESCE(total_amount, 0)) FROM sales_returns WHERE customer_id = ? AND payment_status = 'pending' AND COALESCE(total_amount, 0) > 0), 0)
        """
        connection.contogetrows(sql, result, (customer_id, customer_id))
        return self.to_float(result[0][0]) if result and result[0][0] is not None else 0.0

    async def refresh_history(self):
        async with loading_indicator.show_loading('refresh_receipts', 'Refreshing receipts...', overlay=True):
            data = []
            sql = """SELECT cr.id, cr.payment_date, c.customer_name, cr.amount, cr.payment_method, c.id as customer_id, ISNULL(cr.reference, '') as reference 
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
                    'reference': r[6],
                })
            self._all_receipt_data = rows
            self.history_table.rows = rows
            self.history_table.update()
            await self.load_last_receipt()

    def clear_form(self, reset_customer=True):
        self.customer_input.value = ''
        self.reference_input.value = ''
        self.balance_input.value = 0
        self.amount_input.value = 0
        self.method_select.value = 'Cash'
        self.selected_invoices = []
        self.draft_receipt_id = None
        self.draft_amount = 0.0
        if reset_customer:
            self.selected_customer = None
        self.total_display_input.value = '0.00'
        self._selected_row_index = None

    def exit_new_mode(self):
        self.new_mode = False
        self.history_overlay.set_visibility(False)
        self.history_table.classes(remove='dimmed')
        if hasattr(self, 'action_bar'):
            self.action_bar.reset_state()

    def _ensure_customer_receipt_details_table(self):
        try:
            connection.insertingtodatabase(
                """
                IF NOT EXISTS (
                    SELECT 1 FROM sys.tables WHERE name = 'customer_receipt_details'
                )
                CREATE TABLE customer_receipt_details (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    payment_id INT NOT NULL,
                    source_type NVARCHAR(20) NOT NULL,
                    source_id INT NOT NULL,
                    settlement_amount DECIMAL(18, 2) NOT NULL,
                    settlement_amount_display DECIMAL(18, 2) NULL
                )
                """
            )

            connection.insertingtodatabase(
                """
                IF COL_LENGTH('customer_receipt_details','settlement_amount_display') IS NULL
                BEGIN
                    ALTER TABLE customer_receipt_details
                    ADD settlement_amount_display DECIMAL(18,2) NULL;
                END
                """
            )
        except Exception as e:
            ui.notify(f'Error ensuring customer_receipt_details table: {e}', color='negative')

    def allocate_receipt_to_invoices(self, selected_rows, pay_amount):
        allocations = []
        remaining = round(pay_amount, 2)

        ordered_rows = sorted(
            selected_rows,
            key=lambda row: (0 if row.get('type') == 'Return' else 1, str(row.get('date') or ''), row.get('id') or 0)
        )

        for idx, row in enumerate(ordered_rows):
            is_return = row.get('type') == 'Return'
            invoice_due = self.to_float(row.get('amount'))

            if invoice_due == 0:
                continue

            settlement_amount = invoice_due if is_return else min(invoice_due, remaining)

            if abs(settlement_amount) > 0 or is_return:
                allocations.append({
                    'id': row['id'],
                    'type': row.get('type', 'Sale'),
                    'invoice_number': row.get('invoice_number'),
                    'date': row.get('date'),
                    'amount': invoice_due,
                    'settlement_amount': round(settlement_amount, 2),
                })

                remaining = round(remaining - settlement_amount, 2)

            if remaining <= 0 and not any(r.get('type') == 'Return' for r in ordered_rows[idx + 1:]):
                break

        return allocations

    def select_customer(self):
        c_data = []
        connection.contogetrows(
            "SELECT id, customer_name, phone, balance FROM customers ORDER BY customer_name",
            c_data
        )
        all_customer_rows = [
            {'id': r[0], 'name': r[1], 'phone': r[2], 'balance': self.to_float(r[3])}
            for r in c_data
        ]

        _selected_row = None
        state = {'selected_idx': 0}

        with ui.dialog() as d, ModernCard().classes('w-full max-w-2xl p-6'):
            ui.label('Select Customer').classes('text-xl font-black mb-4 text-white')

            with ui.row().classes('w-full items-center gap-3 bg-white/5 px-4 py-2 rounded-xl border border-white/10 mb-4'):
                ui.icon('search', size='1.25rem').classes('text-purple-400')
                search_query_input = ui.input(placeholder='Search by name or phone...').props('borderless dense').classes('flex-1 text-white text-sm')

            with ui.element('div').classes('w-full h-80 overflow-hidden flex flex-col'):
                with ui.element('div').classes('flex-1 overflow-auto min-h-0'):
                    customer_table = ui.table(
                        columns=[
                            {'name': 'name', 'label': 'Name', 'field': 'name', 'align': 'left', 'sortable': True},
                            {'name': 'phone', 'label': 'Phone', 'field': 'phone', 'align': 'left'},
                            {'name': 'balance', 'label': 'Balance', 'field': 'balance', 'align': 'right'},
                        ],
                        rows=all_customer_rows,
                        row_key='id',
                        selection='single',
                    ).classes('w-full h-full bg-transparent overflow-hidden').props('virtual-scroll flat bordered dense hide-pagination :pagination="{rowsPerPage: 0}"')

            def apply_highlight_js():
                idx = state['selected_idx']
                ui.run_javascript(f"""
                    try {{
                      const root = document.getElementById('{getattr(customer_table, "id", "")}') || document.querySelector('.q-table');
                      if (!root) return;
                      const rows = root.querySelectorAll('tbody tr');
                      if (!rows || rows.length === 0) return;

                      const target = Math.max(0, Math.min({idx} + 1, rows.length - 1));

                      rows.forEach(el => {{
                        el.style.backgroundColor = '';
                        el.style.color = '';
                        el.classList.remove('selected-highlight');
                      }});

                      const selected = rows[target];
                      if (selected) {{
                        selected.style.backgroundColor = '#facc15';
                        selected.style.color = 'black';
                        selected.classList.add('selected-highlight');
                      }}
                    }} catch (e) {{ console.error('Highlight error:', e); }}
                """)

            def select_and_scroll():
                if not customer_table.rows:
                    return
                state['selected_idx'] = max(0, min(state['selected_idx'], len(customer_table.rows) - 1))
                row = customer_table.rows[state['selected_idx']]
                customer_table.selected = [row]
                customer_table.update()
                customer_table.run_method('scrollTo', state['selected_idx'])
                apply_highlight_js()

            def confirm_with_row(row_data):
                self.selected_customer = {'id': row_data['id'], 'name': row_data['name'], 'balance': row_data['balance']}
                self.customer_input.value = row_data['name']
                pending = self.calculate_customer_pending(row_data['id'])
                self.balance_input.value = pending
                self.amount_input.value = '0.00'
                self.selected_invoices = []
                self.draft_amount = 0.0
                self.total_display_input.value = '0.00'

                if hasattr(self, 'customer_date_label'):
                    try:
                        self.customer_date_label.text = str(self.date_input.value or datetime.now().strftime('%Y-%m-%d'))
                    except Exception:
                        pass
                if hasattr(self, 'customer_currency_label'):
                    try:
                        self.customer_currency_label.text = self.get_current_currency_symbol() + ' ' + str(self.currency_select.value)
                    except Exception:
                        pass

                ui.run_javascript('window.__customer_dialog_active = false;')
                d.close()
                ui.notify('Customer selected', color='positive')

            def on_click_row(e):
                nonlocal _selected_row
                try:
                    args = e.args if hasattr(e, 'args') else e
                    row_data = None
                    if isinstance(args, (list, tuple)):
                        for candidate in args:
                            if isinstance(candidate, dict) and 'name' in candidate:
                                row_data = candidate
                                break
                        if row_data is None and len(args) > 1 and isinstance(args[1], dict):
                            row_data = args[1]
                    elif isinstance(args, dict):
                        row_data = args.get('row') or args.get('data') or (args if 'name' in args else None)

                    if not isinstance(row_data, dict):
                        return

                    if customer_table.rows:
                        for i, r in enumerate(customer_table.rows):
                            if r.get('id') == row_data.get('id'):
                                state['selected_idx'] = i
                                break
                        apply_highlight_js()

                    _selected_row = row_data
                    confirm_with_row(row_data)
                except Exception as ex:
                    ui.notify(f'Row selection error: {ex}', color='negative')

            customer_table.on('row-click', on_click_row)

            ui.timer(0.05, select_and_scroll, once=True)

            grid_id = getattr(customer_table, 'id', '')
            search_id = getattr(search_query_input, 'id', '')
            ui.run_javascript(f"""
                window.__customer_dialog_active = true;
                try {{
                  const root = document.getElementById('{grid_id}') || document.querySelector('.q-table');
                  if (root) {{
                    root.tabIndex = 0;
                    try {{ root.style.outline = 'none'; }} catch(e) {{}}
                    try {{ root.style.caretColor = 'transparent'; }} catch(e) {{}}

                    try {{ root.dataset.selIdx = '-1'; }} catch(e) {{}}

                    root.addEventListener('keydown', (ev) => {{
                      if (!window.__customer_dialog_active) return;
                      if (ev.key !== 'ArrowDown' && ev.key !== 'ArrowUp' && ev.key !== 'PageDown' && ev.key !== 'PageUp' && ev.key !== 'Enter') return;

                      const rows = root.querySelectorAll('tbody tr');
                      if (!rows || rows.length === 0) return;

                      let cur = parseInt(root.dataset.selIdx || '-1', 10);
                      if (isNaN(cur)) cur = -1;

                      if (ev.key === 'ArrowUp' && cur === 0) {{
                        ev.preventDefault();
                        const searchEl = document.getElementById('{search_id}');
                        const input = searchEl ? searchEl.querySelector('input') : null;
                        if (input) {{
                          input.focus();
                          return;
                        }}
                      }}

                      ev.preventDefault();

                      const pageStep = 10;

                      if (ev.key === 'ArrowDown') cur = Math.min((cur < 0 ? -1 : cur) + 1, rows.length - 1);
                      if (ev.key === 'ArrowUp') cur = Math.max((cur < 0 ? 0 : cur) - 1, 0);
                      if (ev.key === 'PageDown') cur = Math.min((cur < 0 ? 0 : cur) + pageStep, rows.length - 1);
                      if (ev.key === 'PageUp') cur = Math.max((cur < 0 ? 0 : cur) - pageStep, 0);

                      if (ev.key === 'Enter') {{
                        if (cur < 0) cur = 0;
                      }}

                      root.dataset.selIdx = cur;

                      rows.forEach(el => {{
                        el.style.backgroundColor = '';
                        el.style.color = '';
                        el.classList.remove('selected-highlight');
                      }});
                      const selected = rows[cur];
                      if (selected) {{
                        selected.style.backgroundColor = '#facc15';
                        selected.style.color = 'black';
                        selected.classList.add('selected-highlight');
                      }}

                      if (ev.key === 'Enter') {{
                        selected && selected.click();
                      }}
                    }});
                  }}
                }} catch (e) {{}}

                try {{
                  const searchEl = document.getElementById('{search_id}');
                  const input = searchEl ? searchEl.querySelector('input') : null;
                  if (input) {{
                    input.addEventListener('keydown', (ev) => {{
                      if (!window.__customer_dialog_active) return;
                      if (ev.key === 'ArrowDown') {{
                        ev.preventDefault();
                        ev.stopPropagation();
                        const root = document.getElementById('{grid_id}') || document.querySelector('.q-table');
                        if (root) {{
                          root.dataset.selIdx = '-1';
                          root.focus();
                          setTimeout(() => {{
                            root.dispatchEvent(new KeyboardEvent('keydown', {{key: 'ArrowDown', bubbles: true, cancelable: true}}));
                          }}, 0);
                        }}
                      }} else if (ev.key === 'Enter') {{
                        ev.preventDefault();
                        ev.stopPropagation();
                        const root = document.getElementById('{grid_id}') || document.querySelector('.q-table');
                        if (root) {{
                          const rows = root.querySelectorAll('tbody tr');
                          let cur = parseInt(root.dataset.selIdx || '0', 10);
                          if (cur < 0) cur = 0;
                          const selected = rows[cur];
                          if (selected) {{
                            selected.click();
                          }}
                        }}
                      }}
                    }});
                  }}
                }} catch (e) {{}}
            """)

            def apply_search(e=None):
                nonlocal _selected_row
                q = str(search_query_input.value or '').strip().lower()
                if not q:
                    customer_table.rows = all_customer_rows
                else:
                    customer_table.rows = [
                        r for r in all_customer_rows
                        if q in str(r.get('name', '')).lower()
                        or q in str(r.get('phone', '')).lower()
                        or q in str(r.get('id', '')).lower()
                    ]
                _selected_row = None
                customer_table.selected = []
                customer_table.update()
                try:
                    ui.run_javascript(f"""
                        try {{
                          const root = document.getElementById('{grid_id}') || document.querySelector('.q-table');
                          if (!root) return;
                          root.dataset.selIdx = '-1';
                        }} catch(e) {{}}
                    """)
                except Exception:
                    pass

            search_query_input.on_value_change(apply_search)

            with ui.row().classes('w-full justify-end mt-4 gap-2'):
                ModernButton('Cancel', on_click=lambda: (ui.run_javascript('window.__customer_dialog_active=false;'), d.close()), variant='secondary')
        d.open()

    def open_settlement_dialog(self):
        if not self.selected_customer:
            ui.notify('Select customer first', color='warning')
            return
        
        customer = self.selected_customer
        
        sales_invoices = []
        sql_sales = """
            SELECT s.id, s.invoice_number, s.total_amount, s.sale_date
            FROM sales s
            WHERE s.payment_status = 'pending' AND s.customer_id = ? AND COALESCE(s.total_amount, 0) > 0
            ORDER BY s.sale_date ASC, s.id ASC
        """
        connection.contogetrows(sql_sales, sales_invoices, (customer['id'],))
        
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
            ui.label(f'Balance: ${self.calculate_customer_pending(customer["id"]):,.2f}').classes('text-lg mb-4 text-green-400 font-bold')

            invoice_table = ui.table(
                columns=[
                    {'name': 'type', 'label': 'Type', 'field': 'type', 'align': 'left', 'sortable': True},
                    {'name': 'display_number', 'label': 'Ref #', 'field': 'display_number', 'align': 'left', 'sortable': True},
                    {'name': 'date', 'label': 'Date', 'field': 'date', 'align': 'left', 'sortable': True},
                    {'name': 'amount', 'label': 'Amount', 'field': 'amount', 'align': 'right', 'sortable': True},
                ],
                rows=rows,
                row_key='id',
                selection='multiple',
            ).classes('w-full h-80 mb-6')

            with ui.row().classes('items-center gap-4 mb-4'):
                pay_amount_input = ui.number('Settlement Amount', value=sum(r['amount'] for r in rows)).classes('w-40')
                method_input = ui.select(['Cash', 'Card', 'Transfer', 'USD Cash'], value=self.method_select.value).classes('w-40')

            async def confirm_settlement():
                selected_rows = invoice_table.selected
                if not selected_rows: return ui.notify('Select at least one record', color='warning')
                pay_amount = self.to_float(pay_amount_input.value)
                if pay_amount < 0: return ui.notify('Net amount cannot be negative', color='warning')
                
                allocations = self.allocate_receipt_to_invoices(selected_rows, pay_amount)
                self.selected_invoices = allocations
                self.draft_amount = pay_amount
                self.amount_input.value = f'{pay_amount:,.2f}'
                self.total_display_input.value = f'{pay_amount:,.2f}'
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
                if pay_amount < 0 or not self.selected_invoices:
                    return ui.notify('Amount must be >= 0 + Select invoices', color='warning')

                selected_currency_id = self.currency_select.value
                exchange_rate = float(self.currency_exchange_rates.get(selected_currency_id, 1.0))
                normalized_amount = round(pay_amount / exchange_rate, 2)

                receipt_date = self.date_input.value or datetime.now().strftime('%Y-%m-%d')

                import accounting_helpers
                cust_aux = accounting_helpers.ensure_customer_auxiliary(
                    self.selected_customer['id'],
                    customer_name=self.selected_customer.get('name'),
                    fallback_account_number='4111'
                )

                reference = self.reference_input.value or ''
                sql_receipt = """
                    INSERT INTO customer_receipt
                    (customer_id, amount, total_amount, payment_date, payment_method, status, created_at, reference)
                    VALUES (?, ?, ?, ?, ?, 'completed', GETDATE(), ?)
                """
                connection.insertingtodatabase(sql_receipt, (
                    self.selected_customer['id'], normalized_amount, pay_amount,
                    receipt_date, self.method_select.value, reference
                ))
                
                receipt_id = connection.getid("SELECT MAX(id) FROM customer_receipt", [])
                self.draft_receipt_id = receipt_id

                for alloc in self.selected_invoices:
                    settlement_display = round(float(alloc['settlement_amount']), 2)
                    settlement_base = round(settlement_display / exchange_rate, 2)

                    new_total_base = round(float(alloc['amount']) - settlement_base, 2)

                    status = 'completed' if new_total_base == 0 else ('pending' if new_total_base > 0 else 'credit')

                    if alloc['type'] == 'Return':
                        connection.insertingtodatabase(
                            "UPDATE sales_returns SET total_amount = ?, payment_status = ? WHERE id = ?",
                            (abs(new_total_base), status, alloc['id'])
                        )
                    else:
                        connection.insertingtodatabase(
                            "UPDATE sales SET total_amount = ?, payment_status = ? WHERE id = ?",
                            (new_total_base, status, alloc['id'])
                        )

                    connection.insertingtodatabase(
                        """
                        INSERT INTO customer_receipt_details
                        (payment_id, source_type, source_id, settlement_amount, settlement_amount_display)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (receipt_id, alloc['type'], alloc['id'], settlement_base, settlement_display)
                    )

                connection.insertingtodatabase(
                    "UPDATE customers SET balance = balance - ? WHERE id = ?",
                    (normalized_amount, self.selected_customer['id'])
                )

                import business_track_settings
                payment_cash_account = '5300.000001'
                accounting_helpers.save_accounting_transaction(
                    'Receipt',
                    str(receipt_id),
                    [
                        {'account': cust_aux, 'debit': 0, 'credit': normalized_amount},
                        {'account': payment_cash_account, 'debit': normalized_amount, 'credit': 0},
                    ],
                    description=f"Customer {self.method_select.value} Receipt #{receipt_id} - {self.selected_customer['name']}"
                )

                user_id = session_storage.get('user')['user_id']
                connection.update_cash_drawer_balance(normalized_amount, 'In', user_id, f"Receipt #{receipt_id}")

                ui.notify(f'Saved: {self.get_current_currency_symbol()}{pay_amount:,.2f} (Normalized: ${normalized_amount:,.2f})', color='positive')
                await self.refresh_history()
                self.exit_new_mode()
                await self.show_receipt_print_dialog(receipt_id, self.selected_customer['name'], pay_amount, self.method_select.value, self.selected_customer['id'])
            except Exception as e:
                ui.notify(f'Error: {e}', color='negative')
                print(f"ERROR: {e}")

    async def show_receipt_print_dialog(self, payment_id, customer_name, amount, method, customer_id):
        remaining = self.calculate_customer_pending(customer_id)
        from print_helper import print_dialog_content

        # Fetch settlement details
        alloc_data = []
        connection.contogetrows("""
            SELECT d.source_type, d.settlement_amount_display,
                   s.invoice_number AS sales_inv, r.invoice_number AS return_inv
            FROM customer_receipt_details d
            LEFT JOIN sales s ON d.source_type = 'Sale' AND s.id = d.source_id
            LEFT JOIN sales_returns r ON d.source_type = 'Return' AND r.id = d.source_id
            WHERE d.payment_id = ?
            ORDER BY d.id ASC
        """, alloc_data, (payment_id,))
        alloc_rows = []
        for src_type, s_amt, s_inv, r_inv in alloc_data:
            alloc_rows.append({
                'type': src_type,
                'invoice': s_inv if src_type == 'Sale' else r_inv,
                'amount': self.to_float(s_amt),
            })

        ui.add_head_html('<style> @media print { .q-dialog__inner > div { max-width: none !important; width: 100% !important; background: white !important; color: black !important; } .hide-on-print { display: none !important; } .text-white, .text-gray-400, .text-green-400, .text-orange-400, .text-purple-400 { color: black !important; } [class*="bg-"] { background: white !important; } } </style>')
        with ui.dialog() as d, ModernCard().classes('w-full max-w-lg p-8'):
            with ui.column().classes('w-full items-center gap-6'):
                with ui.column().classes('w-full items-center gap-1'):
                    ui.label('RECEIPT').classes('text-[10px] font-black tracking-[0.3em] text-purple-400')
                    ui.label(f'#{payment_id}').classes('text-4xl font-black text-white')

                with ui.column().classes('w-full bg-white/5 rounded-2xl p-6 gap-4 border border-white/10'):
                    with ui.row().classes('w-full justify-between'):
                        ui.label('Customer').classes('text-sm text-gray-400')
                        ui.label(customer_name).classes('text-sm text-white font-bold')
                    with ui.row().classes('w-full justify-between'):
                        ui.label('Date').classes('text-sm text-gray-400')
                        ui.label(datetime.now().strftime('%Y-%m-%d %H:%M')).classes('text-sm text-white font-bold')
                    with ui.row().classes('w-full justify-between'):
                        ui.label('Amount Paid').classes('text-sm text-gray-400')
                        ui.label(f'${amount:,.2f}').classes('text-lg text-green-400 font-black')
                    with ui.row().classes('w-full justify-between'):
                        ui.label('Method').classes('text-sm text-gray-400')
                        ui.label(method).classes('text-sm text-white font-bold')

                    if alloc_rows:
                        ui.element('div').classes('w-full h-px bg-white/20 my-1')
                        ui.label('SETTLEMENT DETAILS').classes('text-[8px] font-black text-purple-400/60 uppercase tracking-widest')
                        for ar in alloc_rows:
                            with ui.row().classes('w-full justify-between'):
                                ui.label(f"{ar['type']} #{ar['invoice']}").classes('text-xs text-gray-400')
                                ui.label(f"${ar['amount']:,.2f}").classes('text-xs text-white font-bold')

                    with ui.row().classes('w-full justify-between pt-3 border-t border-white/10'):
                        ui.label('Remaining Balance').classes('text-sm text-gray-400')
                        ui.label(f'${remaining:,.2f}').classes('text-lg text-orange-400 font-black' if remaining > 0 else 'text-lg text-green-400 font-black')

                with ui.row().classes('w-full justify-center gap-4 hide-on-print'):
                    ui.button('PRINT', icon='print', on_click=lambda: ui.run_javascript(print_dialog_content())).props('flat color=purple-400').classes('font-black')
                    ui.button('CLOSE', icon='close', on_click=d.close).props('flat color=red').classes('font-black')
        d.open()

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
                                res = []
                                connection.contogetrows("SELECT customer_id, amount FROM customer_receipt WHERE id = ?", res, (self.draft_receipt_id,))
                                if not res: return ui.notify('Receipt record not found')
                                cust_id, norm_amount = res[0]

                                settlements = []
                                connection.contogetrows(
                                    "SELECT source_type, source_id, settlement_amount FROM customer_receipt_details WHERE payment_id = ?",
                                    settlements,
                                    (self.draft_receipt_id,)
                                )

                                for s_type, s_id, s_amt in settlements:
                                    s_amt = self.to_float(s_amt)
                                    if s_type == 'Return':
                                        connection.insertingtodatabase(
                                            "UPDATE sales_returns SET total_amount = total_amount + ?, payment_status = 'pending' WHERE id = ?",
                                            (abs(s_amt), s_id)
                                        )
                                    else:
                                        connection.insertingtodatabase(
                                            "UPDATE sales SET total_amount = total_amount + ?, payment_status = 'pending' WHERE id = ?",
                                            (s_amt, s_id)
                                        )

                                connection.insertingtodatabase(
                                    "UPDATE customers SET balance = balance + ? WHERE id = ?",
                                    (norm_amount, cust_id)
                                )

                                user_id = session_storage.get('user')['user_id']
                                connection.update_cash_drawer_balance(norm_amount, 'Out', user_id, f"Delete Receipt #{self.draft_receipt_id}")

                                accounting_helpers.save_accounting_transaction('Receipt', str(self.draft_receipt_id), [])

                                connection.insertingtodatabase(
                                    "DELETE FROM customer_receipt_details WHERE payment_id = ?",
                                    (self.draft_receipt_id,)
                                )
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
        if self.history_table.rows:
            await self.perform_load_row(self.history_table.rows[0])

    async def perform_load_row(self, row_data):
        self.exit_new_mode()
        if hasattr(self, 'action_bar'):
            self.action_bar.enter_edit_mode()
        self.draft_receipt_id = row_data['id']
        self.selected_customer = {'id': row_data['customer_id'], 'name': row_data['customer']}
        self.customer_input.value = row_data['customer']
        self.amount_input.value = f'{row_data["amount"]:,.2f}'
        self.method_select.value = row_data['method']
        self.total_display_input.value = f'{row_data["amount"]:,.2f}'
        self.balance_input.value = self.calculate_customer_pending(row_data['customer_id'])
        self.reference_input.value = row_data.get('reference', '')

    def on_receipt_amount_click(self):
        if self.new_mode:
            return self.open_settlement_dialog()
        if not self.draft_receipt_id:
            return ui.notify('No receipt selected', color='warning')
        return self.show_receipt_allocation_history(self.draft_receipt_id)

    def show_receipt_allocation_history(self, receipt_id):
        try:
            allocations = []
            sql = """
                SELECT
                    d.source_type,
                    d.source_id,
                    d.settlement_amount_display,
                    s.invoice_number AS sales_invoice_number,
                    r.invoice_number AS return_invoice_number
                FROM customer_receipt_details d
                LEFT JOIN sales s
                    ON d.source_type = 'Sale' AND s.id = d.source_id
                LEFT JOIN sales_returns r
                    ON d.source_type = 'Return' AND r.id = d.source_id
                WHERE d.payment_id = ?
                ORDER BY d.id ASC
            """
            connection.contogetrows(sql, allocations, (receipt_id,))

            rows = []
            for src_type, src_id, settlement_display, sales_inv, ret_inv in allocations:
                inv = sales_inv if src_type == 'Sale' else ret_inv
                rows.append({
                    'Type': src_type,
                    'SourceID': src_id,
                    'Invoice': inv,
                    'AppliedAmount': float(settlement_display or 0),
                })

            with ui.dialog() as dialog, ModernCard().classes('w-full max-w-5xl p-6'):
                ui.label(f'Receipt Allocation History - Receipt #{receipt_id}').classes('text-xl font-black mb-4')
                if not rows:
                    ui.label('No allocation details found for this receipt.').classes('text-gray-500')
                else:
                    ui.table(
                        columns=[
                            {'name': 'Type', 'label': 'Type', 'field': 'Type'},
                            {'name': 'SourceID', 'label': 'Source ID', 'field': 'SourceID'},
                            {'name': 'Invoice', 'label': 'Invoice #', 'field': 'Invoice'},
                            {'name': 'AppliedAmount', 'label': 'Applied Amount (Entered)', 'field': 'AppliedAmount', 'align': 'right'},
                        ],
                        rows=rows,
                        pagination=20
                    ).classes('w-full')
                ui.button('Close', on_click=dialog.close).classes('mt-4').props('flat')
            dialog.open()
        except Exception as e:
            ui.notify(f'Error loading receipt allocations: {e}', color='negative')

    async def _apply_row_from_id(self, cid):
        if not getattr(self, 'history_table', None):
            return
        rows = getattr(self.history_table, 'rows', None) or []
        target_index = next((i for i, r in enumerate(rows) if r.get('id') == cid), None)
        if target_index is None:
            return
        row = rows[target_index]
        self._selected_row_index = target_index
        await self.perform_load_row(row)
        self._apply_selected_row_color()

    def _apply_selected_row_color(self):
        if self._selected_row_index is None:
            return
        ui.run_javascript(f"""
        try {{
          const root = document.querySelector('.history-q-table');
          if (!root) return;
          const rows = root.querySelectorAll('tbody tr');
          if (!rows || rows.length === 0) return;
          const idx = Math.max(0, Math.min({self._selected_row_index} + 1, rows.length - 1));
          rows.forEach(el => {{
            el.style.backgroundColor = '';
            el.style.color = '';
            el.classList.remove('selected-highlight');
          }});
          const selected = rows[idx];
          if (selected) {{
            selected.style.backgroundColor = '#facc15';
            selected.style.color = 'black';
            selected.classList.add('selected-highlight');
          }}
        }} catch (e) {{ console.error('Highlight error:', e); }}
        """)

    async def _focus_first_row(self):
        if self.history_table and self.history_table.rows:
            cid = self.history_table.rows[0].get('id')
            if cid is not None:
                await self._apply_row_from_id(cid)

    def filter_history_table(self, query):
        target_query = str(query or "").lower()
        all_rows = getattr(self, '_all_receipt_data', [])
        if not target_query:
            self.history_table.rows = all_rows
        else:
            self.history_table.rows = [r for r in all_rows if target_query in str(r['customer']).lower() or target_query in str(r['id']).lower()]
        self.history_table.update()
        self._selected_row_index = None
        ui.run_javascript("""
        try {
          const root = document.querySelector('.history-q-table');
          if (!root) return;
          const rows = root.querySelectorAll('tbody tr');
          rows.forEach(el => { el.style.backgroundColor = ''; el.style.color = ''; el.classList.remove('selected-highlight'); });
        } catch (e) {}
        """)

    def create_ui(self):
        ui.add_head_html(MDS.get_global_styles())
        ui.add_head_html(f'<script>{MDS.get_theme_switcher_js()}</script>')
        
        with ui.element('div').classes('w-full mesh-gradient h-[calc(100vh-64px)] p-0 overflow-hidden'):
            with ui.row().classes('w-full h-full gap-0 overflow-hidden'):
                # MAIN CONTENT
                with ui.column().classes('flex-1 h-full p-4 gap-4 relative overflow-hidden'):
                    ui.element('div').classes('h-2')

                    # DUAL PANEL
                    with ui.row().classes('w-full flex-1 gap-6 overflow-hidden'):
                        # LEFT: History
                        with ui.column().classes('w-[35%] h-full gap-4'):
                            with ui.column().classes('w-full h-full glass p-3 rounded-3xl border border-white/10'):
                                with ui.row().classes('w-full items-center gap-3 glass p-3 rounded-2xl border border-white/10 hover:bg-white/5 mb-2'):
                                    ui.icon('history', size='1.25rem').classes('text-purple-400 ml-1')
                                    self.history_search = ui.input(placeholder='Search history...').props('borderless dense clearable dark').classes('flex-1 text-white font-bold').on_value_change(lambda e: self.filter_history_table(e.value)).on('keydown.down', self._focus_first_row)
                                
                                self.history_table = ui.table(
                                    columns=[
                                        {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left', 'sortable': True},
                                        {'name': 'date', 'label': 'Date', 'field': 'date', 'align': 'left', 'sortable': True},
                                        {'name': 'customer', 'label': 'Customer', 'field': 'customer', 'align': 'left', 'sortable': True},
                                        {'name': 'amount', 'label': 'Amount', 'field': 'amount', 'align': 'right', 'sortable': True},
                                    ],
                                    rows=[],
                                    row_key='id',
                                    selection='single',
                                ).classes('w-full flex-1 overflow-hidden history-q-table').props('virtual-scroll flat bordered dense hide-pagination')
                                
                                async def on_keydown(e):
                                    try:
                                        key = getattr(e, 'key', None) or getattr(e, 'args', {}).get('key', None)
                                        if key not in ('ArrowDown', 'ArrowUp'):
                                            return
                                        rows = getattr(self.history_table, 'rows', None) or []
                                        if not rows:
                                            return
                                        if self._selected_row_index is None:
                                            self._selected_row_index = 0
                                        if key == 'ArrowDown':
                                            self._selected_row_index = min(self._selected_row_index + 1, len(rows) - 1)
                                        else:
                                            self._selected_row_index = max(self._selected_row_index - 1, 0)
                                        cid = rows[self._selected_row_index].get('id')
                                        if cid is None:
                                            return
                                        await self._apply_row_from_id(cid)
                                    except Exception as ex:
                                        ui.notify(f'Keyboard navigation error: {ex}', color='warning')

                                async def on_history_row_click(e):
                                    row = e.args[1] if isinstance(e.args, (list, tuple)) and len(e.args) > 1 else None
                                    if not isinstance(row, dict):
                                        if isinstance(e.args, (list, tuple)) and e.args and isinstance(e.args[0], dict):
                                            row = e.args[0]
                                    if row:
                                        self._selected_row_index = next((i for i, r in enumerate(self.history_table.rows or []) if r.get('id') == row.get('id')), None)
                                        self._apply_selected_row_color()
                                        await self.perform_load_row(row)
                                        ui.run_javascript("try { const el = document.querySelector('.history-q-table'); if (el) el.focus(); } catch(e) {}")

                                self.history_table.on('row-click', on_history_row_click)
                                self.history_table.on('keydown', on_keydown)
                                ui.run_javascript("""
                                try {
                                  const el = document.querySelector('.history-q-table');
                                  if (el) {
                                    el.setAttribute('tabindex', '0');
                                    el.addEventListener('keydown', function(ev) {
                                      if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp') {
                                        ev.preventDefault();
                                      }
                                    });
                                    el.addEventListener('focus', function() { this.style.outline = 'none'; });
                                  }
                                } catch(e) {}
                                """)

                                self.history_overlay = ui.element('div').classes('absolute inset-0 bg-black/60 flex items-center justify-center z-20 text-white text-center p-6').style('backdrop-filter: blur(4px); pointer-events: none;')
                                with self.history_overlay:
                                    ui.label('NEW RECEIPT MODE\nClick Customer, then Amount to allocate invoices').classes('font-black text-xl whitespace-pre-wrap')
                                self.history_overlay.set_visibility(False)

                        # RIGHT: Editor
                        with ui.column().classes('flex-1 h-full gap-4'):
                            with ModernCard(glass=True).classes('w-full p-8 rounded-3xl border border-white/10'):
                                with ui.row().classes('w-full justify-between items-start mb-8'):
                                    with ui.column().classes('gap-1'):
                                        ui.label('Commerce Engine').classes('text-[10px] font-black uppercase tracking-[0.2em] text-purple-400')
                                        ui.label('Customer Receipt').classes('text-3xl font-black text-white').style('font-family: "Outfit", sans-serif;')
                                    
                                    with ui.column().classes('items-end gap-2'):
                                        with ui.row().classes('items-center gap-2 bg-white/5 px-3 py-1.5 rounded-xl border border-white/10'):
                                            ui.icon('event', size='0.9rem').classes('text-purple-400')
                                            self.date_input = ui.input(value=datetime.now().strftime('%Y-%m-%d')).props('borderless dense').classes('text-white text-[11px] font-bold w-24 px-1')
                                        
                                        self.currency_select = ui.select({r[0]: f"{r[2]} {r[1]}" for r in self.currency_rows}, value=self.default_currency_id).props('borderless dense').classes('bg-white/5 px-3 py-1 rounded-xl text-white text-[11px] font-bold w-36 border border-white/10').on('change', self.on_currency_change)

                                ui.label('COLLECTION DETAILS').classes('text-[9px] font-black text-purple-400 tracking-widest mb-6 opacity-40')
                                with ui.column().classes('w-full gap-6'):
                                    with ui.column().classes('w-full gap-1'):
                                        ui.label('Customer Account').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                    with ui.row().classes('items-center gap-3 bg-white/5 px-5 py-3 rounded-2xl border border-white/10 w-full hover:bg-white/10 transition-all cursor-pointer shadow-inner'):
                                            ui.icon('person', size='1.5rem').classes('text-purple-400')
                                            self.customer_input = ui.input(placeholder='Select Customer Account...').props('borderless dense dark readonly').classes('flex-1 text-white font-black text-lg').on('click', self.select_customer)

                                    with ui.row().classes('w-full gap-1'):
                                        ui.label('Reference/Notes').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                    with ui.row().classes('items-center gap-3 bg-white/5 px-5 py-3 rounded-2xl border border-white/10 w-full'):
                                        ui.icon('description', size='1.5rem').classes('text-purple-400')
                                        self.reference_input = ui.input(placeholder='Manual reference...').props('borderless dense dark').classes('flex-1 text-white font-black')

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
                                                self.amount_input = ui.input(value='0.00').props('borderless dense dark readonly').classes('flex-1 text-white font-black text-lg').on('click', self.on_receipt_amount_click)
                                                ui.button(icon='open_in_new', on_click=self.on_receipt_amount_click).props('flat round color=purple')
                                    
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
                        self.history_table.classes('dimmed')
                        ui.notify('New Receipt Mode', color='positive')
                        if hasattr(self, 'action_bar'):
                            self.action_bar.enter_new_mode()

                    self.action_bar = ModernActionBar(
                        on_new=handle_new,
                        on_save=self.save_receipt,
                        on_undo=lambda: [self.clear_form(), self.exit_new_mode()],
                        on_delete=self.delete_receipt,
                        on_print=lambda: self.show_receipt_print_dialog(
                            self.draft_receipt_id,
                            self.selected_customer.get('name', '') if self.selected_customer else '',
                            self.to_float(self.amount_input.value),
                            self.method_select.value,
                            self.selected_customer.get('id') if self.selected_customer else None
                        ) if self.draft_receipt_id else ui.notify('No receipt selected'),
                        on_print_special=lambda: self.show_receipt_print_dialog(
                            self.draft_receipt_id,
                            self.selected_customer.get('name', '') if self.selected_customer else '',
                            self.to_float(self.amount_input.value),
                            self.method_select.value,
                            self.selected_customer.get('id') if self.selected_customer else None
                        ) if self.draft_receipt_id else ui.notify('No receipt selected'),
                        on_refresh=self.refresh_history,
                        on_chatgpt=lambda: ui.run_javascript('window.open("https://chatgpt.com", "_blank");'),
                        on_view_transaction=lambda: accounting_helpers.show_transactions_dialog('Receipt', self.draft_receipt_id) if self.draft_receipt_id else ui.notify('No receipt selected'),
                        button_class='h-16',
                    ).style('position: static; width: 80px; border-radius: 20px; box-shadow: 0 20px 50px rgba(0,0,0,0.3);')

        ui.timer(0.1, self.refresh_history, once=True)

@ui.page('/customerreceipt')
def customer_receipt_page_route():
    CustomerReceiptUI()
