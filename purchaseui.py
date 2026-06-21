"""
Modern Purchase UI
Complete redesign with modern components and interactions, exactly matching the Sales UI AgGrid Compact style.
"""

from nicegui import ui
from pathlib import Path
from datetime import date as dt
from connection import connection
from datetime import datetime
from decimal import Decimal
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
from loading_indicator import loading_indicator
from connection_cashdrawer import connection_cashdrawer
from modern_design_system import ModernDesignSystem as MDS
from purchase_service import PurchaseService
from modern_ui_components import ModernActionBar
import asyncio

class PurchaseUI:
    def __init__(self, show_navigation=True):
        self.invoicenumber = ''

        # Check if user is logged in
        user = session_storage.get('user')
        if not user:
            ui.notify('Please login to access this page', color='red')
            ui.run_javascript('window.location.href = "/login"')
            return

        # Get user permissions
        self.permissions = connection.get_user_permissions(user['role_id'])
        # Fallback: Admin role (usually ID 1 or name 'Admin') gets hide-history by default
        is_admin = user.get('role_name') == 'Admin' or user.get('role_id') == 1
        self.can_hide_history = self.permissions.get('hide-history', False) or is_admin
        self.can_view_profit_analytics = self.permissions.get('profit-analytics', False) or is_admin
        allowed_pages = {page for page, can_access in self.permissions.items() if can_access}

        if show_navigation:
            # Create enhanced navigation instance
            navigation = EnhancedNavigation(self.permissions, user)
            navigation.create_navigation_drawer()  # Create drawer first
            navigation.create_navigation_header()  # Then create header with toggle button

        self.service = PurchaseService()
        self.max_purchase_id = self.get_max_purchase_id()

        self.currency_rows = []
        self.currency_exchange_rates = {}
        self.currency_symbols = {}
        self.default_currency_id = 1
        self.ll_currency_id = None
        self.load_currencies()
        self.previous_currency_id = self.default_currency_id

        # --- Global Variables ---
        self.columns = [
            {'headerName': 'Barcode', 'field': 'barcode', 'width': 100, 'headerClass': 'blue-header'},
            {'headerName': 'Product', 'field': 'product', 'width': 150, 'headerClass': 'blue-header'},
            {'headerName': 'Qty', 'field': 'quantity', 'width': 60,  'headerClass': 'blue-header'},
            {'headerName': 'Cost HT', 'field': 'cost', 'width': 80,  'headerClass': 'blue-header'},
            {'headerName': 'Retail TTC', 'field': 'price', 'width': 90,  'headerClass': 'blue-header'},
            {'headerName': 'Disc %', 'field': 'discount_pct', 'width': 70,  'headerClass': 'blue-header'},
            {'headerName': 'VAT %', 'field': 'vat_percentage', 'width': 70,  'headerClass': 'blue-header'},
            {'headerName': 'VAT Amt', 'field': 'vat_amount', 'width': 80,  'headerClass': 'blue-header'},
            {'headerName': 'Subtotal HT', 'field': 'subtotal', 'width': 100,  'headerClass': 'blue-header'}
        ]
        self.supplier_rows = []
        self.supplier_grid = None
        self.current_supplier_id = None
        self.product_rows = []
        self.product_grid = None
        self.rows = []
        self.all_purchase_data = [] # Store full purchase history for filtering
        self.total_amount = 0
        self.total_quantity = 0
        self.total_items = 0
        self.grid_readonly = False
        self.new_mode = False
        self.current_purchase_id = None

        # Initialize UI
        self.create_ui()

    def load_currencies(self):
        try:
            self.currency_rows = []
            connection.contogetrows("SELECT id, currency_name, symbol, exchange_rate FROM currencies", self.currency_rows)
            self.currency_exchange_rates = {row[0]: float(row[3]) for row in self.currency_rows}
            self.currency_symbols = {row[2]: row[0] for row in self.currency_rows}
            # Find L.L. currency by symbol or highest exchange rate
            self.ll_currency_id = None
            for row in self.currency_rows:
                sym = row[2].strip()
                if sym in ('L.L.', 'LL', 'LBP', 'ل.ل.'):
                    self.ll_currency_id = row[0]
                    self.default_currency_id = row[0]
                    break
            else:
                if self.currency_rows:
                    max_rate = max(self.currency_rows, key=lambda r: float(r[3]) if r[3] else 0)
                    if float(max_rate[3]) > 1:
                        self.ll_currency_id = max_rate[0]
                self.default_currency_id = self.currency_rows[0][0] if self.currency_rows else 1
        except Exception as e:
            ui.notify(f'Error loading currencies: {e}', color='red')
            self.currency_rows = []
            self.currency_exchange_rates = {}
            self.currency_symbols = {}
            self.default_currency_id = 1

    def on_currency_change(self):
        if self.previous_currency_id != self.currency_select.value:
            # Get exchange rates
            old_rate = self.currency_exchange_rates.get(self.previous_currency_id, 1.0)
            new_rate = self.currency_exchange_rates.get(self.currency_select.value, 1.0)

            # Convert all prices from old currency to new currency
            for row in self.rows:
                # Prices are in old currency, convert to base then to new
                row['cost'] = row['cost'] / old_rate * new_rate
                row['price'] = row['price'] / old_rate * new_rate
                row['discount'] = row['discount'] / old_rate * new_rate
                row['vat_amount'] = row['vat_amount'] / old_rate * new_rate
                
                discount_amount = row['quantity'] * row['cost'] * (row['discount_pct'] / 100)
                base_sub = row['quantity'] * row['cost'] - discount_amount
                row['subtotal'] = base_sub + row['vat_amount']

            self.aggrid.update()
            self.update_totals()
            self.previous_currency_id = self.currency_select.value

    def get_current_currency_symbol(self):
        selected_currency_id = self.currency_select.value
        for row in self.currency_rows:
            if row[0] == selected_currency_id:
                return row[2]
        return '$'

    def generate_invoice_number(self):
        return self.service.generate_invoice_number()

    def add_product(self, e=None):
        try:
            barcode = self.barcode_input.value
            product_name = self.product_input.value
            quantity = int(self.quantity_input.value) if self.quantity_input.value else 0
            discount_pct = float(self.discount_input.value or 0)
            cost = float(self.cost_input.value) if self.cost_input.value else 0
            price = float(self.price_input.value) if self.price_input.value else 0
            
            if not barcode or not product_name or quantity <= 0 or cost <= 0:
                ui.notify('Please fill in all required fields with valid values')
                return
            
            product_info = self.service.get_product_by_barcode(barcode)
            vat_percentage = product_info.get('vat_percentage', 0) if product_info else 0
            is_vat = product_info.get('is_vat_subjected', False) if product_info else False
            
            discount_amount = quantity * cost * (discount_pct / 100)
            base_subtotal = quantity * cost - discount_amount
            vat_amount = base_subtotal * (vat_percentage / 100) if is_vat else 0
            subtotal = base_subtotal # HT
            
            self.rows.append({
                'barcode': barcode,
                'product': product_name,
                'quantity': quantity,
                'discount': discount_amount,
                'discount_pct': discount_pct,
                'cost': cost,
                'price': price,
                'vat_percentage': vat_percentage if is_vat else 0,
                'vat_amount': vat_amount,
                'subtotal': subtotal,
                'profit': price - cost
            })
            
            # IMPORTANT for AG Grid to refresh reliably:
            # re-assign rowData to a new reference and then call update().
            try:
                self.aggrid.options['rowData'] = self.rows  # list reference used by salesui_aggrid_compact
            except Exception:
                pass
            self.total_amount += subtotal
            self.update_totals()
            
            self.clear_inputs_inputs()
            
            # Force refresh (new reference)
            try:
                self.aggrid.options['rowData'] = list(self.rows)
            except Exception:
                self.aggrid.options['rowData'] = self.rows
            self.aggrid.update()

            # Back to barcode for next scan/workflow
            try:
                self.barcode_input.run_method('focus')
                ui.timer(0.01, lambda: self.barcode_input.run_method('select'), once=True)
            except Exception:
                pass
            
        except ValueError as e:
            ui.notify(f'Invalid input: {str(e)}')
        except Exception as e:
            ui.notify(f'Error adding product: {str(e)}')

    def clear_inputs_inputs(self):
        self.barcode_input.value = ''
        self.product_input.value = ''
        self.quantity_input.value = 1
        self.discount_input.value = 0
        self.cost_input.value = 0.0
        self.price_input.value = 0.0
    
    def clear_inputs(self):
        if hasattr(self, 'action_bar'):
            self.action_bar.enter_new_mode()
        self.purchase_history_aggrid.classes('dimmed')
        self.supplier_input.value = ''
        self.phone_input.value = ''
        self.reference_input.value = ''
        self.barcode_input.value = ''
        self.product_input.value = ''
        self.quantity_input.value = 1
        self.discount_input.value = 0
        self.cost_input.value = 0.0
        self.price_input.value = 0.0
        self.date_input.value = datetime.now().strftime('%Y-%m-%d')
        
        self.rows.clear()
        self.aggrid.options['rowData'] = self.rows
        self.aggrid.update()

        self.total_amount = 0
        self.discount_percent_input.value = 0
        self.discount_amount_input.value = 0
        if hasattr(self, 'discount_type_toggle'):
            self.discount_type_toggle.value = 'Amount'
            self.discount_percent_input.visible = False
            self.discount_amount_input.visible = True
        if hasattr(self, 'll_total_input'):
            self.ll_total_input.value = 0
        self.update_totals()
        
        self.current_purchase_id = None
        self.new_mode=True

    def update_product_dropdown(self, e):
        try:
            barcode = self.barcode_input.value
            if barcode:
                product_data = []
                connection.contogetrows(
                    f"SELECT barcode, product_name, cost_price, price FROM products WHERE barcode = '{barcode}'", 
                    product_data
                )
                
                if product_data:
                    product = product_data[0]
                    self.product_input.value = product[1]
                    self.discount_input.value = 0
                    self.cost_input.value = float(product[2])
                    self.price_input.value = float(product[3])
                    
                    # Store VAT info for this product if needed (can also be fetched in add_product)
                    # For now just notify
                    if product[6]: # is_vat_subjected
                        ui.notify(f"Product has VAT: {product[7]}%")


                    # Get selected currency info
                    selected_currency_id = self.currency_select.value
                    exchange_rate = float(self.currency_exchange_rates.get(selected_currency_id, 1.0))
                    
                    self.cost_input.value = self.cost_input.value * exchange_rate
                    self.price_input.value = self.price_input.value * exchange_rate

                    ui.notify(f"Product loaded: {product[1]}")
                else:
                    self.discount_input.value = 0
                    ui.notify("Product not found for this barcode")
        except Exception as e:
            ui.notify(f'Error updating product: {str(e)}')

    async def on_row_click_edit_cells(self, e):
        try:
            selected_row = await self.aggrid.get_selected_row()
            if selected_row:
                self.open_edit_dialog(selected_row)
        except Exception as ex:
            ui.notify(f"Error opening edit dialog: {str(ex)}")

    def open_product_dialog(self):
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-6xl glass p-6 border border-white/10').style('background: rgba(15, 15, 25, 0.82); backdrop-filter: blur(20px); border-radius: 2rem;'):
            ui.label('Product Catalog').classes('text-2xl font-black mb-6 text-white').style('font-family: "Outfit", sans-serif;')

            with ui.row().classes('w-full items-center gap-3 bg-white/5 px-4 py-2 rounded-xl border border-white/10 mb-4'):
                ui.icon('search', size='1.25rem').classes('text-purple-400')
                search_input = ui.input(placeholder='Search by name or barcode...').props('borderless dense autocomplete="off"').classes('flex-1 text-white text-sm')\
                    .on_value_change(lambda e: self.filter_product_rows(e.value))\
                    .on('keydown.down', lambda: self._product_search_arrow_down(dialog))\
                    .on('keydown.enter', lambda: self._product_search_enter(dialog))
                search_input.run_method('focus')

            data = []
            connection.contogetrows("SELECT barcode, product_name, stock_quantity, cost_price, price FROM products", data)

            self.product_rows = []
            for row in data:
                self.product_rows.append({
                    'barcode': row[0],
                    'product_name': row[1],
                    'stock_quantity': row[2],
                    'cost_price': row[3],
                    'price': row[4]
                })

            columns = [
                {'name': 'barcode', 'label': 'Barcode', 'field': 'barcode', 'align': 'left'},
                {'name': 'product_name', 'label': 'Product', 'field': 'product_name', 'align': 'left'},
                {'name': 'stock_quantity', 'label': 'Stock', 'field': 'stock_quantity', 'align': 'center'},
                {'name': 'cost_price', 'label': 'Cost', 'field': 'cost_price', 'align': 'right'},
                {'name': 'price', 'label': 'Retail', 'field': 'price', 'align': 'right'}
            ]

            with ui.element('div').classes('w-full h-96 overflow-hidden flex flex-col'):
                with ui.element('div').classes('flex-1 overflow-auto min-h-0'):
                    self.product_grid = ui.table(
                        columns=columns,
                        rows=self.product_rows,
                        row_key='barcode',
                        selection='single'
                    ).classes('w-full h-full bg-transparent overflow-hidden').props('virtual-scroll flat bordered dense hide-pagination :pagination="{rowsPerPage: 0}"')

            # --- Category-style keyboard navigation + highlight (Sales methodology) ---
            state = {'selected_idx': 0}

            def apply_highlight_js():
                idx = state['selected_idx']
                ui.run_javascript(f"""
                    try {{
                      const root = document.getElementById('{getattr(self.product_grid, "id", "")}') || document.querySelector('.q-table');
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
                if not getattr(self.product_grid, 'rows', None):
                    return
                if len(self.product_grid.rows) == 0:
                    return
                state['selected_idx'] = max(0, min(state['selected_idx'], len(self.product_grid.rows) - 1))
                row = self.product_grid.rows[state['selected_idx']]
                self.product_grid.selected = [row]
                self.product_grid.update()
                self.product_grid.run_method('scrollTo', state['selected_idx'])
                apply_highlight_js()

            def on_click_row(e):
                # Keep state in sync so Enter always selects the clicked row
                try:
                    clicked_row = e.args[1] if isinstance(e.args, (list, tuple)) and len(e.args) > 1 else None
                    if isinstance(clicked_row, dict) and clicked_row.get('barcode') is not None and self.product_grid.rows:
                        for i, r in enumerate(self.product_grid.rows):
                            if r.get('barcode') == clicked_row.get('barcode'):
                                state['selected_idx'] = i
                                break
                        apply_highlight_js()
                except Exception:
                    pass

                self.handle_product_grid_click({'args': {'data': e.args[1]}}, dialog)

            self.product_grid.on('rowClick', on_click_row)

            # initial select
            ui.timer(0.05, select_and_scroll, once=True)

            # Focus + attach keydown listener to table root
            grid_id = getattr(self.product_grid, 'id', '')
            ui.run_javascript(f"""
                window.__product_dialog_active = true;
                try {{
                  const root = document.getElementById('{grid_id}') || document.querySelector('.q-table');
                  if (root) {{
                    root.tabIndex = 0;
                    try {{ root.style.outline = 'none'; }} catch(e) {{}}
                    try {{ root.style.caretColor = 'transparent'; }} catch(e) {{}}

                    root.addEventListener('keydown', (ev) => {{
                      if (!window.__product_dialog_active) return;
                      if (ev.key !== 'ArrowDown' && ev.key !== 'ArrowUp' && ev.key !== 'Enter') return;
                      ev.preventDefault();

                      const rows = root.querySelectorAll('tbody tr');
                      if (!rows || rows.length === 0) return;

                      let cur = parseInt(root.dataset.selIdx || '0', 10);
                      if (isNaN(cur)) cur = 0;

                      if (ev.key === 'ArrowDown') cur = Math.min(cur + 1, rows.length - 1);
                      if (ev.key === 'ArrowUp') cur = Math.max(cur - 1, 0);
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
                        if (selected) {{ selected.dispatchEvent(new MouseEvent('click', {{ bubbles: true, cancelable: true, view: window }})); }}
                      }}
                    }});
                    root.focus();
                  }}
                }} catch (e) {{}}
            """)

            with ui.row().classes('w-full justify-end mt-6'):
                ui.button(
                    'Cancel',
                    on_click=lambda: (ui.run_javascript('window.__product_dialog_active=false;'), dialog.close())
                ).props('flat text-color=white').classes('px-6 rounded-xl hover:bg-white/5')
        dialog.open()
        ui.run_javascript('window.__product_dialog_active = true;')

    def handle_product_grid_click(self, e, dialog):
        # Keep this method payload-compatible with SalesUI methodology:
        # - most common: {'args': {'data': {...}}}
        # - sometimes event payload carries row dict directly
        try:
            row = None

            if isinstance(e, dict):
                if 'args' in e and isinstance(e.get('args'), dict):
                    row = e['args'].get('data') or e['args'].get('row') or e['args'].get('item')
                if row is None and all(k in e for k in ('product_name', 'barcode')):
                    row = e

            if row is None:
                args_obj = getattr(e, 'args', None)
                if isinstance(args_obj, dict):
                    row = args_obj.get('data') or args_obj.get('row')

            if row is None:
                data_obj = getattr(e, 'data', None)
                if isinstance(data_obj, dict):
                    row = data_obj

            if not isinstance(row, dict):
                raise TypeError(f"Unexpected selection payload type={type(e)}")

            self.product_input.value = row.get('product_name', '')
            self.barcode_input.value = row.get('barcode', '')
            self.discount_input.value = 0
            self.cost_input.value = row.get('cost_price', 0)
            self.price_input.value = row.get('price', 0)

            # Convert to selected currency if needed
            selected_currency_id = self.currency_select.value
            exchange_rate = float(self.currency_exchange_rates.get(selected_currency_id, 1.0))

            self.cost_input.value = float(self.cost_input.value) * exchange_rate
            self.price_input.value = float(self.price_input.value) * exchange_rate

            dialog.close()

            # Continue keyboard flow: Qty -> select value
            try:
                self.quantity_input.run_method('focus')
                ui.timer(0.01, lambda: self.quantity_input.run_method('select'), once=True)
            except Exception:
                pass

            ui.notify(f"Added product: {self.product_input.value}")
        except Exception as ex:
            ui.notify(f"Selection error: {ex}")
            try:
                dialog.close()
            except Exception:
                pass

    def open_supplier_dialog(self):
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-4xl glass p-6 border border-white/10').style('background: rgba(15, 15, 25, 0.8); backdrop-filter: blur(20px); border-radius: 2rem;'):
            ui.label('Select Supplier').classes('text-2xl font-black mb-6 text-white').style('font-family: "Outfit", sans-serif;')
            
            with ui.row().classes('w-full items-center gap-3 bg-white/5 px-4 py-2 rounded-xl border border-white/10 mb-4'):
                ui.icon('search', size='1.25rem').classes('text-purple-400')
                search_input = ui.input(placeholder='Search by name or phone...').props('borderless dense autocomplete="off"').classes('flex-1 text-white text-sm')\
                    .on_value_change(lambda e: self.filter_supplier_rows(e.value))\
                    .on('keydown.down', lambda: self._supplier_search_arrow_down(dialog))\
                    .on('keydown.enter', lambda: self._supplier_search_enter(dialog))
                search_input.run_method('focus')
            
            data = []
            connection.contogetrows("SELECT id, name, phone, balance, balance_usd FROM suppliers", data)
            
            self.supplier_rows = []
            for row in data:
                self.supplier_rows.append({
                    'id': row[0],
                    'name': row[1],
                    'phone': row[2],
                    'balance_ll': row[3] or 0,
                    'balance_usd': row[4] or 0
                })
            
            columns = [
                {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left'},
                {'name': 'name', 'label': 'Name', 'field': 'name', 'align': 'left'},
                {'name': 'phone', 'label': 'Phone', 'field': 'phone', 'align': 'left'},
                {'name': 'balance_ll', 'label': 'Balance LL', 'field': 'balance_ll', 'align': 'right'},
                {'name': 'balance_usd', 'label': 'Balance USD', 'field': 'balance_usd', 'align': 'right'}
            ]
            
            with ui.element('div').classes('w-full h-80 overflow-hidden flex flex-col'):
                with ui.element('div').classes('flex-1 overflow-auto min-h-0'):
                    self.supplier_grid = ui.table(
                        columns=columns,
                        rows=self.supplier_rows,
                        row_key='id',
                        selection='single'
                    ).classes('w-full h-full bg-transparent overflow-hidden').props('virtual-scroll flat bordered dense hide-pagination :pagination="{rowsPerPage: 0}"')
            
            state = {'selected_idx': 0}
            
            def apply_highlight_js():
                idx = state['selected_idx']
                ui.run_javascript(f"""
                    try {{
                      const root = document.getElementById('{getattr(self.supplier_grid, "id", "")}') || document.querySelector('.q-table');
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
                if not getattr(self.supplier_grid, 'rows', None):
                    return
                if len(self.supplier_grid.rows) == 0:
                    return
                state['selected_idx'] = max(0, min(state['selected_idx'], len(self.supplier_grid.rows) - 1))
                row = self.supplier_grid.rows[state['selected_idx']]
                self.supplier_grid.selected = [row]
                self.supplier_grid.update()
                self.supplier_grid.run_method('scrollTo', state['selected_idx'])
                apply_highlight_js()
            
            def on_click_row(e):
                try:
                    clicked_row = None
                    if isinstance(getattr(e, 'args', None), (list, tuple)) and len(e.args) > 1:
                        clicked_row = e.args[1]
                    if isinstance(clicked_row, dict) and clicked_row.get('id') is not None and self.supplier_grid.rows:
                        for i, r in enumerate(self.supplier_grid.rows):
                            if r.get('id') == clicked_row.get('id'):
                                state['selected_idx'] = i
                                break
                        apply_highlight_js()
                except Exception:
                    pass
                
                try:
                    self.handle_supplier_grid_click({'args': {'data': e.args[1]}}, dialog)
                except Exception:
                    pass
            
            self.supplier_grid.on('rowClick', on_click_row)
            
            ui.timer(0.05, select_and_scroll, once=True)
            
            grid_id = getattr(self.supplier_grid, 'id', '')
            ui.run_javascript(f"""
                window.__supplier_dialog_active = true;
                try {{
                  const root = document.getElementById('{grid_id}') || document.querySelector('.q-table');
                  if (root) {{
                    root.tabIndex = 0;
                    try {{ root.style.outline = 'none'; }} catch(e) {{}}
                    try {{ root.style.caretColor = 'transparent'; }} catch(e) {{}}
                    root.dataset.selIdx = root.dataset.selIdx || '0';
                    root.addEventListener('keydown', (ev) => {{
                      if (!window.__supplier_dialog_active) return;
                      if (ev.key !== 'ArrowDown' && ev.key !== 'ArrowUp' && ev.key !== 'Enter') return;
                      ev.preventDefault();

                      const rows = root.querySelectorAll('tbody tr');
                      if (!rows || rows.length === 0) return;

                      let cur = parseInt(root.dataset.selIdx || '0', 10);
                      if (isNaN(cur)) cur = 0;

                      if (ev.key === 'ArrowDown') cur = Math.min(cur + 1, rows.length - 1);
                      if (ev.key === 'ArrowUp') cur = Math.max(cur - 1, 0);
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
                        if (selected) {{ selected.dispatchEvent(new MouseEvent('click', {{ bubbles: true, cancelable: true, view: window }})); }}
                      }}
                    }});
                    root.focus();
                  }}
                }} catch (e) {{}}
            """)
            
            with ui.row().classes('w-full justify-end mt-6'):
                ui.button(
                    'Cancel',
                    on_click=lambda: (
                        ui.run_javascript('window.__supplier_dialog_active=false;'),
                        dialog.close()
                    )
                ).props('flat text-color=white').classes('px-6 rounded-xl hover:bg-white/5')
        dialog.open()
        ui.run_javascript('window.__supplier_dialog_active = true; console.log("[supplier-table] dialog open");')

    def filter_supplier_rows(self, search_text):
        if not search_text:
            filtered_rows = self.supplier_rows
        else:
            filtered_rows = [
                row for row in self.supplier_rows
                if any(search_text.lower() in str(value).lower() for value in row.values())
            ]
        self.supplier_grid.rows = filtered_rows
        if hasattr(self.supplier_grid, 'selected'):
            self.supplier_grid.selected = []
        self.supplier_grid.update()

    def filter_product_rows(self, search_text):
        if not search_text:
            filtered_rows = self.product_rows
        else:
            filtered_rows = [
                row for row in self.product_rows
                if any(search_text.lower() in str(value).lower() for value in row.values())
            ]
        self.product_grid.rows = filtered_rows
        if hasattr(self.product_grid, 'selected'):
            self.product_grid.selected = []
        self.product_grid.update()

    def _product_search_arrow_down(self, dialog):
        if not self.product_grid or not self.product_grid.rows:
            return
        row = self.product_grid.rows[0]
        self.product_grid.selected = [row]
        self.product_grid.update()
        self.product_grid.run_method('scrollTo', 0)
        grid_id = getattr(self.product_grid, 'id', '')
        ui.run_javascript(f"""
            try {{
                const root = document.getElementById('{grid_id}') || document.querySelector('.q-table');
                if (!root) return;
                root.focus();
                const rows = root.querySelectorAll('tbody tr');
                if (!rows || rows.length === 0) return;
                rows.forEach(el => {{
                    el.style.backgroundColor = '';
                    el.style.color = '';
                    el.classList.remove('selected-highlight');
                }});
                const first = rows[0];
                if (first) {{
                    first.style.backgroundColor = '#facc15';
                    first.style.color = 'black';
                    first.classList.add('selected-highlight');
                }}
                root.dataset.selIdx = '0';
            }} catch(e) {{}}
        """)

    def _product_search_enter(self, dialog):
        if not self.product_grid or not self.product_grid.rows:
            return
        self.handle_product_grid_click(self.product_grid.rows[0], dialog)

    def _supplier_search_arrow_down(self, dialog):
        if not self.supplier_grid or not self.supplier_grid.rows:
            return
        row = self.supplier_grid.rows[0]
        self.supplier_grid.selected = [row]
        self.supplier_grid.update()
        self.supplier_grid.run_method('scrollTo', 0)
        grid_id = getattr(self.supplier_grid, 'id', '')
        ui.run_javascript(f"""
            try {{
                const root = document.getElementById('{grid_id}') || document.querySelector('.q-table');
                if (!root) return;
                root.focus();
                const rows = root.querySelectorAll('tbody tr');
                if (!rows || rows.length === 0) return;
                rows.forEach(el => {{
                    el.style.backgroundColor = '';
                    el.style.color = '';
                    el.classList.remove('selected-highlight');
                }});
                const first = rows[0];
                if (first) {{
                    first.style.backgroundColor = '#facc15';
                    first.style.color = 'black';
                    first.classList.add('selected-highlight');
                }}
                root.dataset.selIdx = '0';
            }} catch(e) {{}}
        """)

    def _supplier_search_enter(self, dialog):
        if not self.supplier_grid or not self.supplier_grid.rows:
            return
        self.handle_supplier_grid_click(self.supplier_grid.rows[0], dialog)

    def handle_supplier_grid_click(self, e, dialog):
        try:
            row = None
            if isinstance(e, dict):
                if 'args' in e and isinstance(e.get('args'), dict):
                    row = e['args'].get('data') or e['args'].get('row')
                if row is None and all(k in e for k in ('id', 'name')):
                    row = e
            elif hasattr(e, 'args'):
                args_obj = getattr(e, 'args', None)
                if isinstance(args_obj, dict):
                    row = args_obj.get('data') or args_obj.get('row')
            
            if not isinstance(row, dict):
                raise TypeError(f"Unexpected supplier selection payload: {type(e)}")
            
            self.supplier_input.value = row.get('name', '')
            self.phone_input.value = row.get('phone', '')
            self.current_supplier_id = row.get('id')
            dialog.close()
            ui.notify(f"Selected: {row.get('name', '')}")
            self.barcode_input.run_method('focus')
        except Exception as ex:
            ui.notify(f"Selection error: {ex}")
            dialog.close()

    def handle_product_grid_click(self, e, dialog):
        try:
            # e can be:
            # - NiceGUI/AgGrid event-like object with .args['data']
            # - dict payload like {'args': {'data': {...}}}
            # - sometimes the row dict directly
            row = None

            if hasattr(e, 'args'):
                args_obj = getattr(e, 'args', None)
                if isinstance(args_obj, dict):
                    row = args_obj.get('data') or args_obj.get('row') or args_obj.get('item')

            if row is None and isinstance(e, dict):
                if 'args' in e and isinstance(e.get('args'), dict):
                    row = e['args'].get('data') or e['args'].get('row')
                else:
                    # Direct row dict
                    if all(k in e for k in ('product_name', 'barcode')):
                        row = e

            if not isinstance(row, dict):
                raise TypeError(f"Unexpected selection payload type={type(e)}")

            self.product_input.value = row.get('product_name', '')
            self.barcode_input.value = row.get('barcode', '')
            self.discount_input.value = 0
            self.cost_input.value = row.get('cost_price', 0)
            self.price_input.value = row.get('price', 0)

            selected_currency_id = self.currency_select.value
            exchange_rate = float(self.currency_exchange_rates.get(selected_currency_id, 1.0))
            
            self.cost_input.value = float(self.cost_input.value) * exchange_rate
            self.price_input.value = float(self.price_input.value) * exchange_rate
            
            dialog.close()

            # Continue keyboard flow: Qty -> select value
            try:
                self.quantity_input.run_method('focus')
                ui.timer(0.01, lambda: self.quantity_input.run_method('select'), once=True)
            except Exception:
                pass

            ui.notify(f"Added product: {self.product_input.value}")
        except Exception as ex:
            ui.notify(f"Selection error: {ex}")
            dialog.close()

    def open_edit_dialog(self, row_data):
        with ui.dialog() as dialog, ui.card().classes('glass p-8 border border-white/10').style('background: rgba(15, 15, 25, 0.82); backdrop-filter: blur(20px); border-radius: 2rem; width: 420px;'):
            with ui.row().classes('w-full items-center justify-between mb-4'):
                ui.label('Edit Product').classes('text-2xl font-black text-white').style('font-family: "Outfit", sans-serif;')
                ui.icon('edit', size='1.5rem').classes('text-purple-400 opacity-80')
            
            ui.label(f"Modifying: {row_data.get('product', 'Unknown')}").classes('text-xs font-bold text-gray-400 uppercase tracking-widest mb-6 block')

            with ui.column().classes('w-full gap-3'):
                quantity = ui.number('Quantity', value=row_data['quantity']).props('outlined dense dark color=purple stack-label').classes('w-full text-white')
                discount_pct = ui.number('Discount %', value=row_data.get('discount_pct', 0), min=0, max=100).props('outlined dense dark color=purple stack-label').classes('w-full text-white')
                cost = ui.number('Unit Cost', value=row_data['cost']).props('outlined dense dark color=purple stack-label').classes('w-full text-white')
                price = ui.number('Retail Price', value=row_data.get('price', 0)).props('outlined dense dark color=purple stack-label').classes('w-full text-white')
                
                def save():
                    self.save_edited_row(row_data, quantity.value, discount_pct.value, cost.value, price.value, dialog)

                def delete():
                    self.delete_row(row_data, dialog)

                with ui.row().classes('w-full justify-end mt-8 gap-3'):
                    ui.button('Delete', on_click=delete).props('flat text-color=red-4').classes('px-4 rounded-xl hover:bg-red-500/10 font-bold text-xs uppercase tracking-widest')
                    ui.button('Cancel', on_click=dialog.close).props('flat text-color=grey-5').classes('px-4 rounded-xl hover:bg-white/5 font-bold text-xs uppercase tracking-widest')
                    ui.button('Update Item', on_click=save).props('unelevated color=purple').classes('px-6 py-2 rounded-xl font-black text-xs uppercase tracking-widest shadow-xl shadow-purple-500/20')
        dialog.open()

    def save_edited_row(self, original_row, new_quantity, new_discount_pct, new_cost, new_price, dialog):
        try:
            row_index = next(i for i, row in enumerate(self.rows) 
                           if row['barcode'] == original_row['barcode'] and 
                              row['product'] == original_row['product'])
            
            self.rows[row_index]['quantity'] = int(new_quantity)
            discount_amount = int(new_quantity) * float(new_cost) * (new_discount_pct / 100)
            self.rows[row_index]['discount'] = discount_amount
            self.rows[row_index]['discount_pct'] = new_discount_pct
            self.rows[row_index]['cost'] = float(new_cost)
            self.rows[row_index]['price'] = float(new_price)
            
            base_sub = int(new_quantity) * float(new_cost) - discount_amount
            vat_pct = self.rows[row_index].get('vat_percentage', 0)
            vat_amount = base_sub * (vat_pct / 100)
            
            self.rows[row_index]['vat_amount'] = vat_amount
            self.rows[row_index]['subtotal'] = base_sub # HT
            self.rows[row_index]['profit'] = float(new_price) - float(new_cost)
            
            self.aggrid.options['rowData'] = self.rows
            self.aggrid.update()
            self.update_totals()
            dialog.close()
            ui.notify('Product updated successfully')
        except Exception as e:
            ui.notify(f'Error updating product: {str(e)}')

    def delete_row(self, row_data, dialog):
        try:
            row_index = next(i for i, row in enumerate(self.rows) 
                           if row['barcode'] == row_data['barcode'] and 
                               row['product'] == row_data['product'])
            
            del self.rows[row_index]
            self.aggrid.options['rowData'] = self.rows
            self.aggrid.update()
            self.update_totals()
            dialog.close()
            ui.notify('Product removed successfully')
        except Exception as e:
            ui.notify(f'Error removing product: {str(e)}')

    def toggle_history(self):
        """Toggle the visibility of the purchase history panel"""
        if hasattr(self, 'history_panel'):
            self.history_panel.visible = not self.history_panel.visible
            if hasattr(self, 'show_history_btn'):
                self.show_history_btn.visible = not self.history_panel.visible
            ui.notify('History ' + ('hidden' if not self.history_panel.visible else 'shown'), color='info', duration=1)

    def update_totals(self, e=None):
        if getattr(self, '_updating_totals', False): return
        self._updating_totals = True
        try:
            total_quantity = sum(row['quantity'] for row in self.rows)
            total_vat = sum(row.get('vat_amount', 0) for row in self.rows)
            subtotal = sum(row['subtotal'] for row in self.rows)

            self.summary_label.text = f"{len(self.rows)} items"
            self.quantity_total_label.text = f"Total Qty: {total_quantity}"

            is_pct_mode = hasattr(self, 'discount_type_toggle') and self.discount_type_toggle.value == '%'
            if is_pct_mode:
                pct = float(self.discount_percent_input.value or 0)
                discount_amount = round(subtotal * pct / 100, 2)
                self.discount_amount_input.value = discount_amount
            else:
                discount_amount = float(self.discount_amount_input.value or 0)
                pct = round((discount_amount / subtotal * 100) if subtotal > 0 else 0, 2)
                self.discount_percent_input.value = pct

            final_total = subtotal - discount_amount + total_vat
            self.total_amount = final_total

            selected_currency_id = self.currency_select.value
            currency_symbol = '$'
            for row in self.currency_rows:
                if row[0] == selected_currency_id:
                    currency_symbol = row[2]
                    break
            if hasattr(self, 'ttc_currency_label'):
                self.ttc_currency_label.text = currency_symbol

            self.subtotal_label.text = f"Total HT: {currency_symbol}{subtotal:.2f}"
            self.vat_label.text = f"VAT: {currency_symbol}{total_vat:.2f}"
            if hasattr(self, 'total_input'):
                self.total_input.value = round(final_total, 2)
            
            if hasattr(self, 'll_total_input') and self.ll_currency_id is not None:
                ll_rate = self.currency_exchange_rates.get(self.ll_currency_id, 1.0)
                selected_rate = self.currency_exchange_rates.get(selected_currency_id, 1.0)
                ll_amount = final_total * (ll_rate / selected_rate)
                self.ll_total_input.value = round(ll_amount, 2)
        finally:
            self._updating_totals = False

    def total_input_changed(self, e):
        if getattr(self, '_updating_totals', False): return
        self._updating_totals = True
        try:
            subtotal = sum(row['subtotal'] for row in self.rows)
            total_vat = sum(row.get('vat_amount', 0) for row in self.rows)
            target_val = float(e.value or 0)
            discount_amt = max(0.0, subtotal + total_vat - target_val)
            discount_pct = round((discount_amt / subtotal * 100) if subtotal > 0 else 0, 2)
            self.discount_amount_input.value = round(discount_amt, 2)
            self.discount_percent_input.value = discount_pct
            self.total_amount = target_val
        finally:
            self._updating_totals = False

    def ll_total_input_changed(self, e):
        if getattr(self, '_updating_totals', False): return
        if self.ll_currency_id is None:
            return
        try:
            ll_val = float(e.value or 0)
            ll_rate = self.currency_exchange_rates.get(self.ll_currency_id, 1.0)
            selected_rate = self.currency_exchange_rates.get(self.currency_select.value, 1.0)
            target_total = ll_val * (selected_rate / ll_rate)
            self.total_input.value = round(target_total, 2)
            subtotal = sum(row['subtotal'] for row in self.rows)
            total_vat = sum(row.get('vat_amount', 0) for row in self.rows)
            discount_amt = max(0.0, subtotal + total_vat - target_total)
            discount_pct = round((discount_amt / subtotal * 100) if subtotal > 0 else 0, 2)
            self.discount_amount_input.value = round(discount_amt, 2)
            self.discount_percent_input.value = discount_pct
            self.total_amount = round(target_total, 2)
            self.update_totals()
        except Exception:
            pass

    def _on_discount_mode_change(self, e):
        is_pct = e.value == '%'
        self.discount_amount_input.visible = not is_pct
        self.discount_percent_input.visible = is_pct
        self.update_totals()

    def get_max_purchase_id(self):
        return self.service.get_max_purchase_id()

    def show_undo_confirmation(self):
        with ui.dialog() as dialog, ui.card().classes('glass p-8 border border-white/10').style('background: rgba(15, 15, 25, 0.82); backdrop-filter: blur(20px); border-radius: 2rem; width: 400px;'):
            with ui.row().classes('w-full items-center justify-between mb-4'):
                ui.label('Undo Changes').classes('text-2xl font-black text-white').style('font-family: "Outfit", sans-serif;')
                ui.icon('undo', size='1.5rem').classes('text-warning opacity-80')
            
            ui.label('Are you sure you want to clear the current purchase and undo all changes?').classes('text-sm text-gray-300 mb-8 block font-medium')

            with ui.row().classes('w-full justify-end gap-3'):
                ui.button('Cancel', on_click=dialog.close).props('flat text-color=grey-5').classes('px-4 rounded-xl hover:bg-white/5 font-bold text-xs uppercase tracking-widest')
                ui.button('Yes, Undo', on_click=lambda: self.perform_undo(dialog)).props('unelevated color=warning').classes('px-6 py-2 rounded-xl font-black text-xs uppercase tracking-widest shadow-xl shadow-warning/20')
        dialog.open()

    def perform_undo(self, dialog):
        self.clear_inputs()
        dialog.close()
        self.purchase_history_aggrid.classes(remove='dimmed')
        ui.notify('Undo completed successfully')
        if hasattr(self, 'action_bar'):
            self.action_bar.reset_state()

    def delete_purchase(self):
        try:
            purchase_id = self.current_purchase_id or self.get_max_purchase_id()
            if not purchase_id:
                ui.notify('No purchase data available to delete')
                return
            
            with ui.dialog() as dialog, ui.card().classes('glass p-8 border border-white/10').style('background: rgba(15, 15, 25, 0.82); backdrop-filter: blur(20px); border-radius: 2rem; width: 440px;'):
                with ui.row().classes('w-full items-center justify-between mb-4'):
                    ui.label('Delete Purchase').classes('text-2xl font-black text-white').style('font-family: "Outfit", sans-serif;')
                    ui.icon('warning', size='1.5rem').classes('text-red-500 opacity-80')
                
                ui.label(f'Are you sure you want to delete purchase ID: {purchase_id}?').classes('text-sm text-gray-300 font-bold mb-2 block')
                ui.label('This will permanently remove the purchase and all its items from the database. This action cannot be undone.').classes('text-xs text-gray-400 mb-8 block leading-relaxed')

                with ui.row().classes('w-full justify-end gap-3'):
                    ui.button('No, keep it', on_click=dialog.close).props('flat text-color=grey-5').classes('px-4 rounded-xl hover:bg-white/5 font-bold text-xs uppercase tracking-widest')
                    ui.button('Yes, Delete', on_click=lambda: self.perform_delete_purchase(purchase_id, dialog)).props('unelevated color=negative').classes('px-6 py-2 rounded-xl font-black text-xs uppercase tracking-widest shadow-xl shadow-red-500/20')
            dialog.open()
        except Exception as e:
            ui.notify(f'Error preparing delete: {str(e)}')

    async def perform_delete_purchase(self, purchase_id, dialog):
        async with loading_indicator.show_loading('delete_purchase', 'Deleting purchase...', overlay=True):
            try:
                user = session_storage.get('user')
                msg = self.service.delete_purchase(purchase_id, user['user_id'])
                ui.notify(msg)
                dialog.close()
                self.clear_inputs()
                await self.refresh_purchase_table()
            except Exception as e:
                ui.notify(f'Error deleting purchase: {str(e)}')
                dialog.close()

    async def refresh_purchase_table(self):
        async with loading_indicator.show_loading('refresh_purchase', 'Refreshing purchase data...', overlay=True):
            try:
                purchase_data = self.service.get_all_purchases()
                self.all_purchase_data = purchase_data
                self.purchase_history_aggrid.options['rowData'] = purchase_data
                self.purchase_history_aggrid.update()
                self.purchase_history_aggrid.classes(remove='dimmed')
                self.update_totals()
                ui.notify('Purchase table refreshed successfully')
            except Exception as e:
                ui.notify(f'Error refreshing purchase table: {str(e)}')

    def filter_history_table(self, query):
        target_query = str(query if query is not None else "").lower()
        if hasattr(self, 'purchase_history_aggrid') and hasattr(self, 'all_purchase_data'):
            if not target_query:
                self.purchase_history_aggrid.options['rowData'] = self.all_purchase_data
            else:
                filtered_data = [
                    row for row in self.all_purchase_data 
                    if target_query in str(row['id']).lower() or 
                       target_query in str(row['supplier_name']).lower() or 
                       target_query in str(row['invoice_number']).lower()
                ]
                self.purchase_history_aggrid.options['rowData'] = filtered_data
            self.purchase_history_aggrid.update()

    async def save_purchase(self, is_order=False):
        async with loading_indicator.show_loading('save_purchase', 'Saving purchase...', overlay=True):
            try:
                if not self.rows:
                    ui.notify('No items to save!')
                    return

                supplier_name = self.supplier_input.value
                if not supplier_name:
                    ui.notify('Please select a supplier!')
                    return

                supplier_id = self.service.get_supplier_id(supplier_name)
                # Ensure supplier auxiliary exists for accounting linkage
                import accounting_helpers
                accounting_helpers.ensure_supplier_auxiliary(
                    supplier_id,
                    supplier_name=supplier_name,
                    fallback_account_number='4011'
                )
                selected_currency_id = self.currency_select.value
                
                payment_method = self.payment_method.value
                status = 'Order' if is_order else 'Purchase'
                payment_status = 'pending' if is_order or payment_method != 'Cash' else 'completed'

                invoice_number = self.reference_input.value or self.service.generate_invoice_number()
                data = {
                    'purchase_date': self.date_input.value,
                    'supplier_id': supplier_id,
                    'subtotal': sum(row['subtotal'] for row in self.rows), # Already HT
                    'total_vat': sum(row.get('vat_amount', 0) for row in self.rows),
                    'discount_amount': float(self.discount_amount_input.value or 0),
                    'final_total': self.total_amount,
                    'payment_status': payment_status,
                    'payment_method': 'Cash' if payment_method == 'Cash' else 'On Account',
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'user': session_storage.get('user'),
                    'session_id': session_storage.get('session_id', 'Unknown'),
                    'currency_id': selected_currency_id,
                    'status': status
                }
                data['invoice_number'] = invoice_number

                self.service.save_purchase(data, self.rows, self.current_purchase_id)
                ui.notify(f'{"Order" if is_order else "Purchase"} saved successfully!', color='positive')
                await self.refresh_purchase_table()
                await self.load_max_purchase()
            except Exception as e:
                ui.notify(f'Error saving purchase: {str(e)}')

    async def load_max_purchase(self):
        async with loading_indicator.show_loading('load_max_purchase', 'Loading latest purchase...', overlay=True):
            try:
                max_id = self.get_max_purchase_id()
                if max_id > 0:
                    await self.load_purchase_details(max_id)
            except Exception as e:
                ui.notify(f'Error loading max purchase: {str(e)}')

    async def load_purchase_details(self, purchase_id):
        try:
            details = self.service.get_purchase_details(purchase_id)
            self.current_purchase_id = purchase_id
            self.supplier_input.value = details['supplier_name']
            self.phone_input.value = details['phone']
            pd_val = details['purchase_date']
            if hasattr(pd_val, 'strftime'):
                pd_val = pd_val.strftime('%Y-%m-%d')
            self.date_input.value = str(pd_val).split(' ')[0]
            self.reference_input.value = details['invoice_number']
            self.currency_select.value = details['currency_id']
            self.payment_method.value = 'Cash' if details['payment_status'] == 'completed' else 'On Account'
            
            for row in details['rows']:
                # Ensure discount_pct for display if missing
                if 'discount_pct' not in row:
                    row['discount_pct'] = (row.get('discount', 0) / (row['quantity'] * row['cost']) * 100) if row['quantity'] * row['cost'] > 0 else 0
            
            self.rows = details['rows']
            self.aggrid.options['rowData'] = self.rows
            self.aggrid.update()

            saved_discount = float(details.get('discount_amount', 0))
            self.discount_percent_input.value = 0
            self.discount_amount_input.value = round(saved_discount, 2)
            if hasattr(self, 'discount_type_toggle'):
                self.discount_type_toggle.value = 'Amount'
                self.discount_percent_input.visible = False
                self.discount_amount_input.visible = True

            self.update_totals()
            ui.notify(f'Loaded Purchase ID: {purchase_id}')
        except Exception as e:
            ui.notify(f'Error loading purchase details: {e}')

    def show_statistics_dialog(self):
        try:
            selected_currency_id = self.currency_select.value
            exchange_rate = float(self.currency_exchange_rates.get(selected_currency_id, 1.0))
            selected_currency_symbol = '$'
            for c_row in self.currency_rows:
                if c_row[0] == selected_currency_id:
                    selected_currency_symbol = c_row[2]
                    break

            today_str = dt.today().isoformat()

            with ui.dialog() as dialog, ui.card().classes('glass p-8 border border-white/10').style('background: rgba(15, 15, 25, 0.82); backdrop-filter: blur(20px); border-radius: 2rem; width: 520px; max-width: 95vw;'):
                with ui.row().classes('w-full items-center justify-between mb-4'):
                    ui.label('Statistics').classes('text-2xl font-black text-white').style('font-family: "Outfit", sans-serif;')
                    ui.icon('bar_chart', size='1.5rem').classes('text-purple-400 opacity-80')

                ui.label('PURCHASE STATISTICAL PRESENTATION').classes('text-[10px] font-black text-gray-400 uppercase tracking-widest mb-6 block font-medium')

                with ui.row().classes('w-full gap-4 mb-4'):
                    with ui.column().classes('gap-1 flex-1'):
                        ui.label('From Date').classes('text-[8px] text-gray-500 font-bold uppercase tracking-tighter')
                        from_date = ui.input(value=today_str).props('type=date outlined dense dark').classes('w-full')
                    with ui.column().classes('gap-1 flex-1'):
                        ui.label('To Date').classes('text-[8px] text-gray-500 font-bold uppercase tracking-tighter')
                        to_date = ui.input(value=today_str).props('type=date outlined dense dark').classes('w-full')

                with ui.row().classes('w-full gap-4 mb-4'):
                    with ui.column().classes('gap-1 flex-1'):
                        ui.label('From Time').classes('text-[8px] text-gray-500 font-bold uppercase tracking-tighter')
                        from_time = ui.input(value='00:00').props('type=time outlined dense dark').classes('w-full')
                    with ui.column().classes('gap-1 flex-1'):
                        ui.label('To Time').classes('text-[8px] text-gray-500 font-bold uppercase tracking-tighter')
                        to_time = ui.input(value='23:59').props('type=time outlined dense dark').classes('w-full')

                with ui.row().classes('w-full gap-4 mb-4'):
                    with ui.column().classes('gap-1 flex-1'):
                        ui.label('User').classes('text-[8px] text-gray-500 font-bold uppercase tracking-tighter')
                        user_data = []
                        connection.contogetrows("SELECT id, username FROM users ORDER BY username", user_data)
                        user_dict = {u[0]: u[1] for u in user_data}
                        user_select = ui.select({**{0: 'All Users'}, **user_dict}, value=0).props('outlined dense dark').classes('w-full')
                    with ui.column().classes('gap-1 flex-1'):
                        ui.label('Supplier').classes('text-[8px] text-gray-500 font-bold uppercase tracking-tighter')
                        supp_data = []
                        connection.contogetrows("SELECT id, name FROM suppliers ORDER BY name", supp_data)
                        supp_dict = {s[0]: s[1] for s in supp_data}
                        supplier_select = ui.select({**{0: 'All Suppliers'}, **supp_dict}, value=0).props('outlined dense dark').classes('w-full')

                calc_row = ui.row().classes('w-full justify-center mb-6')
                with calc_row:
                    calculate_btn = ui.button('Calculate', icon='calculate').props('flat').classes('px-8 rounded-xl bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 font-black text-xs uppercase tracking-widest')

                with ui.column().classes('w-full gap-3'):
                    with ui.row().classes('w-full justify-between items-center bg-white/5 p-4 rounded-2xl border border-white/10 shadow-inner'):
                        with ui.column().classes('gap-0'):
                            ui.label('Total Purchases').classes('text-[8px] text-gray-400 font-bold uppercase tracking-tighter')
                            total_purchases_label = ui.label('--').classes('text-sm font-black text-white')
                        with ui.column().classes('gap-0 items-end'):
                            ui.label('Total Profit').classes('text-[8px] text-gray-400 font-bold uppercase tracking-tighter')
                            total_profit_label = ui.label('--').classes('text-sm font-black text-green-400')

                    with ui.row().classes('w-full justify-between items-center px-4'):
                        with ui.column().classes('gap-0'):
                            ui.label('Total Purchase Discount').classes('text-[8px] text-gray-400 font-bold uppercase tracking-tighter')
                            total_discount_label = ui.label('--').classes('text-sm font-black text-red-400')
                        with ui.column().classes('gap-0 items-end'):
                            ui.label('Cash Box Pay Payment').classes('text-[8px] text-gray-400 font-bold uppercase tracking-tighter')
                            cash_box_label = ui.label('--').classes('text-sm font-black text-blue-400')

                    with ui.row().classes('w-full justify-between items-center px-4'):
                        with ui.column().classes('gap-0'):
                            ui.label('On Account Amount').classes('text-[8px] text-gray-400 font-bold uppercase tracking-tighter')
                            on_account_label = ui.label('--').classes('text-sm font-black text-yellow-400')
                        with ui.column().classes('gap-0 items-end'):
                            ui.label('Supplier Payments').classes('text-[8px] text-gray-400 font-bold uppercase tracking-tighter')
                            settlement_label = ui.label('--').classes('text-sm font-black text-cyan-400')

                    with ui.row().classes('w-full justify-center items-center bg-green-500/10 p-4 rounded-2xl border border-green-500/30 mt-2'):
                        with ui.column().classes('items-center gap-0'):
                            ui.label('TOTAL PAID').classes('text-[8px] text-gray-400 font-bold uppercase tracking-tighter')
                            total_paid_label = ui.label('--').classes('text-lg font-black text-white')

                    def do_calculate():
                        try:
                            fd = from_date.value
                            td = to_date.value
                            ft = from_time.value
                            tt = to_time.value
                            usr_val = user_select.value
                            supp_val = supplier_select.value

                            from_dt_str = f"{fd} {ft}:00"
                            to_dt_str = f"{td} {tt}:00"

                            where_clauses = ["p.status = 'Purchase'", "p.purchase_date >= ?", "p.purchase_date <= ?"]
                            params = [from_dt_str, to_dt_str]

                            if supp_val and supp_val != 0:
                                where_clauses.append("p.supplier_id = ?")
                                params.append(supp_val)

                            if usr_val and usr_val != 0:
                                where_clauses.append("p.user_id = ?")
                                params.append(usr_val)

                            where_sql = " AND ".join(where_clauses)

                            # Total purchases & discount
                            purch_data = []
                            connection.contogetrows(
                                f"SELECT COALESCE(SUM(p.total_amount), 0), COALESCE(SUM(p.discount_amount), 0) FROM purchases p WHERE {where_sql}",
                                purch_data, tuple(params)
                            )
                            total_purchases = float(purch_data[0][0]) if purch_data and purch_data[0][0] else 0.0
                            total_discount = float(purch_data[0][1]) if purch_data and purch_data[0][1] else 0.0

                            # Profit = retail value - cost value (stored in purchase_items)
                            cost_retail_data = []
                            connection.contogetrows(
                                f"SELECT COALESCE(SUM(pi.quantity * pi.unit_cost), 0), COALESCE(SUM(pi.quantity * pi.unit_price), 0) FROM purchase_items pi JOIN purchases p ON p.id = pi.purchase_id WHERE {where_sql}",
                                cost_retail_data, tuple(params)
                            )
                            total_cost = float(cost_retail_data[0][0]) if cost_retail_data and cost_retail_data[0][0] else 0.0
                            total_retail = float(cost_retail_data[0][1]) if cost_retail_data and cost_retail_data[0][1] else 0.0
                            total_profit = total_retail - total_cost

                            # Cash box payments (Out) = money paid to suppliers
                            cash_out_data = []
                            connection.contogetrows(
                                "SELECT COALESCE(SUM(cdo.amount), 0) FROM cash_drawer_operations cdo WHERE cdo.operation_type = 'Out' AND cdo.operation_date >= ? AND cdo.operation_date <= ?",
                                cash_out_data, (from_dt_str, to_dt_str)
                            )
                            cash_box = float(cash_out_data[0][0]) if cash_out_data and cash_out_data[0][0] else 0.0

                            # On Account (pending payment purchases)
                            on_acct_data = []
                            connection.contogetrows(
                                f"SELECT COALESCE(SUM(p.total_amount), 0) FROM purchases p WHERE {where_sql} AND p.payment_status = 'pending'",
                                on_acct_data, tuple(params)
                            )
                            on_account = float(on_acct_data[0][0]) if on_acct_data and on_acct_data[0][0] else 0.0

                            # Supplier payments (payments made to suppliers)
                            supp_pay_where = ["sp.payment_date >= ?", "sp.payment_date <= ?"]
                            supp_pay_params = [from_dt_str, to_dt_str]
                            if supp_val and supp_val != 0:
                                supp_pay_where.append("sp.supplier_id = ?")
                                supp_pay_params.append(supp_val)
                            supp_pay_data = []
                            connection.contogetrows(
                                f"SELECT COALESCE(SUM(sp.amount), 0) FROM supplier_payment sp WHERE {' AND '.join(supp_pay_where)}",
                                supp_pay_data, tuple(supp_pay_params)
                            )
                            supplier_payments = float(supp_pay_data[0][0]) if supp_pay_data and supp_pay_data[0][0] else 0.0

                            total_paid = cash_box + supplier_payments

                            total_purchases_label.set_text(f"{selected_currency_symbol}{total_purchases:,.2f}")
                            total_profit_label.set_text(f"{selected_currency_symbol}{total_profit:,.2f}")
                            total_discount_label.set_text(f"{selected_currency_symbol}{total_discount:,.2f}")
                            cash_box_label.set_text(f"{selected_currency_symbol}{cash_box:,.2f}")
                            on_account_label.set_text(f"{selected_currency_symbol}{on_account:,.2f}")
                            settlement_label.set_text(f"{selected_currency_symbol}{supplier_payments:,.2f}")
                            total_paid_label.set_text(f"{selected_currency_symbol}{total_paid:,.2f}")
                        except Exception as calc_err:
                            ui.notify(f'Calculation error: {str(calc_err)}')
                            print(f'Purchase statistics calc error: {str(calc_err)}')

                    calculate_btn.on_click(do_calculate)

                with ui.row().classes('w-full justify-end mt-8'):
                    ui.button('Dismiss', on_click=dialog.close).props('flat text-color=grey-5').classes('px-6 rounded-xl hover:bg-white/5 font-black text-xs uppercase tracking-widest')

            dialog.open()
        except Exception as e:
            ui.notify(f'Error opening statistics dialog: {str(e)}')
            print(f'Purchase statistics dialog error: {str(e)}')

    def show_profit_dialog(self):
        """Show margin analysis (profit based on retail price)"""
        try:
            if not self.can_view_profit_analytics:
                return ui.notify('Access denied: profit analytics', color='negative')
            total_cost = sum(row['subtotal'] for row in self.rows)
            total_retail = sum(row['quantity'] * row['price'] for row in self.rows)
            profit = total_retail - total_cost
            margin = (profit / total_retail * 100) if total_retail > 0 else 0

            with ui.dialog() as dialog, ui.card().classes('glass p-8 border border-white/10').style('background: rgba(15, 15, 25, 0.82); backdrop-filter: blur(20px); border-radius: 2rem; width: 380px;'):
                with ui.row().classes('w-full items-center justify-between mb-4'):
                    ui.label('Margin Analysis').classes('text-2xl font-black text-white').style('font-family: "Outfit", sans-serif;')
                    ui.icon('trending_up', size='1.5rem').classes('text-green-400 opacity-80')
                
                with ui.column().classes('w-full gap-3'):
                    with ui.row().classes('w-full justify-between items-center bg-white/5 p-4 rounded-2xl border border-white/10 shadow-inner'):
                        with ui.column().classes('gap-0'):
                            ui.label('Potential Profit').classes('text-[8px] text-gray-400 font-bold uppercase tracking-tighter')
                            ui.label(f'${profit:,.2f}').classes('text-2xl font-black text-green-400')
                        
                        with ui.column().classes('gap-0 items-end'):
                            ui.label('Margin').classes('text-[8px] text-gray-400 font-bold uppercase tracking-tighter')
                            ui.label(f'{margin:.2f}%').classes('text-xl font-black text-blue-400')

                    with ui.row().classes('w-full justify-between items-center px-4'):
                        ui.label('Total Cost').classes('text-[10px] text-gray-500 font-bold uppercase tracking-widest')
                        ui.label(f'${total_cost:,.2f}').classes('text-xs font-black text-white px-2 py-1 bg-white/10 rounded-lg')

                with ui.row().classes('w-full justify-end mt-8'):
                    ui.button('Dismiss', on_click=dialog.close).props('flat text-color=grey-5').classes('px-6 rounded-xl hover:bg-white/5 font-black text-xs uppercase tracking-widest')
            dialog.open()
        except Exception as e:
            ui.notify(f'Error: {e}')

    def view_purchase_transaction(self):
        """Open accounting transactions dialog for the current purchase.

        For cash purchases (payment_status='completed'), display the Purchase Payment JV
        so that supplier/caisse directions match cash settlement.
        For on-account purchases, display the Purchase JV.
        """
        if not self.current_purchase_id:
            ui.notify('Select a purchase to view its transaction', color='warning')
            return

        import accounting_helpers
        ref_id = str(self.current_purchase_id)

        # Determine whether this purchase was settled in cash (vs on-account)
        payment_status_rows = []
        connection.contogetrows(
            "SELECT payment_status FROM purchases WHERE id = ?",
            payment_status_rows,
            (self.current_purchase_id,)
        )
        payment_status = payment_status_rows[0][0] if payment_status_rows else None

        # If cash/completed -> show payment JV, else show invoice JV
        if payment_status == 'completed':
            accounting_helpers.show_transactions_dialog(reference_type='Purchase Payment', reference_id=ref_id)
        else:
            accounting_helpers.show_transactions_dialog(reference_type='Purchase', reference_id=ref_id)

    def print_purchase_invoice(self):
        try:
            if not self.rows:
                ui.notify('No items to print!')
                return
            invoice_number = self.invoicenumber or self.generate_invoice_number()
            subtotal = sum(row['subtotal'] for row in self.rows)
            discount_amount = float(self.discount_amount_input.value or 0)
            final_total = self.total_amount
            currency_symbol = self.get_current_currency_symbol()
            
            invoice_items = []
            for item in self.rows:
                invoice_items.append({
                    'Barcode': str(item['barcode']),
                    'Product': str(item['product']),
                    'Quantity': str(item['quantity']),
                    'Price': f"{currency_symbol}{item['cost']:.2f}",
                    'Discount': "0.0%",
                    'Subtotal': f"{currency_symbol}{item['subtotal']:.2f}"
                })
            self.generate_pdf_inline(invoice_number, invoice_items, subtotal, 0, discount_amount, final_total, currency_symbol)
        except Exception as e:
            ui.notify(f'Error generating invoice: {str(e)}')

    def generate_pdf_inline(self, invoice_number, invoice_data, subtotal, discount_percent, discount_amount, final_total, currency_symbol='$'):
        try:
            import base64
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from io import BytesIO

            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=20, rightMargin=20, topMargin=30, bottomMargin=30)
            elements = []
            styles = getSampleStyleSheet()
            
            elements.append(Paragraph(f"Purchase Invoice", styles['Heading1']))
            elements.append(Spacer(1, 12))
            
            supplier_name = self.supplier_input.value or 'N/A'
            elements.append(Paragraph(f"Invoice #: {invoice_number}<br/>Date: {datetime.now().strftime('%Y-%m-%d')}<br/>Supplier: {supplier_name}", styles['Normal']))
            elements.append(Spacer(1, 12))

            table_data = [['Barcode', 'Product', 'Quantity', 'Cost', 'Discount', 'Subtotal']]
            for item in invoice_data:
                table_data.append([item['Barcode'], item['Product'], item['Quantity'], item['Price'], item['Discount'], item['Subtotal']])

            available_width = letter[0] - 40
            col_widths = [available_width * 0.15, available_width * 0.25, available_width * 0.15, available_width * 0.15, available_width * 0.15, available_width * 0.15]
            table = Table(table_data, colWidths=col_widths)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)
            elements.append(Spacer(1, 12))

            totals_data = [['Subtotal:', f"{currency_symbol}{subtotal:.2f}"], ['Discount:', f"{currency_symbol}{discount_amount:.2f}"], ['Grand Total:', f"{currency_symbol}{final_total:.2f}"]]
            totals_table = Table(totals_data, colWidths=[available_width * 0.7, available_width * 0.3])
            totals_table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'RIGHT'), ('FONTNAME', (-1, -1), (-1, -1), 'Helvetica-Bold'), ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
            elements.append(totals_table)

            doc.build(elements)
            pdf_bytes = buffer.getvalue()
            buffer.close()
            from pdf_viewer_helper import show_pdf_modal
            show_pdf_modal(pdf_bytes, filename='Purchase_Invoice.pdf', title='Purchase Invoice PDF')
        except Exception as e:
            ui.notify(f'Error generating PDF: {str(e)}')

    def create_ui(self):
        # Fetch session metadata for footer
        user = session_storage.get('user', {})
        is_employee = user.get('role_name') == 'Employee'
        company_info = connection.get_company_info()
        company_name = company_info.get('company_name', '') if company_info else ''

        uiAggridTheme.addingtheme()  # Apply AG Grid theme for proper row/header alignment
        ui.add_head_html(MDS.get_global_styles())
        ui.add_head_html(f'<script>{MDS.get_theme_switcher_js()}</script>')
        # global helper to store ag-Grid APIs and trigger layout when a hidden grid becomes visible
        ui.add_head_html('''
<script>
window.__aggrid_store = window.__aggrid_store || {};
window.__aggrid_triggerLayout = function(name) {
  try {
    const api = window.__aggrid_store[name];
    if (api) {
      api.sizeColumnsToFit && api.sizeColumnsToFit();
      api.doLayout && api.doLayout();
      api.refreshHeader && api.refreshHeader();
      setTimeout(()=>{ api.sizeColumnsToFit && api.sizeColumnsToFit(); }, 80);
    }
  } catch(e) { console.error('aggrid triggerLayout error', e); }
};
</script>
''')
        # click/tab-change helper: trigger layout for all stored grids when user interacts with tabs
        ui.add_head_html('''
<script>
window.__aggrid_triggerAll = function(){
  try {
    const s = window.__aggrid_store || {};
    for (const k in s) {
      try { s[k].sizeColumnsToFit && s[k].sizeColumnsToFit(); s[k].doLayout && s[k].doLayout(); s[k].refreshHeader && s[k].refreshHeader(); }
      catch(e){console.error('aggrid triggerAll', k, e)}
    }
  } catch(e) { console.error('aggrid triggerAll error', e); }
};

document.addEventListener('click', function(e){
  const t = e.target.closest('[role="tab"], .q-tab, .tab');
  if (!t) return;
  // slight delay to allow tab content to become visible
  setTimeout(()=>{ window.__aggrid_triggerAll && window.__aggrid_triggerAll(); }, 80);
});
</script>
''')
        
        with ui.element('div').classes('w-full mesh-gradient h-[calc(100vh-64px)] p-4 overflow-hidden'):
                    with ui.row().classes('w-full h-full gap-4 overflow-hidden'):
                        with ui.column().classes('flex-1 h-full gap-4 relative overflow-hidden'):
                            with ui.row().classes('w-full gap-4 overflow-hidden').style('height: 600px;'):
                                # LEFT PANEL: Purchase History (35%)
                                self.history_panel = ui.column().classes('w-[35%] h-full gap-4')
                                with self.history_panel:
                                    with ui.column().classes('w-full h-full glass p-4 rounded-3xl border border-white/10 gap-4'):
                                        with ui.row().classes('w-full items-center gap-3 glass p-3 rounded-2xl border border-white/10 hover:bg-white/5 transition-all'):
                                            ui.icon('history', size='1.25rem').classes('text-purple-400 ml-1')
                                            self.history_search = ui.input(placeholder='Search history...').props('borderless dense clearable dark')\
                                                .classes('flex-1 text-white font-bold')\
                                                .on_value_change(lambda e: self.filter_history_table(e.value))
                                            
                                            if self.can_hide_history:
                                                ui.button(icon='first_page', on_click=self.toggle_history).props('flat dense color=white').classes('ml-auto bg-purple-600/30 hover:bg-purple-600 rounded-lg transition-colors').tooltip('Hide History Panel')
                                            
                                            ui.icon('search', size='1.1rem').classes('text-gray-500 mr-2')
                        
                                        self.purchase_history_aggrid = ui.aggrid({
                                            'columnDefs': [
                                                {'headerName': 'ID', 'field': 'id', 'width': 60, 'sortable': True, 'filter': True},
                                                {'headerName': 'Date', 'field': 'purchase_date', 'width': 100, 'sortable': True, 'filter': True},
                                                {'headerName': 'Ref', 'field': 'invoice_number', 'width': 110, 'sortable': True, 'filter': True},
                                                {'headerName': 'Supplier', 'field': 'supplier_name', 'width': 130, 'sortable': True, 'filter': True},
                                                {'headerName': 'Status', 'field': 'payment_status', 'width': 90, 'sortable': True, 'filter': True},
                                                {'headerName': 'Total', 'field': 'total_amount', 'width': 90, 'sortable': True, 'filter': True, 'type': 'numericColumn'}
                                            ],
                                            'rowData': [],
                                            # store api for layout when tab becomes visible
                                            'onGridReady': "function(params){ window.__aggrid_store['purchase_history'] = params.api; }",
                                            'rowSelection': 'single',
                                            'pagination': False,

                                            'domLayout': 'normal',
                                        }).classes('w-full flex-1 ag-theme-quartz-dark shadow-inner').style('background: transparent; border: none; height: 490px;')
                        
                                        self.purchase_history_aggrid.on('cellClicked', self.handle_history_aggrid_click_wrapper)
                 
                                with ui.row().classes('flex-1 h-full gap-4 overflow-hidden relative'):
                                    if self.can_hide_history:
                                        self.show_history_btn = ui.button(icon='last_page', on_click=self.toggle_history)\
                                            .props('flat dense color=white').classes('absolute -left-2 top-1/2 z-50 bg-purple-600 rounded-r-xl shadow-lg border border-white/20 h-12 w-6')\
                                            .tooltip('View History')
                                        self.show_history_btn.visible = False
                                    with ui.column().classes('flex-1 h-full gap-4 overflow-hidden'):
                                        with ui.row().classes('w-full glass p-4 rounded-2xl border border-white/10 gap-4 items-center'):
                                            # Date
                                            with ui.column().classes('w-32 gap-1'):
                                                ui.label('Date').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                with ui.row().classes('items-center gap-2'):
                                                    self.date_input = ui.input(value=datetime.now().strftime('%Y-%m-%d')).props('dark rounded outlined type=date').classes('w-full glass-input')

                                            # Currency
                                            with ui.column().classes('w-40 gap-1'):
                                                ui.label('Currency').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                self.currency_select = ui.select(
                                                    {row[0]: f"{row[2]} {row[1]}" for row in self.currency_rows},
                                                    value=self.default_currency_id
                                                ).props('borderless dense').classes('bg-white/5 px-4 py-1 rounded-xl border border-white/10 text-white text-xs font-bold w-full h-[36px]').on('change', self.on_currency_change)

                                            # Supplier
                                            with ui.column().classes('w-48 gap-1'):
                                                ui.label('Supplier').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                with ui.row().classes('items-center gap-3 bg-white/5 px-3 py-1.5 rounded-xl border border-white/10 w-full hover:bg-white/10 transition-all cursor-pointer shadow-inner h-[36px]'):
                                                    self.supplier_input = ui.input(placeholder='Select...').props('borderless dense dark').classes('flex-1 text-white font-black text-xs').on('click', self.open_supplier_dialog)
                                            with ui.column().classes('w-48 gap-1'):
                                                ui.label('Contact').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                with ui.row().classes('items-center gap-3 bg-white/5 px-3 py-1 rounded-xl border border-white/10 w-full'):
                                                    ui.icon('phone', size='1.25rem').classes('text-gray-400 opacity-40')
                                                    self.phone_input = ui.input(placeholder='Phone').props('borderless dense dark').classes('flex-1 text-white font-bold text-sm')

                                            with ui.column().classes('w-32 gap-1'):
                                                ui.label('Ref #').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                with ui.row().classes('items-center gap-3 bg-white/5 px-3 py-1 rounded-xl border border-white/10 w-full'):
                                                    self.reference_input = ui.input(placeholder='Ref #').props('borderless dense dark').classes('flex-1 text-white font-bold text-sm')

                                            with ui.column().classes('gap-1'):
                                                ui.label('Payment').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                with ui.row().classes('items-center gap-2 bg-white/5 px-3 py-1 rounded-xl border border-white/10 h-[36px]'):
                                                    self.payment_method = ui.radio(options=['Cash', 'On Account'], value='Cash').props('inline dark color=purple').classes('text-white text-[10px] font-black uppercase tracking-tighter')

                                        # --- Inline Product Entry ---
                                        with ui.row().classes('items-end gap-3 px-3 py-2 bg-white/5 rounded-2xl border border-white/10 ml-auto'):
                                            with ui.column().classes('flex-[2] gap-1'):
                                                ui.label('Barcode').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                with ui.row().classes('items-center gap-3 bg-white/5 px-3 py-1 rounded-xl border border-white/10 w-full'):
                                                    ui.icon('qr_code_scanner', size='1.25rem').classes('text-purple-400')
                                                    self.barcode_input = ui.input(placeholder='Barcode...').props('borderless dense dark').classes('flex-1 text-white font-bold').on(
                                                        'change', self.update_product_dropdown
                                                    ).on(
                                                        'keydown.enter',
                                                        lambda: (
                                                            self.product_input.run_method('focus'),
                                                            ui.timer(0.01, lambda: self.product_input.run_method('select'), once=True)
                                                        )
                                                    )

                                            with ui.column().classes('flex-[3] gap-1'):
                                                ui.label('Product').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                with ui.row().classes('items-center gap-3 bg-white/5 px-3 py-1 rounded-xl border border-white/10 w-full'):
                                                    ui.icon('inventory_2', size='1.25rem').classes('text-purple-400')
                                                    self.product_input = ui.input(placeholder='Product...').props('borderless dense dark').classes('flex-1 text-white font-bold').on(
                                                        'click', self.open_product_dialog
                                                    ).on(
                                                        'keydown.enter', self.open_product_dialog
                                                    )

                                            with ui.column().classes('w-20 gap-1'):
                                                ui.label('Qty').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest ml-4 text-center')
                                                with ui.row().classes('items-center gap-1 bg-white/5 px-2 py-2 rounded-2xl border border-white/10 w-full'):
                                                    self.quantity_input = ui.number(value=1).props('borderless dense dark').classes('w-full text-white font-black text-center').on(
                                                        'keydown.enter',
                                                        lambda: (
                                                            self.discount_input.run_method('focus'),
                                                            ui.timer(0.01, lambda: self.discount_input.run_method('select'), once=True)
                                                        )
                                                    )

                                            with ui.column().classes('w-24 gap-1'):
                                                ui.label('Disc %').classes('text-[8px] font-black text-orange-400 uppercase tracking-widest ml-4 text-center')
                                                with ui.row().classes('items-center gap-1 bg-white/5 px-2 py-2 rounded-2xl border border-white/10 w-full'):
                                                    self.discount_input = ui.number(value=0, min=0, max=100).props('borderless dense dark').classes('w-full text-white font-black text-center').on(
                                                        'keydown.enter',
                                                        lambda: (
                                                            self.cost_input.run_method('focus'),
                                                            ui.timer(0.01, lambda: self.cost_input.run_method('select'), once=True)
                                                        )
                                                    )

                                            with ui.column().classes('w-28 gap-1'):
                                                ui.label('Cost').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest ml-4 text-center')
                                                with ui.row().classes('items-center gap-1 bg-white/5 px-2 py-2 rounded-2xl border border-white/10 w-full'):
                                                    self.cost_input = ui.number(value=0.0).props('borderless dense dark').classes('w-full text-white font-black text-center').on(
                                                        'keydown.enter',
                                                        lambda: (
                                                            self.price_input.run_method('focus'),
                                                            ui.timer(0.01, lambda: self.price_input.run_method('select'), once=True)
                                                        )
                                                    )

                                            # Create the + button before wiring Enter on Retail to it
                                            
                                            with ui.column().classes('w-28 gap-1'):
                                                ui.label('Retail').classes('text-[8px] font-black text-accent uppercase tracking-widest ml-4 text-center')
                                                with ui.row().classes('items-center gap-1 bg-white/5 px-2 py-2 rounded-2xl border border-white/10 w-full'):
                                                    self.price_input = ui.number(value=0.0).props('borderless dense dark').classes('w-full text-white font-black text-center').on(
                                                        'keydown.enter',
                                                        lambda: (
                                                            self.add_product_button.run_method('click')
                                                        )
                                                    )
                                            self.add_product_button = ui.button(icon='add', on_click=self.add_product).props('elevated round size=lg color=purple').classes('shadow-lg shadow-purple-500/30 hover:scale-110 transition-transform mb-1')
                            
                                        with ui.element('div').classes('w-full min-h-[400px] overflow-auto'):
                                            self.aggrid = ui.aggrid({
                                                'columnDefs': self.columns,
                                                'rowData': self.rows,
                                                'rowSelection': 'single',
                                                'domLayout': 'normal',
                                                'rowHeight': 30,
                                            }).classes('w-full h-full ag-theme-quartz-dark')

                                        def store_grid_api():
                                            try:
                                                ui.run_javascript("if(window.__aggrid_store) window.__aggrid_store['purchase'] = document.querySelector('.ag-theme-quartz-dark').__ag_api;")
                                            except Exception:
                                                pass
                                        ui.timer(0.5, store_grid_api, once=True)

                                        self.aggrid.on('cellClicked', self.on_row_click_edit_cells)

                                        # -------------------------------------------------------
                                        # Arrow navigation for the main purchase grid (robust)
                                        # Mirrors the salesui_aggrid_compact keyboard methodology:
                                        # document-level capture listener + always targeting latest
                                        # grid instance + ensureIndexVisible + setFocusedCell.
                                        # -------------------------------------------------------
                                        main_grid_id = self.aggrid.id
                                        ui.run_javascript('''
                                            (() => {
                                                // Always target the latest main grid API from the global store.
                                                // This avoids stale grid_id / DOM issues after refreshes (add/load).
                                                window.__purchase_main_grid_key_listener = (ev) => {
                                                    try {
                                                        if (ev.key !== 'ArrowDown' && ev.key !== 'ArrowUp') return;

                                                        const apiFromStore = (window.__aggrid_store && window.__aggrid_store['purchase']);
                                                        if (!apiFromStore) return;
                                                        const api = apiFromStore;

                                                        ev.preventDefault();

                                                        const nodes = api.getSelectedNodes ? api.getSelectedNodes() : [];
                                                        let idx = 0;

                                                        if (nodes && nodes.length > 0 && typeof nodes[0].rowIndex === 'number') {
                                                            idx = nodes[0].rowIndex;
                                                        } else {
                                                            const focused = api.getFocusedCell && api.getFocusedCell();
                                                            if (focused && typeof focused.rowIndex === 'number') idx = focused.rowIndex;
                                                            else idx = 0;
                                                        }

                                                        const dir = ev.key === 'ArrowDown' ? 1 : -1;
                                                        idx = idx + dir;

                                                        const rowCount = api.getDisplayedRowCount ? api.getDisplayedRowCount() : 0;
                                                        const max = rowCount - 1;
                                                        if (idx > max) idx = max;
                                                        if (idx < 0) idx = 0;

                                                        if (api.ensureIndexVisible) api.ensureIndexVisible(idx);

                                                        const row = api.getDisplayedRowAtIndex && api.getDisplayedRowAtIndex(idx);
                                                        if (row && row.setSelected) row.setSelected(true, false);

                                                        if (api.setFocusedCell) api.setFocusedCell(idx, 'product');
                                                    } catch(e) {
                                                        console.error('[purchase-grid] listener error', e);
                                                    }
                                                };

                                                if (window.__purchase_main_grid_key_listener_attached) {
                                                    window.removeEventListener('keydown', window.__purchase_main_grid_key_listener, true);
                                                }
                                                window.addEventListener('keydown', window.__purchase_main_grid_key_listener, true);
                                                window.__purchase_main_grid_key_listener_attached = true;
                                            })();
                                        ''')
                                        
                                    # Action Bar Panel (Right Side of Editor)
                                    with ui.column().classes('w-60px items-center shrink-0'):
                                        from modern_ui_components import ModernActionBar
                                        self.action_bar = ModernActionBar(
                                            on_new=self.clear_inputs,
                                            on_save=self.save_purchase,
                                            on_undo=self.show_undo_confirmation,
                                            on_delete=self.delete_purchase,
                                            on_print=self.print_purchase_invoice,
                                             on_print_special=lambda: __import__('purchase_reports').open_print_special_dialog(
                                                 supplier_id=self.current_supplier_id,
                                                 supplier_name=self.supplier_input.value),
                                            on_chatgpt=lambda: ui.run_javascript('window.open("https://chatgpt.com", "_blank");'),
                                            on_view_transaction=self.view_purchase_transaction,
                                            on_refresh=self.refresh_purchase_table,
                                            button_class='h-10',
                                            classes=' '
                                        ).style('position: static; width: 60px; border-radius: 12px; margin-top: 0;')



                             
                            # --- FOOTER: Consolidated High-Visibility Row ---
                            with ui.row().classes('w-full bg-black/80 backdrop-blur-xl border-t border-white/20 p-4 items-center justify-between shadow-2xl flex-nowrap gap-4'):
                                # 1. Operational Metrics
                                with ui.row().classes('items-center gap-3 shrink-0'):
                                    with ui.row().classes('items-center gap-2 bg-purple-500/10 px-3 py-1.5 rounded-xl border border-purple-500/20 shadow-sm'):
                                        ui.icon('analytics', size='1rem').classes('text-purple-400')
                                        with ui.column().classes('gap-0'):
                                            ui.label('Procurement Pipeline').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest')
                                            if self.can_view_profit_analytics:
                                                ui.button('STATISTICS', on_click=self.show_statistics_dialog, icon='bar_chart').props('flat dense size=sm').classes('text-purple-400 text-[9px] h-3 p-0 min-h-0')
                                                ui.button('PROFIT', on_click=self.show_profit_dialog, icon='insights').props('flat dense size=sm').classes('text-purple-400 text-[9px] h-3 p-0 min-h-0')
                                        
                                    with ui.row().classes('items-center gap-3 bg-white/5 py-1 px-3 rounded-xl border border-white/10'):
                                        with ui.column().classes('items-center gap-0'):
                                            ui.label('Items').classes('text-[8px] text-gray-500 font-bold uppercase tracking-tighter')
                                            self.summary_label = ui.label('0 items').classes('text-xs font-black text-white')
                                        ui.element('div').classes('w-[1px] h-6 bg-white/10')
                                        with ui.column().classes('items-center gap-0'):
                                            ui.label('Quantity').classes('text-[8px] text-gray-500 font-bold uppercase tracking-tighter')
                                            self.quantity_total_label = ui.label('Total Qty: 0').classes('text-xs font-black text-white')

                                # 2. Session Info (Operator & Terminal)
                                with ui.row().classes('items-center gap-4 px-4 py-1.5 bg-white/5 border border-white/10 rounded-2xl shadow-inner mx-2 shrink-0'):
                                    with ui.column().classes('items-center gap-0'):
                                        ui.label('Operator').classes('text-[8px] text-gray-500 font-bold uppercase tracking-widest')
                                        ui.label(user.get('username', 'Guest')).classes('text-xs font-black text-[#80B9AD] uppercase tracking-wider')
                                    
                                    ui.element('div').classes('w-[1px] h-6 bg-white/10')
                                    
                                    with ui.column().classes('items-center gap-0'):
                                        ui.label('Organization').classes('text-[8px] text-gray-500 font-bold uppercase tracking-widest')
                                        ui.label(company_name).classes('text-xs font-black text-white uppercase tracking-wider')
                                    
                                    ui.element('div').classes('w-[1px] h-6 bg-white/10')
                                    
                                    with ui.column().classes('items-center gap-0'):
                                        ui.label('Terminal Time').classes('text-[8px] text-gray-500 font-bold uppercase tracking-widest')
                                        def update_footer_time():
                                            now_time = datetime.now().strftime('%H:%M:%S')
                                            footer_time_label.text = now_time
                                        footer_time_label = ui.label()
                                        update_footer_time()
                                        ui.timer(1.0, update_footer_time)
                                        footer_time_label.classes('text-xs font-black text-[#80B9AD] tracking-widest')

                                # 3. Financial Summary
                                with ui.row().classes('items-center gap-3 bg-purple-500/5 px-4 py-1.5 rounded-2xl border border-purple-500/20 shadow-inner ml-auto shrink-0'):
                                    with ui.column().classes('items-center gap-0'):
                                        ui.label('Total HT').classes('text-[9px] text-gray-400 font-bold uppercase tracking-widest')
                                        self.subtotal_label = ui.label('$0.00').classes('text-sm font-black text-white')
                                        ui.label('Total VAT').classes('text-[9px] text-gray-400 font-bold uppercase tracking-widest mt-1')
                                        self.vat_label = ui.label('$0.00').classes('text-sm font-black text-purple-400')
                                    
                                    ui.element('div').classes('w-[1px] h-14 bg-white/10')
                                    
                                    with ui.column().classes('items-center gap-0 w-28'):
                                        ui.label('Total L.L.').classes('text-[9px] text-yellow-400/80 font-bold uppercase tracking-widest')
                                        self.ll_total_input = ui.number(value=0, on_change=self.ll_total_input_changed).props('dense dark borderless').classes('w-full text-lg font-bold text-yellow-400/90 text-center bg-white/5 rounded')
                                    
                                    ui.element('div').classes('w-[1px] h-14 bg-white/10')
                                    
                                    with ui.column().classes('items-center gap-0 w-36'):
                                        with ui.row().classes('items-center justify-between w-full'):
                                            ui.label('Discount').classes('text-[8px] text-purple-300 font-black uppercase tracking-widest')
                                            self.discount_type_toggle = ui.radio(['Amount', '%'], value='Amount', on_change=self._on_discount_mode_change).props('inline dense dark color=purple').classes('text-[9px] font-black')
                                        with ui.row().classes('items-center w-full gap-1'):
                                            self.discount_amount_input = ui.number(value=0, on_change=self.update_totals).props('dense dark borderless').classes('w-full text-right text-xs text-white bg-white/5 rounded px-1')
                                            self.discount_percent_input = ui.number(value=0, on_change=self.update_totals).props('dense dark borderless').classes('w-full text-right text-xs text-white bg-white/5 rounded px-1 hidden')
                                        with ui.row().classes('items-center justify-center gap-1 mt-1'):
                                            ui.label('Total TTC').classes('text-[10px] text-purple-300 font-black uppercase tracking-[.25em]')
                                            self.ttc_currency_label = ui.label('$').classes('text-[10px] text-purple-300 font-black')
                                        self.total_input = ui.number(value=0, on_change=self.total_input_changed).props('dense dark borderless').classes('w-full text-2xl font-black text-white text-center bg-white/5 rounded')


                    ui.timer(0.1, self.load_max_purchase, once=True)
                    ui.timer(0.2, self.refresh_purchase_table, once=True)
                    # trigger ag-Grid layout after tables are rendered
                    ui.timer(0.3, lambda: ui.run_javascript("window.__aggrid_triggerVisible && window.__aggrid_triggerVisible();"), once=True)

    async def handle_history_aggrid_click_wrapper(self, e):
        async with loading_indicator.show_loading('load_purchase_items', 'Loading purchase items...', overlay=True):
            try:
                selected_row = e.args.get('data')
                if selected_row and isinstance(selected_row, dict) and 'id' in selected_row:
                    await self.load_purchase_details(selected_row['id'])
            except Exception as ex:
                ui.notify(f'Error: {ex}')


@ui.page('/purchase')
def purchase_page_route():
    PurchaseUI()
