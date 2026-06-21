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

class SupplierPaymentUI:
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

        # Ensure reference column exists
        try:
            connection.insertingtodatabase("ALTER TABLE supplier_payment ADD reference NVARCHAR(100) NULL")
        except Exception:
            pass

        # State
        self.selected_supplier = None
        self.unpaid_invoices = []
        self.selected_invoices = []
        self.payment_data = []
        self._selected_row_index = None
        self._all_payment_data = []
        self.new_mode = False
        self.draft_payment_id = None
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
            ui.notify('Currency changed.')

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

    def calculate_supplier_pending(self, supplier_id):
        result = []
        sql = """
            SELECT SUM(COALESCE(total_amount, 0)) 
            FROM purchases p 
            INNER JOIN suppliers s ON s.id = p.supplier_id 
            WHERE s.id = ? AND p.payment_status = 'pending' AND COALESCE(p.total_amount, 0) > 0
        """
        connection.contogetrows(sql, result, (supplier_id,))
        return self.to_float(result[0][0]) if result and result[0][0] is not None else 0.0

    async def refresh_history(self):
        async with loading_indicator.show_loading('refresh_payments', 'Refreshing payments...', overlay=True):
            data = []
            sql = """SELECT sp.id, sp.payment_date, s.name, sp.amount, sp.payment_method, s.id as supplier_id, ISNULL(sp.reference, '') as reference 
                     FROM supplier_payment sp
                     JOIN suppliers s ON sp.supplier_id = s.id
                     ORDER BY sp.id DESC"""
            connection.contogetrows(sql, data)
            rows = []
            for r in data:
                rows.append({
                    'id': r[0],
                    'date': r[1],
                    'supplier': r[2],
                    'amount': self.to_float(r[3]),
                    'method': r[4],
                    'supplier_id': r[5],
                    'reference': r[6],
                })
            self._all_payment_data = rows
            self.history_table.rows = rows
            self.history_table.update()
            await self.load_last_payment()

    def clear_form(self, reset_supplier=True):
        self.supplier_input.value = ''
        self.reference_input.value = ''
        self.balance_usd_input.value = 0
        self.balance_ll_input.value = 0
        self.amount_input.value = 0
        self.method_select.value = 'Cash'
        self.selected_invoices = []
        self.draft_payment_id = None
        self.draft_amount = 0.0
        if reset_supplier:
            self.selected_supplier = None
        self.total_display_input.value = '0.00'

    def exit_new_mode(self):
        self.new_mode = False
        self.history_overlay.set_visibility(False)
        self.history_table.classes(remove='dimmed')
        if hasattr(self, 'action_bar'):
            self.action_bar.reset_state()

    def allocate_payment_to_invoices(self, selected_rows, pay_amount):
        allocations = []
        remaining = round(pay_amount, 2)
        # Prioritize Returns (Credits) to increase settlement capacity
        ordered_rows = sorted(selected_rows, key=lambda row: (0 if row.get('type') == 'Return' else 1, str(row.get('date') or ''), row.get('id') or 0))
        
        for row in ordered_rows:
            is_return = row.get('type') == 'Return'
            invoice_due = self.to_float(row.get('amount'))
            
            if invoice_due == 0: continue
            
            settlement_amount = invoice_due if is_return else min(invoice_due, remaining)
            
            if abs(settlement_amount) > 0 or is_return:
                allocations.append({
                    'id': row['id'],
                    'type': row.get('type', 'Purchase'),
                    'invoice_number': row['invoice_number'],
                    'date': row['date'],
                    'amount': invoice_due,
                    'settlement_amount': round(settlement_amount, 2),
                })
                # Subtracting settlement from remaining. 
                # If settlement is positive (Invoice), remaining decreases.
                # If settlement is negative (Return), remaining increases.
                remaining = round(remaining - settlement_amount, 2)

            if remaining <= 0 and not any(r.get('type') == 'Return' for r in ordered_rows[ordered_rows.index(row)+1:]):
                break
        return allocations

    def select_supplier(self):
        s_data = []
        connection.contogetrows("SELECT id, name, balance, balance_usd FROM suppliers ORDER BY name", s_data)
        all_supplier_rows = [
            {'id': r[0], 'name': r[1], 'balance_ll': self.to_float(r[2]), 'balance_usd': self.to_float(r[3])}
            for r in s_data
        ]

        _selected_row = None
        state = {'selected_idx': 0}

        with ui.dialog() as d, ModernCard().classes('w-full max-w-2xl p-6'):
            ui.label('Select Supplier').classes('text-xl font-black mb-4 text-white')

            with ui.row().classes('w-full items-center gap-3 bg-white/5 px-4 py-2 rounded-xl border border-white/10 mb-4'):
                ui.icon('search', size='1.25rem').classes('text-orange-400')
                search_query_input = ui.input(placeholder='Search by name or id...').props('borderless dense').classes('flex-1 text-white text-sm')

            with ui.element('div').classes('w-full h-80 overflow-hidden flex flex-col'):
                with ui.element('div').classes('flex-1 overflow-auto min-h-0'):
                    supplier_table = ui.table(
                        columns=[
                            {'name': 'name', 'label': 'Name', 'field': 'name', 'align': 'left', 'sortable': True},
                            {'name': 'balance_ll', 'label': 'Balance LL', 'field': 'balance_ll', 'align': 'right'},
                            {'name': 'balance_usd', 'label': 'Balance USD', 'field': 'balance_usd', 'align': 'right'},
                        ],
                        rows=all_supplier_rows,
                        row_key='id',
                        selection='single',
                    ).classes('w-full h-full bg-transparent overflow-hidden').props('virtual-scroll flat bordered dense hide-pagination')

            def apply_highlight_js():
                idx = state['selected_idx']
                ui.run_javascript(f"""
                    try {{
                      const root = document.getElementById('{getattr(supplier_table, "id", "")}') || document.querySelector('.q-table');
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
                if not supplier_table.rows:
                    return
                state['selected_idx'] = max(0, min(state['selected_idx'], len(supplier_table.rows) - 1))
                row = supplier_table.rows[state['selected_idx']]
                supplier_table.selected = [row]
                supplier_table.update()
                supplier_table.run_method('scrollTo', state['selected_idx'])
                apply_highlight_js()

            def confirm_with_row(row_data):
                self.selected_supplier = row_data
                self.supplier_input.value = row_data['name']
                self.balance_usd_input.value = row_data['balance_usd']
                self.balance_ll_input.value = row_data['balance_ll']
                self.amount_input.value = '0.00'
                self.selected_invoices = []
                self.total_display_input.value = '0.00'

                ui.run_javascript('window.__supplier_dialog_active = false;')
                d.close()
                ui.notify('Supplier selected', color='positive')

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

                    if supplier_table.rows:
                        for i, r in enumerate(supplier_table.rows):
                            if r.get('id') == row_data.get('id'):
                                state['selected_idx'] = i
                                break
                        apply_highlight_js()

                    _selected_row = row_data
                    confirm_with_row(row_data)
                except Exception as ex:
                    ui.notify(f'Row selection error: {ex}', color='negative')

            supplier_table.on('row-click', on_click_row)

            ui.timer(0.05, select_and_scroll, once=True)

            grid_id = getattr(supplier_table, 'id', '')
            search_id = getattr(search_query_input, 'id', '')
            ui.run_javascript(f"""
                window.__supplier_dialog_active = true;
                try {{
                  const root = document.getElementById('{grid_id}') || document.querySelector('.q-table');
                  if (root) {{
                    root.tabIndex = 0;
                    try {{ root.style.outline = 'none'; }} catch(e) {{}}
                    try {{ root.style.caretColor = 'transparent'; }} catch(e) {{}}

                    try {{ root.dataset.selIdx = '-1'; }} catch(e) {{}}

                    root.addEventListener('keydown', (ev) => {{
                      if (!window.__supplier_dialog_active) return;
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
                      if (!window.__supplier_dialog_active) return;
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
                    supplier_table.rows = all_supplier_rows
                else:
                    supplier_table.rows = [
                        r for r in all_supplier_rows
                        if q in str(r.get('name', '')).lower()
                        or q in str(r.get('id', '')).lower()
                    ]
                _selected_row = None
                supplier_table.selected = []
                supplier_table.update()
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
                ModernButton('Cancel', on_click=lambda: (ui.run_javascript('window.__supplier_dialog_active=false;'), d.close()), variant='secondary')
        d.open()

    def open_settlement_dialog(self):
        if not self.selected_supplier:
            ui.notify('Select supplier first', color='warning')
            return
        
        supplier = self.selected_supplier
        invoices_data = []
        # Fetch Purchases
        purchase_invoices = []
        sql_purchases = """
            SELECT p.id, p.invoice_number, p.total_amount, p.purchase_date
            FROM purchases p
            WHERE p.payment_status = 'pending' AND p.supplier_id = ? AND COALESCE(p.total_amount, 0) > 0
            ORDER BY p.purchase_date ASC, p.id ASC
        """
        connection.contogetrows(sql_purchases, purchase_invoices, (supplier['id'],))
        
        # Fetch Returns
        returns_data = []
        sql_returns = """
            SELECT r.id, r.invoice_number, r.total_amount, r.return_date
            FROM purchase_returns r
            WHERE r.payment_status = 'pending' AND r.supplier_id = ? AND COALESCE(r.total_amount, 0) > 0
            ORDER BY r.return_date ASC, r.id ASC
        """
        connection.contogetrows(sql_returns, returns_data, (supplier['id'],))

        rows = []
        for r in purchase_invoices:
            rows.append({
                'id': r[0], 'invoice_number': r[1], 'amount': self.to_float(r[2]), 
                'date': str(r[3]), 'type': 'Purchase', 'display_number': r[1]
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
            ui.label(f'Pending: {supplier["name"]}').classes('text-2xl font-black mb-2 text-white')
            pending_usd = self.calculate_supplier_pending(supplier["id"])
            ui.label(f'Total Due: ${pending_usd:,.2f}').classes('text-lg mb-4 text-orange-400 font-bold')

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
                pay_amount_input = ui.number('Payment Amount', value=sum(r['amount'] for r in rows)).classes('w-40')
                method_input = ui.select(['Cash', 'Card', 'Visa', 'OMT'], value=self.method_select.value).classes('w-40')

            async def confirm_settlement():
                selected_rows = invoice_table.selected
                if not selected_rows: return ui.notify('Select at least one record', color='warning')
                pay_amount = self.to_float(pay_amount_input.value)
                if pay_amount < 0: return ui.notify('Net amount cannot be negative', color='warning')
                
                allocations = self.allocate_payment_to_invoices(selected_rows, pay_amount)
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

    async def save_payment(self):
        if not self.selected_supplier or not self.new_mode:
            return ui.notify('New mode + Select supplier', color='warning')

        async with loading_indicator.show_loading('save_payment', 'Saving payment...', overlay=True):
            try:
                pay_amount = self.to_float(self.amount_input.value)
                # Allow net-zero settlements when Return offsets Purchase exactly.
                if pay_amount < 0 or not self.selected_invoices:
                    return ui.notify('Amount must be >= 0 + Select invoices', color='warning')

                # Normalization for shared records (base currency)
                selected_currency_id = self.currency_select.value
                exchange_rate = float(self.currency_exchange_rates.get(selected_currency_id, 1.0))
                normalized_amount = round(pay_amount / exchange_rate, 2)
                
                payment_date = self.date_input.value or datetime.now().strftime('%Y-%m-%d')
                user_id = session_storage.get('user')['user_id']

                # Fetch/ensure auxiliary number
                import accounting_helpers
                supp_aux = accounting_helpers.ensure_supplier_auxiliary(
                    self.selected_supplier['id'],
                    supplier_name=self.selected_supplier.get('name'),
                    fallback_account_number='4011'
                )

                # Standardized INSERT with auxiliary, user, currency, and balance column info
                reference = self.reference_input.value or ''
                sql_payment = """
                    INSERT INTO supplier_payment 
                    (supplier_id, amount, total_amount, payment_date, payment_method, auxiliary_number, user_id, currency_id, status, balance_column, created_at, reference) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'completed', ?, GETDATE(), ?)
                """
                connection.insertingtodatabase(sql_payment, (
                    self.selected_supplier['id'], normalized_amount, pay_amount, 
                    payment_date, self.method_select.value, supp_aux, user_id, selected_currency_id,
                    self.pay_currency_select.value, reference
                ))
                
                payment_id = connection.getid("SELECT MAX(id) FROM supplier_payment", [])
                self.draft_payment_id = payment_id

                for alloc in self.selected_invoices:
                    # Invoices/Returns in DB are normalized (base currency)
                    norm_settlement = round(alloc['settlement_amount'] / exchange_rate, 2)
                    new_total = round(alloc['amount'] - norm_settlement, 2)
                    status = 'completed' if new_total == 0 else ('pending' if new_total > 0 else 'credit')
                    
                    if alloc['type'] == 'Return':
                        connection.insertingtodatabase("UPDATE purchase_returns SET total_amount = ?, payment_status = ? WHERE id = ?", (abs(new_total), status, alloc['id']))
                    else:
                        connection.insertingtodatabase("UPDATE purchases SET total_amount = ?, payment_status = ? WHERE id = ?", (new_total, status, alloc['id']))
                        
                    # Record settlement details for robust "Undo/Delete"
                    connection.insertingtodatabase(
                        "INSERT INTO supplier_payment_details (payment_id, source_type, source_id, settlement_amount) VALUES (?, ?, ?, ?)",
                        (payment_id, alloc['type'], alloc['id'], alloc['settlement_amount'])
                    )

                # Update supplier specific balance columns
                pay_curr = self.pay_currency_select.value
                if pay_curr == 'USD':
                    # Use actual USD amount for USD balance column
                    connection.insertingtodatabase("UPDATE suppliers SET balance_usd = balance_usd - ? WHERE id = ?", (pay_amount if exchange_rate == 1 else normalized_amount, self.selected_supplier['id']))
                else:
                    # Use actual L.L. amount for L.L. balance column
                    connection.insertingtodatabase("UPDATE suppliers SET balance = balance - ? WHERE id = ?", (pay_amount, self.selected_supplier['id']))

                # Accounting
                # Cash payments should affect cash account (5300) with:
                # - debit caisse (5300) for cash decrease
                # - credit supplier auxiliary when reducing supplier liability
                if self.method_select.value == 'Cash':
                    # Resolve caisse auxiliary_id from auxiliary table
                    caisse_rows = []
                    connection.contogetrows(
                        "SELECT TOP 1 id FROM auxiliary WHERE number = ?",
                        caisse_rows,
                        params=['5300.000001']
                    )
                    caisse_aux_id = caisse_rows[0][0] if caisse_rows else None

                    accounting_helpers.save_accounting_transaction(
                        'Payment',
                        str(payment_id),
                        [
                            # Supplier is DEBITed, caisse/cash is CREDITed
                            {'account': supp_aux, 'debit': normalized_amount, 'credit': 0},
                            {'account': '5300', 'auxiliary_id': caisse_aux_id, 'debit': 0, 'credit': normalized_amount},
                        ],
                        description=f"Supplier Cash Payment (Caisse) #{payment_id} - {self.selected_supplier['name']}"
                    )
                else:
                    import business_track_settings
                    payment_aux = business_track_settings.get_payment_account(self.method_select.value)
                    accounting_helpers.save_accounting_transaction(
                        'Payment',
                        str(payment_id),
                        [
                            {'account': supp_aux,    'debit': normalized_amount, 'credit': 0},
                            {'account': payment_aux, 'debit': 0,                 'credit': normalized_amount},
                        ],
                        description=f"Supplier {self.method_select.value} Payment #{payment_id} - {self.selected_supplier['name']}"
                    )
                
                connection.update_cash_drawer_balance(normalized_amount, 'Out', user_id, f"Payment #{payment_id}")

                ui.notify(f'Saved: {self.get_current_currency_symbol()}{pay_amount:,.2f} (Normalized: ${normalized_amount:,.2f})', color='positive')
                await self.refresh_history()
                self.exit_new_mode()
                await self.show_payment_print_dialog(payment_id, self.selected_supplier['name'], pay_amount, self.method_select.value, self.selected_supplier['id'])
            except Exception as e:
                ui.notify(f'Error: {e}', color='negative')
                print(f"ERROR: {e}")

    async def show_payment_print_dialog(self, payment_id, supplier_name, amount, method, supplier_id):
        remaining = self.calculate_supplier_pending(supplier_id)
        from print_helper import print_dialog_content

        # Fetch settlement details
        alloc_data = []
        connection.contogetrows("""
            SELECT d.source_type, d.settlement_amount,
                   p.invoice_number AS pur_inv, r.invoice_number AS ret_inv
            FROM supplier_payment_details d
            LEFT JOIN purchases p ON d.source_type = 'Purchase' AND p.id = d.source_id
            LEFT JOIN purchase_returns r ON d.source_type = 'Return' AND r.id = d.source_id
            WHERE d.payment_id = ?
            ORDER BY d.id ASC
        """, alloc_data, (payment_id,))
        alloc_rows = []
        for src_type, s_amt, p_inv, r_inv in alloc_data:
            alloc_rows.append({
                'type': src_type,
                'invoice': p_inv if src_type == 'Purchase' else r_inv,
                'amount': self.to_float(s_amt),
            })

        ui.add_head_html('<style> @media print { .q-dialog__inner > div { max-width: none !important; width: 100% !important; background: white !important; color: black !important; } .hide-on-print { display: none !important; } .text-white, .text-gray-400, .text-red-400, .text-orange-400, .text-green-400 { color: black !important; } [class*="bg-"] { background: white !important; } } </style>')
        with ui.dialog() as d, ModernCard().classes('w-full max-w-lg p-8'):
            with ui.column().classes('w-full items-center gap-6'):
                with ui.column().classes('w-full items-center gap-1'):
                    ui.label('PAYMENT VOUCHER').classes('text-[10px] font-black tracking-[0.3em] text-orange-400')
                    ui.label(f'#{payment_id}').classes('text-4xl font-black text-white')

                with ui.column().classes('w-full bg-white/5 rounded-2xl p-6 gap-4 border border-white/10'):
                    with ui.row().classes('w-full justify-between'):
                        ui.label('Supplier').classes('text-sm text-gray-400')
                        ui.label(supplier_name).classes('text-sm text-white font-bold')
                    with ui.row().classes('w-full justify-between'):
                        ui.label('Date').classes('text-sm text-gray-400')
                        ui.label(datetime.now().strftime('%Y-%m-%d %H:%M')).classes('text-sm text-white font-bold')
                    with ui.row().classes('w-full justify-between'):
                        ui.label('Amount Paid').classes('text-sm text-gray-400')
                        ui.label(f'${amount:,.2f}').classes('text-lg text-red-400 font-black')
                    with ui.row().classes('w-full justify-between'):
                        ui.label('Method').classes('text-sm text-gray-400')
                        ui.label(method).classes('text-sm text-white font-bold')

                    if alloc_rows:
                        ui.element('div').classes('w-full h-px bg-white/20 my-1')
                        ui.label('SETTLEMENT DETAILS').classes('text-[8px] font-black text-orange-400/60 uppercase tracking-widest')
                        for ar in alloc_rows:
                            with ui.row().classes('w-full justify-between'):
                                ui.label(f"{ar['type']} #{ar['invoice']}").classes('text-xs text-gray-400')
                                ui.label(f"${ar['amount']:,.2f}").classes('text-xs text-white font-bold')

                    with ui.row().classes('w-full justify-between pt-3 border-t border-white/10'):
                        ui.label('Remaining Balance').classes('text-sm text-gray-400')
                        ui.label(f'${remaining:,.2f}').classes('text-lg text-orange-400 font-black' if remaining > 0 else 'text-lg text-green-400 font-black')

                with ui.row().classes('w-full justify-center gap-4 hide-on-print'):
                    ui.button('PRINT', icon='print', on_click=lambda: ui.run_javascript(print_dialog_content())).props('flat color=orange-400').classes('font-black')
                    ui.button('CLOSE', icon='close', on_click=d.close).props('flat color=red').classes('font-black')
        d.open()

    async def delete_payment(self):
        if not self.draft_payment_id or self.new_mode:
            return ui.notify('Select a payment from history first', color='warning')

        with ui.dialog() as d, ModernCard().classes('p-8 bg-slate-900 border border-orange-500/30 shadow-2xl'):
            with ui.column().classes('w-full items-center gap-4'):
                ui.icon('warning', size='4rem', color='orange')
                ui.label('Confirm Deletion').classes('text-2xl font-black text-white uppercase tracking-wider')
                ui.label(f'This will permanently delete Payment #{self.draft_payment_id} and revert all related purchase settlements.').classes('text-gray-400 text-center mb-4')
                
                with ui.row().classes('w-full justify-center gap-4'):
                    ModernButton('Cancel', on_click=d.close, variant='secondary').classes('w-32')
                    async def do_delete():
                        d.close()
                        async with loading_indicator.show_loading('delete_payment', 'Reverting financial data...', overlay=True):
                            try:
                                # 1. Fetch payment core info
                                res = []
                                connection.contogetrows("SELECT supplier_id, amount, total_amount, balance_column FROM supplier_payment WHERE id = ?", res, (self.draft_payment_id,))
                                if not res: return ui.notify('Payment record not found')
                                supp_id, norm_amt, total_amt, bal_col = res[0]

                                # 2. Revert Settlements
                                settlements = []
                                connection.contogetrows("SELECT source_type, source_id, settlement_amount FROM supplier_payment_details WHERE payment_id = ?", settlements, (self.draft_payment_id,))
                                for s_type, s_id, s_amt in settlements:
                                    if s_type == 'Return':
                                        connection.insertingtodatabase("UPDATE purchase_returns SET total_amount = total_amount + ?, payment_status = 'pending' WHERE id = ?", (abs(s_amt), s_id))
                                    else:
                                        connection.insertingtodatabase("UPDATE purchases SET total_amount = total_amount + ?, payment_status = 'pending' WHERE id = ?", (s_amt, s_id))

                                # 3. Revert Supplier Balance
                                if bal_col == 'USD':
                                    connection.insertingtodatabase("UPDATE suppliers SET balance_usd = balance_usd + ? WHERE id = ?", (total_amt, supp_id))
                                else:
                                    connection.insertingtodatabase("UPDATE suppliers SET balance = balance + ? WHERE id = ?", (total_amt, supp_id))

                                # 4. Reverse Cash Drawer
                                user_id = session_storage.get('user')['user_id']
                                connection.update_cash_drawer_balance(norm_amt, 'In', user_id, f"Delete Payment #{self.draft_payment_id}")

                                # 5. Remove Accounting Transactions
                                accounting_helpers.save_accounting_transaction('Payment', str(self.draft_payment_id), [])

                                # 6. Clean up records
                                connection.insertingtodatabase("DELETE FROM supplier_payment_details WHERE payment_id = ?", (self.draft_payment_id,))
                                connection.insertingtodatabase("DELETE FROM supplier_payment WHERE id = ?", (self.draft_payment_id,))

                                ui.notify(f'Payment #{self.draft_payment_id} deleted successfully', color='positive')
                                await self.refresh_history()
                                self.clear_form()
                            except Exception as ex:
                                ui.notify(f'Delete Error: {ex}', color='negative')
                    ModernButton('Delete Forever', on_click=do_delete, variant='error').classes('w-48')
        d.open()

    async def load_last_payment(self):
        await asyncio.sleep(0.1)
        if self.history_table.rows:
            await self.perform_load_row(self.history_table.rows[0])

    async def perform_load_row(self, row_data):
        self.exit_new_mode()
        if hasattr(self, 'action_bar'):
            self.action_bar.enter_edit_mode()
        self.draft_payment_id = row_data['id']
        self.selected_supplier = {'id': row_data['supplier_id'], 'name': row_data['supplier']}
        self.supplier_input.value = row_data['supplier']
        self.amount_input.value = f'{row_data["amount"]:,.2f}'
        self.method_select.value = row_data['method']
        self.total_display_input.value = f'{row_data["amount"]:,.2f}'
        self.reference_input.value = row_data.get('reference', '')
        
        # Load up-to-date balances
        s_res = []
        connection.contogetrows("SELECT id, name, balance, balance_usd FROM suppliers WHERE id = ?", s_res, (row_data['supplier_id'],))
        if s_res:
             self.selected_supplier = {'id': s_res[0][0], 'name': s_res[0][1], 'balance_ll': s_res[0][2], 'balance_usd': s_res[0][3]}
             self.balance_usd_input.value = s_res[0][3]
             self.balance_ll_input.value = s_res[0][2]

    def on_payment_amount_click(self):
        if self.new_mode:
            return self.open_settlement_dialog()
        if not self.draft_payment_id:
            return ui.notify('No payment selected', color='warning')
        return self.show_payment_allocation_history(self.draft_payment_id)

    def show_payment_allocation_history(self, payment_id):
        try:
            allocations = []
            sql = """
                SELECT
                    d.source_type,
                    d.source_id,
                    d.settlement_amount,
                    p.invoice_number AS purchases_invoice_number,
                    r.invoice_number AS return_invoice_number
                FROM supplier_payment_details d
                LEFT JOIN purchases p
                    ON d.source_type = 'Purchase' AND p.id = d.source_id
                LEFT JOIN purchase_returns r
                    ON d.source_type = 'Return' AND r.id = d.source_id
                WHERE d.payment_id = ?
                ORDER BY d.id ASC
            """
            connection.contogetrows(sql, allocations, (payment_id,))

            rows = []
            for src_type, src_id, settlement_base, pur_inv, ret_inv in allocations:
                inv = pur_inv if src_type == 'Purchase' else ret_inv
                rows.append({
                    'Type': src_type,
                    'SourceID': src_id,
                    'Invoice': inv,
                    'AppliedAmount': float(settlement_base or 0),
                })

            with ui.dialog() as dialog, ModernCard().classes('w-full max-w-5xl p-6'):
                ui.label(f'Payment Allocation History - Payment #{payment_id}').classes('text-xl font-black mb-4')
                if not rows:
                    ui.label('No allocation details found for this payment.').classes('text-gray-500')
                else:
                    ui.table(
                        columns=[
                            {'name': 'Type', 'label': 'Type', 'field': 'Type'},
                            {'name': 'SourceID', 'label': 'Source ID', 'field': 'SourceID'},
                            {'name': 'Invoice', 'label': 'Invoice #', 'field': 'Invoice'},
                            {'name': 'AppliedAmount', 'label': 'Applied Settlement (Base)', 'field': 'AppliedAmount', 'align': 'right'},
                        ],
                        rows=rows,
                        pagination=20
                    ).classes('w-full')
                ui.button('Close', on_click=dialog.close).classes('mt-4').props('flat')
            dialog.open()
        except Exception as e:
            ui.notify(f'Error loading payment allocations: {e}', color='negative')

    def filter_history_table(self, query):
        target_query = str(query or "").lower()
        all_rows = getattr(self, '_all_payment_data', [])
        if not target_query:
            self.history_table.rows = all_rows
        else:
            self.history_table.rows = [r for r in all_rows if target_query in str(r['supplier']).lower() or target_query in str(r['id']).lower()]
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

    async def _focus_first_row(self, *args):
        if self.history_table and self.history_table.rows:
            cid = self.history_table.rows[0].get('id')
            if cid is not None:
                await self._apply_row_from_id(cid)

    def create_ui(self):
        ui.add_head_html(MDS.get_global_styles())
        ui.add_head_html(f'<script>{MDS.get_theme_switcher_js()}</script>')
        
        with ui.element('div').classes('w-full mesh-gradient h-[calc(100vh-64px)] p-0 overflow-hidden'):
            with ui.row().classes('w-full h-full gap-0 overflow-hidden'):
                with ui.column().classes('flex-1 h-full p-4 gap-4 relative overflow-hidden'):
                    # HEADER (Empty as elements moved)
                    ui.element('div').classes('h-2')

                    # DUAL PANEL
                    with ui.row().classes('w-full flex-1 gap-6 overflow-hidden'):
                        # LEFT: History
                        with ui.column().classes('w-[35%] h-full gap-4'):
                            with ui.column().classes('w-full h-full glass p-3 rounded-3xl border border-white/10'):
                                with ui.row().classes('w-full items-center gap-3 glass p-3 rounded-2xl border border-white/10 hover:bg-white/5 mb-2'):
                                    ui.icon('history', size='1.25rem').classes('text-orange-400 ml-1')
                                    self.history_search = ui.input(placeholder='Search vendors...').props('borderless dense clearable dark').classes('flex-1 text-white font-bold').on_value_change(lambda e: self.filter_history_table(e.value)).on('keydown.down', self._focus_first_row)
                                
                                self.history_table = ui.table(
                                    columns=[
                                        {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left', 'sortable': True},
                                        {'name': 'date', 'label': 'Date', 'field': 'date', 'align': 'left', 'sortable': True},
                                        {'name': 'supplier', 'label': 'Vendor', 'field': 'supplier', 'align': 'left', 'sortable': True},
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
                                    ui.label('NEW PAYMENT MODE\nClick Vendor, then Amount to allocate invoices').classes('font-black text-xl whitespace-pre-wrap')
                                self.history_overlay.set_visibility(False)

                        # RIGHT: Editor
                        with ui.column().classes('flex-1 h-full gap-4'):
                            with ModernCard(glass=True).classes('w-full p-8 rounded-3xl border border-white/10'):
                                # BRANDING & TITLE (MOVED FROM HEADER)
                                with ui.row().classes('w-full justify-between items-start mb-8'):
                                    with ui.column().classes('gap-1'):
                                        ui.label('Procurement Engine').classes('text-[10px] font-black uppercase tracking-[0.2em] text-orange-400')
                                        ui.label('Supplier Payment').classes('text-3xl font-black text-white').style('font-family: "Outfit", sans-serif;')
                                    
                                    with ui.column().classes('items-end gap-2'):
                                        with ui.row().classes('items-center gap-2 bg-white/5 px-3 py-1.5 rounded-xl border border-white/10'):
                                            ui.icon('event', size='0.9rem').classes('text-orange-400')
                                            self.date_input = ui.input(value=datetime.now().strftime('%Y-%m-%d')).props('borderless dense').classes('text-white text-[11px] font-bold w-24 px-1')
                                        
                                        self.currency_select = ui.select({r[0]: f"{r[2]} {r[1]}" for r in self.currency_rows}, value=self.default_currency_id).props('borderless dense').classes('bg-white/5 px-3 py-1 rounded-xl text-white text-[11px] font-bold w-36 border border-white/10').on('change', self.on_currency_change)

                                ui.label('DISBURSEMENT DETAILS').classes('text-[9px] font-black text-orange-400 tracking-widest mb-6 opacity-40')
                                with ui.column().classes('w-full gap-6'):
                                    with ui.column().classes('w-full gap-1'):
                                        ui.label('Supplier Entity').classes('text-[9px] font-black text-orange-400 uppercase tracking-widest ml-4')
                                        with ui.row().classes('items-center gap-3 bg-white/5 px-5 py-3 rounded-2xl border border-white/10 w-full hover:bg-white/10 transition-all cursor-pointer shadow-inner'):
                                            ui.icon('business', size='1.5rem').classes('text-orange-400')
                                            self.supplier_input = ui.input(placeholder='Select Supplier Entity...').props('borderless dense dark readonly').classes('flex-1 text-white font-black text-lg').on('click', self.select_supplier)
                                    
                                    with ui.row().classes('w-full gap-1'):
                                        ui.label('Reference/Notes').classes('text-[9px] font-black text-orange-400 uppercase tracking-widest ml-4')
                                    with ui.row().classes('items-center gap-3 bg-white/5 px-5 py-3 rounded-2xl border border-white/10 w-full'):
                                        ui.icon('description', size='1.5rem').classes('text-orange-400')
                                        self.reference_input = ui.input(placeholder='Manual reference...').props('borderless dense dark').classes('flex-1 text-white font-black')
                                    
                                    with ui.row().classes('w-full gap-4'):
                                        with ui.column().classes('flex-1 gap-1'):
                                            ui.label('USD Balance').classes('text-[9px] font-black text-orange-400 uppercase tracking-widest ml-4')
                                            with ui.row().classes('items-center gap-3 bg-white/5 px-4 py-2 rounded-xl border border-white/10 w-full'):
                                                self.balance_usd_input = ui.number(value=0, format='%.2f').props('borderless dense dark readonly').classes('flex-1 text-white font-black')
                                        with ui.column().classes('flex-1 gap-1'):
                                            ui.label('LL Balance').classes('text-[9px] font-black text-orange-400 uppercase tracking-widest ml-4')
                                            with ui.row().classes('items-center gap-3 bg-white/5 px-4 py-2 rounded-xl border border-white/10 w-full'):
                                                self.balance_ll_input = ui.number(value=0, format='%.0f').props('borderless dense dark readonly').classes('flex-1 text-white font-black')
                                        with ui.column().classes('w-32 gap-1'):
                                            ui.label('Pay from').classes('text-[9px] font-black text-orange-400 uppercase tracking-widest ml-4')
                                            self.pay_currency_select = ui.select(['LL', 'USD'], value='USD').props('borderless dense dark').classes('bg-white/5 px-4 py-2 rounded-xl border border-white/10 w-full text-white text-xs font-bold')

                                    with ui.row().classes('w-full gap-4'):
                                        with ui.column().classes('flex-1 gap-1'):
                                            ui.label('Disbursement Amount').classes('text-[9px] font-black text-orange-400 uppercase tracking-widest ml-4')
                                            with ui.row().classes('items-center gap-3 bg-white/5 px-5 py-3 rounded-2xl border border-white/10 w-full hover:bg-white/10 transition-all cursor-pointer'):
                                                ui.icon('payments', size='1.5rem').classes('text-red-400')
                                                self.amount_input = ui.input(value='0.00').props('borderless dense dark readonly').classes('flex-1 text-white font-black text-lg').on('click', self.on_payment_amount_click)
                                                ui.button(icon='open_in_new', on_click=self.on_payment_amount_click).props('flat round color=orange')
                                        
                                        with ui.column().classes('flex-1 gap-1'):
                                            ui.label('Payment Method').classes('text-[9px] font-black text-orange-400 uppercase tracking-widest ml-4')
                                            self.method_select = ui.select(['Cash', 'Card', 'Visa', 'OMT'], value='Cash').props('borderless dense dark').classes('bg-white/5 px-5 py-3 rounded-2xl border border-white/10 w-full text-white font-black')

                                    with ui.column().classes('w-full gap-1'):
                                        ui.label('Selected for Settlement').classes('text-[9px] font-black text-orange-400 uppercase tracking-widest ml-4')
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
                        ui.notify('New Payment Mode', color='warning')
                        if hasattr(self, 'action_bar'):
                            self.action_bar.enter_new_mode()

                    self.action_bar = ModernActionBar(
                        on_new=handle_new,
                        on_save=self.save_payment,
                        on_undo=lambda: [self.clear_form(), self.exit_new_mode()],
                        on_delete=self.delete_payment,
                        on_print=lambda: self.show_payment_print_dialog(
                            self.draft_payment_id,
                            self.selected_supplier.get('name', '') if self.selected_supplier else '',
                            self.to_float(self.amount_input.value),
                            self.method_select.value,
                            self.selected_supplier.get('id') if self.selected_supplier else None
                        ) if self.draft_payment_id else ui.notify('No payment selected'),
                        on_print_special=lambda: self.show_payment_print_dialog(
                            self.draft_payment_id,
                            self.selected_supplier.get('name', '') if self.selected_supplier else '',
                            self.to_float(self.amount_input.value),
                            self.method_select.value,
                            self.selected_supplier.get('id') if self.selected_supplier else None
                        ) if self.draft_payment_id else ui.notify('No payment selected'),
                        on_refresh=self.refresh_history,
                        on_chatgpt=lambda: ui.run_javascript('window.open("https://chatgpt.com", "_blank");'),
                        on_view_transaction=lambda: accounting_helpers.show_transactions_dialog('Payment', str(self.draft_payment_id)) if self.draft_payment_id else ui.notify('No payment selected'),
                        button_class='h-16',
                    ).style('position: static; width: 80px; border-radius: 20px; box-shadow: 0 20px 50px rgba(0,0,0,0.3);')

        ui.timer(0.1, self.refresh_history, once=True)

@ui.page('/supplierpayment')
def supplier_payment_page_route():
    SupplierPaymentUI()
