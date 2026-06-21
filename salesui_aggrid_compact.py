from nicegui import ui
from pathlib import Path
from datetime import date as dt
from connection import connection
from datetime import datetime
from decimal import Decimal
from invoice_pdf_cairo import generate_sales_invoice_pdf
import accounting_helpers
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
from loading_indicator import loading_indicator
from connection_cashdrawer import connection_cashdrawer
from modern_design_system import ModernDesignSystem as MDS
import asyncio
class SalesUI:
    
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
        self.is_employee = user.get('role_name') == 'Employee'
        # Fallback: Admin role (usually ID 1 or name 'Admin') gets hide-history by default
        is_admin = user.get('role_name') == 'Admin' or user.get('role_id') == 1
        self.can_hide_history = self.permissions.get('hide-history', False) or is_admin

        # Profit analytics permission gating
        self.can_view_profit_analytics = self.permissions.get('profit-analytics', False) or is_admin

        allowed_pages = {page for page, can_access in self.permissions.items() if can_access}

        if show_navigation:
            # Create enhanced navigation instance
            navigation = EnhancedNavigation(self.permissions, user)
            navigation.create_navigation_drawer()  # Create drawer first
            navigation.create_navigation_header()  # Then create header with toggle button

        self.max_sale_id = self.get_max_sale_id()

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
            {'headerName': 'Price (TTC)', 'field': 'price', 'width': 90,  'headerClass': 'blue-header'}, 
            {'headerName': 'Discount %', 'field': 'discount', 'width': 80,  'headerClass': 'blue-header'},
            {'headerName': 'VAT %', 'field': 'vat_percentage', 'width': 80,  'headerClass': 'blue-header'},
            {'headerName': 'VAT Amt(Ref)', 'field': 'vat_amount', 'width': 80,  'headerClass': 'blue-header'},
            {'headerName': 'Subtotal (TTC)', 'field': 'subtotal', 'width': 100,  'headerClass': 'blue-header'}
        ]
        self.customer_rows = []
        self.customer_grid = None
        self.product_rows = []
        self.product_grid = None
        self.rows = []
        self.all_sales_data = [] # Store full sales history for filtering
        self.total_amount = 0
        self.total_quantity = 0
        self.total_items = 0
        self.grid_readonly = False  # Track grid state
        self.new_mode = False  # Track new mode state
        self.current_customer_id = None
        self.current_customer_name = 'Cash Client'

        # Initialize UI
        self.create_ui()
        self.load_default_customer()

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
                row['price'] = row['price'] / old_rate * new_rate
                row['subtotal'] = self.calculate_subtotal(row['quantity'], row['price'], row['discount'])

            self.aggrid.update()
            self.update_totals()
            self.previous_currency_id = self.currency_select.value

    def get_current_currency_symbol(self):
        selected_currency_id = self.currency_select.value
        for row in self.currency_rows:
            if row[0] == selected_currency_id:
                return row[2]
        return '$'

    def calculate_subtotal(self, quantity, price, discount, vat_percentage=11):
        # Total TTC = Qty * Price
        total_ttc = (quantity * price) * (1 - discount / 100)
        return round(total_ttc, 2)

    

  

    def generate_invoice_number(self):
        try:
            existing_invoices = connection.contogetrows(
                "SELECT invoice_number FROM sales WHERE invoice_number IS NOT NULL", []
            )
            existing_set = {row[0] for row in existing_invoices}
            max_num = 0
            for invoice in existing_set:
                if invoice.startswith('INV-'):
                    try:
                        num = int(invoice.split('-')[1])
                        max_num = max(max_num, num)
                    except (ValueError, IndexError):
                        continue
            next_num = max_num + 1
            while f"INV-{next_num:06d}" in existing_set:
                next_num += 1
            return f"INV-{next_num:06d}"
        except Exception as e:
            import time
            return f"INV-{int(time.time())}"

    def add_product(self, e=None):
        try:
            barcode = self.barcode_input.value
            product_name = self.product_input.value
            quantity = int(self.quantity_input.value) if self.quantity_input.value else 0
            discount = float(self.discount_input.value) if self.discount_input.value else 0
            price = float(self.price_input.value) if self.price_input.value else 0
            
            if not barcode or not product_name or quantity <= 0 or price <= 0:
                ui.notify('Please fill in all required fields with valid values')
                return
            
            # Check if product has sufficient stock (Standard only)
            product_id = connection.getid('select id from products where product_name = ?', [product_name])
            stock_result = []
            connection.contogetrows(f"SELECT stock_quantity FROM products WHERE id = {product_id}", stock_result)

            is_performa = getattr(self, 'sale_type', None) and self.sale_type.value == 'Performa'
            if not is_performa and stock_result and stock_result[0][0] < quantity:
                ui.notify(f'Insufficient stock! Available: {stock_result[0][0]}, Requested: {quantity}')
                return
            
            # Fetch VAT info
            product_vat_data = []
            connection.contogetrows(f"SELECT is_vat_subjected, vat_percentage FROM products WHERE id = {product_id}", product_vat_data)
            is_vat_subjected = product_vat_data[0][0] if product_vat_data else False
            vat_percentage = float(product_vat_data[0][1] or 0) if product_vat_data else 0.0
            
            # VAT is 11% if subjected, otherwise 0
            vat_percentage = 11.0 if is_vat_subjected else 0.0
            
            # price is TTC. We need to extract HT for VAT amount calculation if needed, 
            # but subtotal should be TTC.
            price_ttc = price
            price_ht = price_ttc / (1 + vat_percentage / 100)
            
            total_ttc = (quantity * price_ttc) * (1 - discount / 100)
            total_ht = total_ttc / (1 + vat_percentage / 100)
            vat_amount = total_ttc - total_ht
            subtotal = total_ttc 
            
            self.rows.append({
                'barcode': barcode,
                'product': product_name,
                'quantity': quantity,
                'discount': discount,
                'price': price_ttc,
                'vat_percentage': vat_percentage if is_vat_subjected else 0,
                'vat_amount': vat_amount,
                'subtotal': subtotal,
            })
            
            self.total_amount += subtotal
            self.update_totals()
            
            # Stock update moved to save/update/delete (persisted invoice) only.
            # Cart add should NOT mutate inventory stock.
            self.clear_inputs_inputs()
            # Ensure aggrid receives the new rowData reference for proper refresh
            try:
                self.aggrid.options['rowData'] = self.rows
            except Exception:
                pass
            self.aggrid.update()
            
            # Focus back to barcode
            self.barcode_input.run_method('focus')
            
        except ValueError as e:
            ui.notify(f'Invalid input: {str(e)}')
        except Exception as e:
            ui.notify(f'Error adding product: {str(e)}')

    def clear_inputs_inputs(self):
        self.barcode_input.value = ''
        self.product_input.value = ''
        self.quantity_input.value = 1
        self.discount_input.value = 0
        self.price_input.value = 0.0
    
    def clear_inputs(self, dim_history=True):
        if hasattr(self, 'action_bar'):
            self.action_bar.enter_new_mode()
        if dim_history:
            self.sales_aggrid.classes('dimmed')
        #ui.run_javascript(f'document.getElementById({self.sales_aggrid.id}).disabled = true;')
        self.load_default_customer()
        self.barcode_input.value = ''
        self.product_input.value = ''
        self.quantity_input.value = 1
        self.discount_input.value = 0
        self.price_input.value = 0.0
        self.discount_percent_input.value = 0
        self.discount_amount_input.value = 0
        if hasattr(self, 'discount_type_toggle'):
            self.discount_type_toggle.value = 'Amount'
            self.discount_percent_input.visible = False
            self.discount_amount_input.visible = True
        
        self.rows.clear()
        self.aggrid.options['rowData'] = self.rows
        self.aggrid.update()

        self.total_amount = 0
        if hasattr(self, 'total_input'):
            self.total_input.value = 0
        else:
            self.total_label.text = f"Total: {self.get_current_currency_symbol()}0.00"
        if hasattr(self, 'll_total_input'):
            self.ll_total_input.value = 0
        self.subtotal_label.text = f"Subtotal: {self.get_current_currency_symbol()}0.00"
        
        self.current_sale_id = None
        self.new_mode=True
        
        # Focus back to barcode
        self.barcode_input.run_method('focus')
        
        #if hasattr(self, 'searchtable'):
        #   self.searchtable.props(remove='readonly')
        

    def update_product_dropdown(self, e):
        try:
            barcode = self.barcode_input.value
            if barcode:
                product_data = []
                connection.contogetrows(
                    f"SELECT barcode, product_name, price_ttc FROM products WHERE barcode = '{barcode}'", 
                    product_data
                )
                
                if product_data:
                    product = product_data[0]
                    self.product_input.value = product[1]
                    self.price_input.value = float(product[2])

                    # Get selected currency info
                    selected_currency_id = self.currency_select.value
                    selected_currency_symbol = None
                    exchange_rate = float(self.currency_exchange_rates.get(selected_currency_id, 1.0))
                    for row in self.currency_rows:
                        if row[0] == selected_currency_id:
                            selected_currency_symbol = row[2]
                            break

                    # Convert to selected currency if needed
                    if selected_currency_symbol != '$':
                        self.price_input.value = self.price_input.value * exchange_rate

                    ui.notify(f"Product loaded: {product[1]}")
                    
                else:
                    ui.notify("Product not found for this barcode")
        except Exception as e:
            ui.notify(f'Error updating product: {str(e)}')

    async def on_row_click_edit_cells(self, e):
        try:
            selected_row = await self.aggrid.get_selected_row()
            
            if selected_row and isinstance(selected_row, dict) and 'barcode' in selected_row:
                ui.notify(f"Selected: {selected_row.get('product', 'Unknown')} - Qty: {selected_row.get('quantity', 0)}")
                self.open_edit_dialog(selected_row)
            else:
                ui.notify("Please select a valid row to edit")
                
        except Exception as ex:
            ui.notify(f"Error opening edit dialog: {str(ex)}")

    def open_product_dialog(self):
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-6xl glass p-6 border border-white/10').style('background: rgba(15, 15, 25, 0.82); backdrop-filter: blur(20px); border-radius: 2rem;'):
            ui.label('Inventory Catalog').classes('text-2xl font-black mb-6 text-white').style('font-family: "Outfit", sans-serif;')
            
            with ui.row().classes('w-full items-center gap-3 bg-white/5 px-4 py-2 rounded-xl border border-white/10 mb-4'):
                ui.icon('search', size='1.25rem').classes('text-purple-400')
                search_input = ui.input(placeholder='Search by name or barcode...').props('borderless dense autocomplete="off"').classes('flex-1 text-white text-sm')\
                    .on_value_change(lambda e: self.filter_product_rows(e.value))\
                    .on('keydown.down', lambda: self._product_search_arrow_down(dialog))\
                    .on('keydown.enter', lambda: self._product_search_enter(dialog))
                search_input.run_method('focus')

            data = []
            connection.contogetrows("SELECT barcode, product_name, stock_quantity, price_ttc, cost_price FROM products", data)
            
            self.product_rows = []
            for row in data:
                self.product_rows.append({
                    'barcode': row[0],
                    'product_name': row[1],
                    'stock_quantity': row[2],
                    'price': row[3],
                    'cost_price': row[4]
                })
            
            columns = [
                {'name': 'barcode', 'label': 'Barcode', 'field': 'barcode', 'align': 'left'},
                {'name': 'product_name', 'label': 'Product', 'field': 'product_name', 'align': 'left'},
                {'name': 'stock_quantity', 'label': 'Stock', 'field': 'stock_quantity', 'align': 'center'},
                {'name': 'price', 'label': 'Price', 'field': 'price', 'align': 'right'},
                {'name': 'cost_price', 'label': 'Cost', 'field': 'cost_price', 'align': 'right'}
            ]
            
            with ui.element('div').classes('w-full h-96 overflow-hidden flex flex-col'):
                with ui.element('div').classes('flex-1 overflow-auto min-h-0'):
                    self.product_grid = ui.table(
                        columns=columns, 
                        rows=self.product_rows, 
                        row_key='barcode',
                        selection='single'
                    ).classes('w-full h-full bg-transparent overflow-hidden').props('virtual-scroll flat bordered dense hide-pagination :pagination="{rowsPerPage: 0}"')

            # --- Category-style keyboard navigation + highlight ---
            state = {'selected_idx': 0}

            def clear_highlight_js():
                ui.run_javascript("""
                    try {
                      const root = document.querySelector('.q-table');
                      if (!root) return;
                      const rows = root.querySelectorAll('tbody tr');
                      rows.forEach(el => {
                        el.style.backgroundColor = '';
                        el.style.color = '';
                        el.classList.remove('selected-highlight');
                      });
                    } catch (e) {}
                """)

            def apply_highlight_js():
                # Uses (selected_idx + 1) offset like category.py
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
                if not self.product_grid.rows:
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
                    args = e.args if hasattr(e, 'args') else e
                    row_data = None
                    if isinstance(args, (list, tuple)):
                        # Quasar row-click: [mouse_event, row_dict, cols, index]
                        for candidate in args:
                            if isinstance(candidate, dict) and 'barcode' in candidate:
                                row_data = candidate
                                break
                        if row_data is None and len(args) > 1 and isinstance(args[1], dict):
                            row_data = args[1]
                    elif isinstance(args, dict):
                        row_data = args.get('row') or args.get('data') or (args if 'barcode' in args else None)

                    if not isinstance(row_data, dict):
                        return

                    if self.product_grid.rows:
                        for i, r in enumerate(self.product_grid.rows):
                            if r.get('barcode') == row_data.get('barcode'):
                                state['selected_idx'] = i
                                break
                        apply_highlight_js()

                    self.handle_product_grid_click({'args': {'data': row_data}}, dialog)
                except Exception as ex:
                    ui.notify(f'Row selection error: {ex}', color='negative')

            self.product_grid.on('row-click', on_click_row)

            # initial select
            ui.timer(0.05, select_and_scroll, once=True)

            # Focus + attach keydown listener to table root
            grid_id = getattr(self.product_grid, 'id', '')
            search_id = getattr(search_input, 'id', '')
            ui.run_javascript(f"""
                window.__product_dialog_active = true;
                try {{
                  const root = document.getElementById('{grid_id}') || document.querySelector('.q-table');
                  if (root) {{
                    root.tabIndex = 0;
                    try {{ root.style.outline = 'none'; }} catch(e) {{}}
                    try {{ root.style.caretColor = 'transparent'; }} catch(e) {{}}

                    // Start with "nothing selected" so the first ArrowDown lands on row 0
                    try {{ root.dataset.selIdx = '-1'; }} catch(e) {{}}

                    root.addEventListener('keydown', (ev) => {{
                      if (!window.__product_dialog_active) return;
                      if (ev.key !== 'ArrowDown' && ev.key !== 'ArrowUp' && ev.key !== 'Enter') return;

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

                      if (ev.key === 'ArrowDown') cur = Math.min((cur < 0 ? -1 : cur) + 1, rows.length - 1);
                      if (ev.key === 'ArrowUp') cur = Math.max((cur < 0 ? 0 : cur) - 1, 0);

                      // If Enter is pressed while nothing selected yet => click first row
                      if (ev.key === 'Enter') {{
                        if (cur < 0) cur = 0;
                      }}

                      root.dataset.selIdx = cur;

                      // highlight
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
                  }}
                }} catch (e) {{}}


            """)

            with ui.row().classes('w-full justify-end mt-6'):
                ui.button('Cancel', on_click=lambda: (ui.run_javascript('window.__product_dialog_active=false;'), dialog.close())).props('flat text-color=white').classes('px-6 rounded-xl hover:bg-white/5')

        dialog.open()

    def open_customer_dialog(self):
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-4xl glass p-6 border border-white/10').style('background: rgba(15, 15, 25, 0.8); backdrop-filter: blur(20px); border-radius: 2rem;'):
            ui.label('Select Customer').classes('text-2xl font-black mb-6 text-white').style('font-family: "Outfit", sans-serif;')
            
            with ui.row().classes('w-full items-center gap-3 bg-white/5 px-4 py-2 rounded-xl border border-white/10 mb-4'):
                ui.icon('search', size='1.25rem').classes('text-purple-400')
                search_input = ui.input(placeholder='Search by name or phone...').props('borderless dense autocomplete="off"').classes('flex-1 text-white text-sm').on_value_change(lambda e: self.filter_customer_rows(e.value)).on('keydown.down', lambda: self._customer_search_arrow_down(dialog)).on('keydown.enter', lambda: self._customer_search_enter(dialog))
                search_input.run_method('focus')
            
            headers = ['id', 'customer_name', 'phone', 'balance']
            data = []
            connection.contogetrows("SELECT id, customer_name, phone, balance FROM customers", data)
            
            self.customer_rows = []
            for row in data:
                self.customer_rows.append({
                    'id': row[0],
                    'customer_name': row[1],
                    'phone': row[2],
                    'balance': row[3]
                })
            
            columns = [
                {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left'},
                {'name': 'customer_name', 'label': 'Name', 'field': 'customer_name', 'align': 'left'},
                {'name': 'phone', 'label': 'Phone', 'field': 'phone', 'align': 'left'},
                {'name': 'balance', 'label': 'Balance', 'field': 'balance', 'align': 'right'}
            ]
            
            with ui.element('div').classes('w-full h-80 overflow-hidden flex flex-col'):
                with ui.element('div').classes('flex-1 overflow-auto min-h-0'):
                    self.customer_grid = ui.table(
                        columns=columns, 
                        rows=self.customer_rows, 
                        row_key='id',
                        selection='single'
                    ).classes('w-full h-full bg-transparent overflow-hidden').props('virtual-scroll flat bordered dense hide-pagination :pagination="{rowsPerPage: 0}"')
            
            # --- Category-style keyboard navigation + highlight (same methodology as product dialog) ---
            state = {'selected_idx': 0}

            def apply_highlight_js():
                idx = state['selected_idx']
                ui.run_javascript(f"""
                    try {{
                      const root = document.getElementById('{getattr(self.customer_grid, "id", "")}') || document.querySelector('.q-table');
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
                if not self.customer_grid.rows:
                    return
                state['selected_idx'] = max(0, min(state['selected_idx'], len(self.customer_grid.rows) - 1))
                row = self.customer_grid.rows[state['selected_idx']]
                self.customer_grid.selected = [row]
                self.customer_grid.update()
                self.customer_grid.run_method('scrollTo', state['selected_idx'])
                apply_highlight_js()

            def on_click_row(e):
                try:
                    args = e.args if hasattr(e, 'args') else e
                    row_data = None
                    if isinstance(args, (list, tuple)):
                        # Quasar row-click: [mouse_event, row_dict, cols, index]
                        for candidate in args:
                            if isinstance(candidate, dict) and 'customer_name' in candidate:
                                row_data = candidate
                                break
                        if row_data is None and len(args) > 1 and isinstance(args[1], dict):
                            row_data = args[1]
                    elif isinstance(args, dict):
                        row_data = args.get('row') or args.get('data') or (args if 'customer_name' in args else None)

                    if not isinstance(row_data, dict):
                        return

                    if self.customer_grid.rows:
                        for i, r in enumerate(self.customer_grid.rows):
                            if r.get('id') == row_data.get('id'):
                                state['selected_idx'] = i
                                break
                        apply_highlight_js()

                    self.handle_customer_grid_click({'args': {'data': row_data}}, dialog)
                except Exception as ex:
                    ui.notify(f'Row selection error: {ex}', color='negative')

            self.customer_grid.on('row-click', on_click_row)

            # initial select
            ui.timer(0.05, select_and_scroll, once=True)

            # Focus + attach keydown listener to table root
            grid_id = getattr(self.customer_grid, 'id', '')
            search_id = getattr(search_input, 'id', '')
            ui.run_javascript(f"""
                window.__customer_dialog_active = true;
                try {{
                  const root = document.getElementById('{grid_id}') || document.querySelector('.q-table');
                  if (root) {{
                    root.tabIndex = 0;
                    try {{ root.style.outline = 'none'; }} catch(e) {{}}
                    try {{ root.style.caretColor = 'transparent'; }} catch(e) {{}}

                    // Start with "nothing selected" so the first ArrowDown lands on row 0
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

                      const pageStep = 10; // fallback jump size for PageUp/PageDown

                      if (ev.key === 'ArrowDown') cur = Math.min((cur < 0 ? -1 : cur) + 1, rows.length - 1);
                      if (ev.key === 'ArrowUp') cur = Math.max((cur < 0 ? 0 : cur) - 1, 0);
                      if (ev.key === 'PageDown') cur = Math.min((cur < 0 ? 0 : cur) + pageStep, rows.length - 1);
                      if (ev.key === 'PageUp') cur = Math.max((cur < 0 ? 0 : cur) - pageStep, 0);

                      // If Enter is pressed while nothing selected yet => click first row
                      if (ev.key === 'Enter') {{
                        if (cur < 0) cur = 0;
                      }}

                      root.dataset.selIdx = cur;

                      // highlight
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
                  }}
                }} catch (e) {{}}


            """)

            with ui.row().classes('w-full justify-end mt-6'):
                ui.button(
                    'Cancel',
                    on_click=lambda: (ui.run_javascript('window.__customer_dialog_active=false;'), dialog.close())
                ).props('flat text-color=white').classes('px-6 rounded-xl hover:bg-white/5')
        dialog.open()

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

                ui.label('STATISTICAL PRESENTATION').classes('text-[10px] font-black text-gray-400 uppercase tracking-widest mb-6 block font-medium')

                # Date & Time row
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

                # Employee & Customer row
                with ui.row().classes('w-full gap-4 mb-4'):
                    with ui.column().classes('gap-1 flex-1'):
                        ui.label('Employee').classes('text-[8px] text-gray-500 font-bold uppercase tracking-tighter')
                        emp_data = []
                        connection.contogetrows("SELECT id, first_name, last_name FROM employees ORDER BY first_name", emp_data)
                        emp_dict = {e[0]: f"{e[1]} {e[2]}" for e in emp_data}
                        employee_select = ui.select({**{0: 'All Employees'}, **emp_dict}, value=0).props('outlined dense dark').classes('w-full')
                    with ui.column().classes('gap-1 flex-1'):
                        ui.label('Customer').classes('text-[8px] text-gray-500 font-bold uppercase tracking-tighter')
                        cust_data = []
                        connection.contogetrows("SELECT id, customer_name FROM customers ORDER BY customer_name", cust_data)
                        cust_dict = {c[0]: c[1] for c in cust_data}
                        customer_select = ui.select({**{0: 'All Customers'}, **cust_dict}, value=0).props('outlined dense dark').classes('w-full')

                # Calculate button
                calc_row = ui.row().classes('w-full justify-center mb-6')
                with calc_row:
                    calculate_btn = ui.button('Calculate', icon='calculate').props('flat').classes('px-8 rounded-xl bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 font-black text-xs uppercase tracking-widest')

                # Results container
                with ui.column().classes('w-full gap-3'):
                    with ui.row().classes('w-full justify-between items-center bg-white/5 p-4 rounded-2xl border border-white/10 shadow-inner'):
                        with ui.column().classes('gap-0'):
                            ui.label('Total Sales').classes('text-[8px] text-gray-400 font-bold uppercase tracking-tighter')
                            total_sales_label = ui.label('--').classes('text-sm font-black text-white')
                        with ui.column().classes('gap-0 items-end'):
                            ui.label('Total Profit').classes('text-[8px] text-gray-400 font-bold uppercase tracking-tighter')
                            total_profit_label = ui.label('--').classes('text-sm font-black text-green-400')

                    with ui.row().classes('w-full justify-between items-center px-4'):
                        with ui.column().classes('gap-0'):
                            ui.label('Total Sales Discount').classes('text-[8px] text-gray-400 font-bold uppercase tracking-tighter')
                            total_discount_label = ui.label('--').classes('text-sm font-black text-red-400')
                        with ui.column().classes('gap-0 items-end'):
                            ui.label('Cash Box Amount').classes('text-[8px] text-gray-400 font-bold uppercase tracking-tighter')
                            cash_box_label = ui.label('--').classes('text-sm font-black text-blue-400')

                    with ui.row().classes('w-full justify-between items-center px-4'):
                        with ui.column().classes('gap-0'):
                            ui.label('On Account Amount').classes('text-[8px] text-gray-400 font-bold uppercase tracking-tighter')
                            on_account_label = ui.label('--').classes('text-sm font-black text-yellow-400')
                        with ui.column().classes('gap-0 items-end'):
                            ui.label('Customer Settlement').classes('text-[8px] text-gray-400 font-bold uppercase tracking-tighter')
                            settlement_label = ui.label('--').classes('text-sm font-black text-cyan-400')

                    with ui.row().classes('w-full justify-center items-center bg-green-500/10 p-4 rounded-2xl border border-green-500/30 mt-2'):
                        with ui.column().classes('items-center gap-0'):
                            ui.label('TOTAL RECEIVED').classes('text-[8px] text-gray-400 font-bold uppercase tracking-tighter')
                            total_received_label = ui.label('--').classes('text-lg font-black text-white')

                    def do_calculate():
                        try:
                            fd = from_date.value
                            td = to_date.value
                            ft = from_time.value
                            tt = to_time.value
                            emp_val = employee_select.value
                            cust_val = customer_select.value

                            from_dt_str = f"{fd} {ft}:00"
                            to_dt_str = f"{td} {tt}:00"

                            where_clauses = ["s.status = 'Sale'", "s.sale_date >= ?", "s.sale_date <= ?"]
                            params = [from_dt_str, to_dt_str]

                            if cust_val and cust_val != 0:
                                where_clauses.append("s.customer_id = ?")
                                params.append(cust_val)

                            if emp_val and emp_val != 0:
                                emp_name = next((v for k, v in emp_dict.items() if k == emp_val), '')
                                user_res = []
                                connection.contogetrows("SELECT id FROM users WHERE username LIKE ?", user_res, (f'%{emp_name}%',))
                                if not user_res:
                                    emp_parts = emp_name.split()
                                    if len(emp_parts) >= 2:
                                        alt_search = f"{emp_parts[0]}.{emp_parts[-1]}"
                                        connection.contogetrows("SELECT id FROM users WHERE username LIKE ?", user_res, (f'%{alt_search}%',))
                                if user_res:
                                    where_clauses.append("s.user_id = ?")
                                    params.append(user_res[0][0])

                            where_sql = " AND ".join(where_clauses)

                            # Total sales & discount
                            sales_data = []
                            connection.contogetrows(
                                f"SELECT COALESCE(SUM(s.total_amount), 0), COALESCE(SUM(s.discount_amount), 0) FROM sales s WHERE {where_sql}",
                                sales_data, tuple(params)
                            )
                            total_sales = float(sales_data[0][0]) if sales_data and sales_data[0][0] else 0.0
                            total_discount = float(sales_data[0][1]) if sales_data and sales_data[0][1] else 0.0

                            # Profit: total revenue minus total cost
                            cost_data = []
                            connection.contogetrows(
                                f"SELECT COALESCE(SUM(si.quantity * p.cost_price), 0) FROM sale_items si JOIN products p ON p.id = si.product_id JOIN sales s ON s.id = si.sales_id WHERE {where_sql}",
                                cost_data, tuple(params)
                            )
                            total_cost = float(cost_data[0][0]) if cost_data and cost_data[0][0] else 0.0
                            total_profit = total_sales - total_cost

                            # Cash box = cash sales (uses same filters as total sales)
                            cash_data = []
                            connection.contogetrows(
                                f"SELECT COALESCE(SUM(s.total_amount), 0) FROM sales s WHERE {where_sql} AND s.payment_status = 'completed' AND s.payment_method = 'Cash'",
                                cash_data, tuple(params)
                            )
                            cash_box = float(cash_data[0][0]) if cash_data and cash_data[0][0] else 0.0

                            # On Account (pending payment sales - respects all filters)
                            on_acct_data = []
                            connection.contogetrows(
                                f"SELECT COALESCE(SUM(s.total_amount), 0) FROM sales s WHERE {where_sql} AND s.payment_status = 'pending'",
                                on_acct_data, tuple(params)
                            )
                            on_account = float(on_acct_data[0][0]) if on_acct_data and on_acct_data[0][0] else 0.0

                            # Customer settlements (receipts) - respects customer/date filters
                            settl_where = ["cr.payment_date >= ?", "cr.payment_date <= ?"]
                            settl_params = [from_dt_str, to_dt_str]
                            if cust_val and cust_val != 0:
                                settl_where.append("cr.customer_id = ?")
                                settl_params.append(cust_val)
                            settl_data = []
                            connection.contogetrows(
                                f"SELECT COALESCE(SUM(cr.amount), 0) FROM customer_receipt cr WHERE {' AND '.join(settl_where)}",
                                settl_data, tuple(settl_params)
                            )
                            settlement = float(settl_data[0][0]) if settl_data and settl_data[0][0] else 0.0

                            # Total received = cash box + customer settlements
                            total_received = cash_box + settlement

                            total_sales_label.set_text(f"{selected_currency_symbol}{total_sales:,.2f}")
                            total_profit_label.set_text(f"{selected_currency_symbol}{total_profit:,.2f}")
                            total_discount_label.set_text(f"{selected_currency_symbol}{total_discount:,.2f}")
                            cash_box_label.set_text(f"{selected_currency_symbol}{cash_box:,.2f}")
                            on_account_label.set_text(f"{selected_currency_symbol}{on_account:,.2f}")
                            settlement_label.set_text(f"{selected_currency_symbol}{settlement:,.2f}")
                            total_received_label.set_text(f"{selected_currency_symbol}{total_received:,.2f}")
                        except Exception as calc_err:
                            ui.notify(f'Calculation error: {str(calc_err)}')
                            print(f'Statistics calc error: {str(calc_err)}')

                    calculate_btn.on_click(do_calculate)

                with ui.row().classes('w-full justify-end mt-8'):
                    ui.button('Dismiss', on_click=dialog.close).props('flat text-color=grey-5').classes('px-6 rounded-xl hover:bg-white/5 font-black text-xs uppercase tracking-widest')

            dialog.open()
        except Exception as e:
            ui.notify(f'Error opening statistics dialog: {str(e)}')
            print(f'Statistics dialog error: {str(e)}')

    def show_profit_dialog(self):
        """Calculate and display profit in a dialog dynamically based on current cart items."""
        try:
            if not self.can_view_profit_analytics:
                return ui.notify('Access denied: profit analytics', color='negative')
            if not self.rows:
                ui.notify('No items in cart to calculate profit')
                return

            selected_currency_id = self.currency_select.value
            exchange_rate = float(self.currency_exchange_rates.get(selected_currency_id, 1.0))
            
            selected_currency_symbol = '$'
            for c_row in self.currency_rows:
                if c_row[0] == selected_currency_id:
                    selected_currency_symbol = c_row[2]
                    break

            total_cost_local = 0.0
            total_revenue_local = 0.0

            for row in self.rows:
                barcode = row.get('barcode')
                if not barcode:
                    continue
                cost_data = []
                connection.contogetrows(f"SELECT cost_price FROM products WHERE barcode = '{barcode}'", cost_data)
                
                cost_price_usd = float(cost_data[0][0]) if cost_data and cost_data[0][0] else 0.0
                cost_price_local = cost_price_usd * exchange_rate
                
                total_cost_local += cost_price_local * row['quantity']
                total_revenue_local += row['subtotal']
                
            # Apply global discounts
            discount_percent = float(self.discount_percent_input.value or 0)
            discount_amount = float(self.discount_amount_input.value or 0)
            
            total_after_percent = total_revenue_local * (1 - discount_percent / 100)
            final_revenue = total_after_percent - discount_amount

            profit_value = final_revenue - total_cost_local
            profit_percentage = (profit_value / final_revenue) * 100 if final_revenue > 0 else 0

            with ui.dialog() as dialog, ui.card().classes('glass p-8 border border-white/10').style('background: rgba(15, 15, 25, 0.82); backdrop-filter: blur(20px); border-radius: 2rem; width: 380px;'):
                with ui.row().classes('w-full items-center justify-between mb-4'):
                    ui.label('Analytics').classes('text-2xl font-black text-white').style('font-family: "Outfit", sans-serif;')
                    ui.icon('savings', size='1.5rem').classes('text-green-400 opacity-80')
                
                ui.label(f'PROFIT ANALYSIS - CURRENT CART').classes('text-[10px] font-black text-gray-400 uppercase tracking-widest mb-6 block font-medium')

                with ui.column().classes('w-full gap-5'):
                    with ui.row().classes('w-full justify-between items-center bg-white/5 p-4 rounded-2xl border border-white/10 shadow-inner'):
                        with ui.column().classes('gap-0'):
                            ui.label('Net Profit').classes('text-[8px] text-gray-400 font-bold uppercase tracking-tighter')
                            ui.label(f'{selected_currency_symbol}{profit_value:,.2f}').classes('text-2xl font-black text-green-400')
                        
                        with ui.column().classes('gap-0 items-end'):
                            ui.label('Margin').classes('text-[8px] text-gray-400 font-bold uppercase tracking-tighter')
                            ui.label(f'{profit_percentage:.2f}%').classes('text-xl font-black text-blue-400')

                    with ui.row().classes('w-full justify-between items-center px-4'):
                        ui.label(f'Total Value ({selected_currency_symbol})').classes('text-[10px] text-gray-500 font-bold uppercase tracking-widest')
                        ui.label(f'{selected_currency_symbol}{final_revenue:,.2f}').classes('text-xs font-black text-white px-2 py-1 bg-white/10 rounded-lg')

                with ui.row().classes('w-full justify-end mt-8'):
                    ui.button('Dismiss', on_click=dialog.close).props('flat text-color=grey-5').classes('px-6 rounded-xl hover:bg-white/5 font-black text-xs uppercase tracking-widest')
            dialog.open()
            
        except Exception as e:
            ui.notify(f'Error calculating profit: {str(e)}')
            print(f'Profit calculation error: {str(e)}')
    def print_sale_invoice(self):
        """Show on-screen invoice receipt dialog with Print to PDF option"""
        try:
            if not self.rows:
                ui.notify('No items to print!')
                return

            invoice_number = self.invoicenumber or self.generate_invoice_number()
            if not self.invoicenumber:
                self.invoicenumber = invoice_number

            subtotal = sum(row['subtotal'] for row in self.rows)
            discount_percent = float(self.discount_percent_input.value or 0)
            discount_amount = float(self.discount_amount_input.value or 0)
            total_after_percent = subtotal * (1 - discount_percent / 100)
            final_total = total_after_percent - discount_amount

            company_info = connection.get_company_info()
            company_name = company_info.get('company_name') if company_info else 'Company Name'

            selected_currency_id = self.currency_select.value
            currency_symbol = '$'
            for row in self.currency_rows:
                if row[0] == selected_currency_id:
                    currency_symbol = row[2]
                    break

            invoice_data = []
            for item in self.rows:
                invoice_data.append({
                    'Barcode': str(item['barcode']),
                    'Product': str(item['product']),
                    'Quantity': str(item['quantity']),
                    'Price': f"{currency_symbol}{item['price']:,.2f}",
                    'Discount': f"{item['discount']:.1f}%",
                    'Subtotal': f"{currency_symbol}{item['subtotal']:,.2f}"
                })

            customer_name = self.customer_input.value or 'Cash Client'
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
            payment_method = getattr(self, 'payment_method_select', None)
            method = payment_method.value if payment_method else 'Cash'

            from print_helper import print_dialog_content
            ui.add_head_html('<style> @media print { .q-dialog__inner > div { max-width: none !important; width: 100% !important; background: white !important; color: black !important; } .hide-on-print { display: none !important; } .text-white, .text-gray-400, .text-green-400, .text-orange-400, .text-purple-400, .text-red-400 { color: black !important; } [class*="bg-"] { background: white !important; } } </style>')
            with ui.dialog() as d, ui.card().classes('w-full max-w-3xl p-8').style('background: rgba(15, 15, 25, 0.82); backdrop-filter: blur(20px); border-radius: 2rem;'):
                with ui.column().classes('w-full items-center gap-6'):
                    with ui.column().classes('w-full items-center gap-1'):
                        ui.label('INVOICE').classes('text-[10px] font-black tracking-[0.3em] text-purple-400')
                        ui.label(f'#{invoice_number}').classes('text-4xl font-black text-white')
                        ui.label(company_name).classes('text-sm text-gray-400')

                    with ui.column().classes('w-full bg-white/5 rounded-2xl p-6 gap-4 border border-white/10'):
                        with ui.row().classes('w-full justify-between'):
                            ui.label('Customer').classes('text-sm text-gray-400')
                            ui.label(customer_name).classes('text-sm text-white font-bold')
                        with ui.row().classes('w-full justify-between'):
                            ui.label('Date').classes('text-sm text-gray-400')
                            ui.label(now_str).classes('text-sm text-white font-bold')
                        with ui.row().classes('w-full justify-between'):
                            ui.label('Payment').classes('text-sm text-gray-400')
                            ui.label(method).classes('text-sm text-white font-bold')

                        # Items table
                        ui.element('div').classes('w-full h-px bg-white/20 my-1')
                        with ui.column().classes('w-full gap-1'):
                            with ui.row().classes('w-full justify-between text-[9px] font-black text-purple-400/60 uppercase tracking-widest'):
                                ui.label('Item').classes('flex-1')
                                ui.label('Qty').classes('w-12 text-right')
                                ui.label('Price').classes('w-20 text-right')
                                ui.label('Disc').classes('w-12 text-right')
                                ui.label('Total').classes('w-20 text-right')
                            for item in self.rows:
                                with ui.row().classes('w-full justify-between text-xs'):
                                    ui.label(str(item['product'])).classes('flex-1 text-gray-300')
                                    ui.label(str(item['quantity'])).classes('w-12 text-right text-white font-bold')
                                    ui.label(f"{currency_symbol}{item['price']:,.2f}").classes('w-20 text-right text-gray-300')
                                    ui.label(f"{item['discount']:.0f}%").classes('w-12 text-right text-gray-300')
                                    ui.label(f"{currency_symbol}{item['subtotal']:,.2f}").classes('w-20 text-right text-white font-bold')

                        # Totals
                        ui.element('div').classes('w-full h-px bg-white/20 my-1')
                        with ui.row().classes('w-full justify-end'):
                            with ui.column().classes('gap-1'):
                                with ui.row().classes('justify-between'):
                                    ui.label('Subtotal:').classes('text-sm text-gray-400')
                                    ui.label(f'{currency_symbol}{subtotal:,.2f}').classes('text-sm text-white font-bold w-24 text-right')
                                if discount_percent > 0:
                                    with ui.row().classes('justify-between'):
                                        ui.label(f'Discount ({discount_percent:.0f}%):').classes('text-sm text-gray-400')
                                        ui.label(f'-{currency_symbol}{discount_amount:,.2f}').classes('text-sm text-red-400 font-bold w-24 text-right')
                                with ui.row().classes('justify-between pt-2 border-t border-white/10'):
                                    ui.label('TOTAL:').classes('text-base text-white font-black')
                                    ui.label(f'{currency_symbol}{final_total:,.2f}').classes('text-lg text-green-400 font-black w-24 text-right')

                    with ui.row().classes('w-full justify-center gap-4 hide-on-print'):
                        ui.button('PRINT', icon='print', on_click=lambda: ui.run_javascript(print_dialog_content())).props('flat color=purple-400').classes('font-black')
                        pdf_btn = ui.button('PDF', icon='picture_as_pdf').props('flat color=purple-400').classes('font-black')
                        ui.button('CLOSE', icon='close', on_click=d.close).props('flat color=red').classes('font-black')

                    def do_pdf():
                        d.close()
                        self.print_invoice_pdf(invoice_number, invoice_data, subtotal, discount_percent, discount_amount, final_total, company_name, currency_symbol)
                    pdf_btn.on_click(do_pdf)
            d.open()

        except Exception as e:
            ui.notify(f'Error generating invoice: {str(e)}')
            print(f'Print invoice error: {str(e)}')

    def filter_customer_rows(self, search_text):
        if not search_text:
            filtered_rows = self.customer_rows
        else:
            filtered_rows = [row for row in self.customer_rows if any(search_text.lower() in str(value).lower() for value in row.values())]

        self.customer_grid.rows = filtered_rows

        # Reset selection so the first ArrowDown navigates to the first visible row.
        # Also reset highlight index in the DOM listener (if attached).
        if hasattr(self.customer_grid, 'selected'):
            self.customer_grid.selected = []

        self.customer_grid.update()

        try:
            grid_id = getattr(self.customer_grid, 'id', '')
            ui.run_javascript(f"""
                try {{
                  const root = document.getElementById('{grid_id}') || document.querySelector('.q-table');
                  if (!root) return;
                  root.dataset.selIdx = '-1';
                }} catch(e) {{}}
            """)
        except Exception:
            pass

    def filter_product_rows(self, search_text):
        if not search_text:
            filtered_rows = self.product_rows
        else:
            filtered_rows = [row for row in self.product_rows if any(search_text.lower() in str(value).lower() for value in row.values())]
        self.product_grid.rows = filtered_rows
        if hasattr(self.product_grid, 'selected'):
            self.product_grid.selected = []
        self.product_grid.update()
        # Reset keyboard navigation index so ArrowDown starts from row 0 after filtering
        try:
            grid_id = getattr(self.product_grid, 'id', '')
            ui.run_javascript(f"""
                try {{
                  const root = document.getElementById('{grid_id}') || document.querySelector('.q-table');
                  if (!root) return;
                  root.dataset.selIdx = '-1';
                }} catch(e) {{}}
            """)
        except Exception:
            pass

    def _customer_search_arrow_down(self, dialog):
        if not self.customer_grid or not self.customer_grid.rows:
            return
        row = self.customer_grid.rows[0]
        self.customer_grid.selected = [row]
        self.customer_grid.update()
        self.customer_grid.run_method('scrollTo', 0)
        grid_id = getattr(self.customer_grid, 'id', '')
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

    def _customer_search_enter(self, dialog):
        if not self.customer_grid or not self.customer_grid.rows:
            return
        self.handle_customer_grid_click(self.customer_grid.rows[0], dialog)

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

    def handle_customer_grid_click(self, e, dialog):
        try:
            row = None
            if isinstance(e, dict):
                if 'args' in e and isinstance(e.get('args'), dict):
                    row = e['args'].get('data')
                elif 'customer_name' in e:
                    row = e
            
            if not isinstance(row, dict):
                ui.notify("Selection error: unexpected event payload", color='negative')
                dialog.close()
                return

            self.customer_input.value = row['customer_name']
            self.phone_input.value = row['phone']
            self.current_customer_id = row['id']
            self.current_customer_name = row['customer_name']
            dialog.close()
            ui.notify(f"Selected: {row['customer_name']}")
            ui.timer(0.05, lambda: self.barcode_input.run_method('focus'), once=True)
        except Exception as ex:
            ui.notify(f"Selection error: {ex}")
            dialog.close()

    def handle_product_grid_click(self, e, dialog):
        try:
            # e can be:
            # - dict payload: { args: { data: {...row...} } }
            # - NiceGUI GenericEventArguments
            # - sometimes even a dict row directly
            row = None

            if isinstance(e, dict):
                # Most common: {'args': {'data': {...}}}
                if 'args' in e and isinstance(e.get('args'), dict):
                    row = e['args'].get('data')
                # Or direct: {...row...}
                if row is None and all(k in e for k in ('barcode', 'product_name')):
                    row = e

            # If still not resolved, try NiceGUI event object
            if row is None:
                # GenericEventArguments usually has .args (dict)
                args_obj = getattr(e, 'args', None)
                if isinstance(args_obj, dict):
                    row = args_obj.get('data') or args_obj.get('item') or args_obj.get('row')

            # Final fallback: maybe the event object carries .data directly
            if row is None:
                data_obj = getattr(e, 'data', None)
                if isinstance(data_obj, dict):
                    row = data_obj

            if not isinstance(row, dict):
                # Donâ€™t hard-fail: notify and keep dialog open
                ui.notify(f"Selection error: unexpected event payload ({type(e)})", color='negative')
                return

            self.product_input.value = row.get('product_name', '')
            self.barcode_input.value = row.get('barcode', '')
            self.price_input.value = row.get('price_ttc') or row.get('price', 0)

            # Get selected currency info
            selected_currency_id = self.currency_select.value
            exchange_rate = float(self.currency_exchange_rates.get(selected_currency_id, 1.0))
            
            # Convert to selected currency if needed
            selected_currency_symbol = '$'
            for c_row in self.currency_rows:
                if c_row[0] == selected_currency_id:
                    selected_currency_symbol = c_row[2]
                    break

            if selected_currency_symbol != '$':
                self.price_input.value = float(self.price_input.value) * exchange_rate
            
            dialog.close()
            ui.notify(f"Product selected: {row.get('product_name', 'Unknown')}")

            # Focus quantity input after selection
            self.quantity_input.run_method('focus')
            ui.timer(0.01, lambda: self.quantity_input.run_method('select'), once=True)

            # Auto-add the product by calling add_product after a short delay
            # This ensures the UI is ready and all values are set
            def auto_add():
                try:
                    # Verify all fields are filled
                    if (self.barcode_input.value and self.product_input.value and 
                        self.quantity_input.value > 0 and self.price_input.value > 0):
                        self.add_product()
                except Exception as add_error:
                    ui.notify(f"Error auto-adding product: {add_error}", color='warning')

            ui.timer(0.1, auto_add, once=True)

        except Exception as ex:
            ui.notify(f"Selection error: {ex}")
            dialog.close()

    def print_invoice_pdf(self, invoice_number, invoice_data, subtotal, discount_percent, discount_amount, final_total, company_name, currency_symbol='$'):
     #"""Generate and display PDF invoice with Arabic text support"""
        try:
            import base64
            import os
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from io import BytesIO
            from datetime import datetime
            
            # Arabic processing tools
            import arabic_reshaper
            from bidi.algorithm import get_display

            # Helper function to shape and fix Arabic text direction
            def fix_arabic(text):
                """
                Mixed Arabic/English rendering:
                - Keep English (LTR) segments as-is.
                - For Arabic segments: reshape and reverse the segment only (not the whole string).
                """
                if not text:
                    return ""

                s = str(text)

                def is_arabic_char(ch: str) -> bool:
                    o = ord(ch)
                    return 0x0600 <= o <= 0x06FF or 0x0750 <= o <= 0x077F or 0x08A0 <= o <= 0x08FF

                out_parts = []
                i = 0
                while i < len(s):
                    ch = s[i]
                    arabic_segment = is_arabic_char(ch)

                    j = i
                    while j < len(s) and is_arabic_char(s[j]) == arabic_segment:
                        j += 1

                    segment = s[i:j]
                    if arabic_segment:
                        reshaped = arabic_reshaper.reshape(segment)
                        out_parts.append(reshaped)
                    else:
                        out_parts.append(segment)

                    i = j

                return "".join(out_parts)

            # Register an Arabic font.
            base_dir = os.path.dirname(__file__)
            font_candidates = [
                os.path.join(base_dir, "fonts", "Amiri-Regular.ttf"),
                os.path.join(base_dir, "Amiri-Regular.ttf"),
            ]

            PRIMARY_FONT = "Tahoma"
            registered = False
            for fp in font_candidates:
                if os.path.exists(fp):
                    pdfmetrics.registerFont(TTFont('ArabicFont', fp))
                    PRIMARY_FONT = 'ArabicFont'
                    registered = True
                    break

            if not registered:
                print("Warning: Arabic font file not found. Falling back to Helvetica.")

            # Create PDF buffer
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter,
                                leftMargin=20, rightMargin=20,
                                topMargin=30, bottomMargin=30)
            elements = []

            # Styles
            styles = getSampleStyleSheet()
            
            # Custom styles using the Arabic-capable font
            title_style = ParagraphStyle(
                'ArabicTitle',
                parent=styles['Heading1'],
                fontName=PRIMARY_FONT,
                alignment=1 # Centered
            )
            
            # FIXED: Added native wordWrap RTL engine properties 
            normal_style = ParagraphStyle(
                'ArabicNormal',
                parent=styles['Normal'],
                fontName=PRIMARY_FONT,
                fontSize=10,
                leading=14,
                alignment=2,       # Force right alignment for reading RTL content flow
                wordWrap='RTL'     # Forces ReportLab to calculate RTL word breaks natively
            )

            # Title
            title_text = f"{fix_arabic(company_name)} - Sales Invoice"
            title = Paragraph(title_text, title_style)
            elements.append(title)
            elements.append(Spacer(1, 12))

            # Invoice details (FIXED: Individual components are processed, then combined with HTML tags)
            customer_name = self.customer_input.value or 'Cash Client'
            invoice_info_text = (
                f"<b>{fix_arabic('Invoice #:')}</b> {invoice_number}<br/>"
                f"<b>{fix_arabic('Date:')}</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>"
                f"<b>{fix_arabic('Customer:')}</b> {fix_arabic(customer_name)}"
            )
            invoice_info = Paragraph(invoice_info_text, normal_style)
            elements.append(invoice_info)
            elements.append(Spacer(1, 12))

            # Prepare table headers (FIXED: Wrapped completely inside individual Paragraph wrappers)
            headers = [
                Paragraph(fix_arabic('Barcode'), normal_style), 
                Paragraph(fix_arabic('Product'), normal_style), 
                Paragraph(fix_arabic('Quantity'), normal_style), 
                Paragraph(fix_arabic('Price'), normal_style), 
                Paragraph(fix_arabic('Discount'), normal_style), 
                Paragraph(fix_arabic('Subtotal'), normal_style)
            ]
            
            table_data = [headers]
            
            # Table body processing loop (FIXED: Every cell uses flowable layout text shapes)
            for item in invoice_data:
                table_data.append([
                    Paragraph(fix_arabic(item['Barcode']), normal_style),
                    Paragraph(fix_arabic(item['Product']), normal_style),
                    Paragraph(str(item['Quantity']), normal_style),
                    Paragraph(str(item['Price']), normal_style),
                    Paragraph(str(item['Discount']), normal_style),
                    Paragraph(str(item['Subtotal']), normal_style)
                ])

            # Create table
            page_width, page_height = letter
            available_width = page_width - 40
            col_widths = [available_width * 0.15, available_width * 0.25, available_width * 0.15, available_width * 0.15, available_width * 0.15, available_width * 0.15]
            
            table = Table(table_data, colWidths=col_widths)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white), # Clean white backing for data rows
                ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey) # Cleaner table styling grids
            ]))

            elements.append(table)
            elements.append(Spacer(1, 12))

            # Totals section
            totals_data = []
            if discount_percent > 0 or discount_amount > 0:
                totals_data.append([Paragraph(fix_arabic('Subtotal:'), normal_style), f"{currency_symbol}{subtotal:,.2f}"])
                if discount_percent > 0:
                    totals_data.append([Paragraph(fix_arabic(f'Discount ({discount_percent}%):'), normal_style), f"-{currency_symbol}{subtotal * discount_percent / 100:,.2f}"])
                if discount_amount > 0:
                    totals_data.append([Paragraph(fix_arabic('Discount Amount:'), normal_style), f"-{currency_symbol}{discount_amount:,.2f}"])

            totals_data.append([Paragraph(f"<b>{fix_arabic('Grand Total:')}</b>", normal_style), f"{currency_symbol}{final_total:,.2f}"])

            totals_table = Table(totals_data, colWidths=[available_width * 0.7, available_width * 0.3])
            totals_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey)
            ]))

            elements.append(totals_table)

            # Build PDF
            doc.build(elements)

            # Get PDF bytes
            pdf_bytes = buffer.getvalue()
            buffer.close()

            from pdf_viewer_helper import show_pdf_modal
            show_pdf_modal(pdf_bytes, filename='Sales_Invoice.pdf', title='Sales Invoice PDF')
            ui.notify('Sales invoice PDF generated and displayed', color='green')

        except Exception as e:
            import traceback
            ui.notify(f'Error generating PDF: {str(e)}', color='negative')
            print('PDF generation error:', str(e))
            print(traceback.format_exc())
        
                            
    def open_edit_dialog(self, row_data):
        with ui.dialog() as dialog, ui.card().classes('glass p-8 border border-white/10').style('background: rgba(15, 15, 25, 0.82); backdrop-filter: blur(20px); border-radius: 2rem; width: 420px;'):
            # Header
            with ui.row().classes('w-full items-center justify-between mb-4'):
                ui.label('Edit Product').classes('text-2xl font-black text-white').style('font-family: "Outfit", sans-serif;')
                ui.icon('edit', size='1.5rem').classes('text-purple-400 opacity-80')
            
            ui.label(f"Modifying: {row_data.get('product', 'Unknown')}").classes('text-xs font-bold text-gray-400 uppercase tracking-widest mb-6 block')

            with ui.column().classes('w-full gap-5'):
                # Inputs with glass/dark theme props
                quantity = ui.number('Quantity', value=row_data['quantity']).props('outlined dense dark color=purple stack-label').classes('w-full text-white')
                discount = ui.number('Discount %', value=row_data['discount']).props('outlined dense dark color=purple stack-label').classes('w-full text-white')
                price = ui.number('Unit Price', value=row_data['price']).props('outlined dense dark color=purple stack-label').classes('w-full text-white')
                
                def save():
                    self.save_edited_row(row_data, quantity.value, discount.value, price.value, dialog)

                def delete():
                    self.delete_row(row_data, dialog)

                # Action Buttons
                with ui.row().classes('w-full justify-end mt-8 gap-3'):
                    ui.button('Delete', on_click=delete).props('flat text-color=red-4').classes('px-4 rounded-xl hover:bg-red-500/10 font-bold text-xs uppercase tracking-widest')
                    ui.button('Cancel', on_click=dialog.close).props('flat text-color=grey-5').classes('px-4 rounded-xl hover:bg-white/5 font-bold text-xs uppercase tracking-widest')
                    ui.button('Update Item', on_click=save).props('unelevated color=purple').classes('px-6 py-2 rounded-xl font-black text-xs uppercase tracking-widest shadow-xl shadow-purple-500/20')
        dialog.open()

    def save_edited_row(self, original_row, new_quantity, new_discount, new_price, dialog):
        try:
            row_index = next(i for i, row in enumerate(self.rows) 
                           if row['barcode'] == original_row['barcode'] and 
                              row['product'] == original_row['product'])
            
            old_quantity = self.rows[row_index]['quantity']
            old_subtotal = self.rows[row_index]['subtotal']
            
            # Check if new quantity exceeds available stock
            product_id = connection.getid('select id from products where product_name = ?', [original_row['product']])
            stock_result = []
            connection.contogetrows(f"SELECT stock_quantity FROM products WHERE id = {product_id}", stock_result)
            
            # Calculate available stock including the old quantity that will be restored
            available_stock = stock_result[0][0] + old_quantity if stock_result else 0
            
            if int(new_quantity) > available_stock:
                ui.notify(f'Insufficient stock! Available: {available_stock}, Requested: {new_quantity}')
                return
            
            self.rows[row_index]['quantity'] = int(new_quantity)
            self.rows[row_index]['discount'] = float(new_discount)
            self.rows[row_index]['price'] = float(new_price)
            
            # Fetch VAT status for the product
            product_id = connection.getid('select id from products where product_name = ?', [self.rows[row_index]['product']])
            vat_chk = []
            connection.contogetrows(f"SELECT is_vat_subjected FROM products WHERE id = {product_id}", vat_chk)
            is_vat_subjected = vat_chk[0][0] if vat_chk else False
            
            vat_pct = 11.0 if is_vat_subjected else 0.0
            
            # new_price is TTC. Extract HT for VAT calculation.
            price_ttc = float(new_price)
            price_ht = price_ttc / (1 + vat_pct / 100)
            
            total_ttc = (int(new_quantity) * price_ttc) * (1 - float(new_discount) / 100)
            total_ht = total_ttc / (1 + vat_pct / 100)
            vat_amount = total_ttc - total_ht
            
            self.rows[row_index]['vat_percentage'] = vat_pct
            self.rows[row_index]['vat_amount'] = vat_amount
            self.rows[row_index]['subtotal'] = round(total_ttc, 2)
            
            self.total_amount = self.total_amount - old_subtotal + self.rows[row_index]['subtotal']
            self.update_totals()
            
            # Stock update moved to save/update/delete (persisted invoice) only.
            self.aggrid.options['rowData'] = self.rows
            self.aggrid.update()
            
            dialog.close()
            ui.notify('Product updated successfully')
            
        except Exception as e:
            ui.notify(f'Error updating product: {str(e)}')

    def delete_row(self, row_data, dialog):
        try:
            row_index = next(i for i, row in enumerate(self.rows) 
                           if row['barcode'] == row_data['barcode'] and 
                              row['product'] == row_data['product'])
            
            # Get the quantity to restore to stock
            quantity_to_restore = self.rows[row_index]['quantity']
            
            self.total_amount -= self.rows[row_index]['subtotal']
            self.update_totals()
            
            # Stock update moved to save/update/delete (persisted invoice) only.
            del self.rows[row_index]
            self.aggrid.options['rowData'] = self.rows
            self.aggrid.update()
            
            dialog.close()
            ui.notify('Product removed successfully')
            
        except Exception as e:
            ui.notify(f'Error removing product: {str(e)}')

    def total_input_changed(self, e):
        if getattr(self, '_updating_totals', False): return
        self._updating_totals = True
        try:
            subtotal = sum(row['subtotal'] for row in self.rows)
            target_val = float(e.value or 0)
            discount_amt = max(0.0, subtotal - target_val)
            discount_pct = round((discount_amt / subtotal * 100) if subtotal > 0 else 0, 2)
            self.discount_amount_input.value = round(discount_amt, 2)
            self.discount_percent_input.value = discount_pct
            self.total_amount = target_val
            ui.run_javascript(f'window.__invoice_is_open = {str(len(self.rows) > 0).lower()};')
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
            discount_amt = max(0.0, subtotal - target_total)
            discount_pct = round((discount_amt / subtotal * 100) if subtotal > 0 else 0, 2)
            self.discount_amount_input.value = round(discount_amt, 2)
            self.discount_percent_input.value = discount_pct
            self.total_amount = round(target_total, 2)
            self.update_totals()
        except Exception:
            pass

    def _on_discount_mode_change(self, e):
        """Toggle between amount and percentage discount mode."""
        is_pct = e.value == '%'
        self.discount_amount_input.visible = not is_pct
        self.discount_percent_input.visible = is_pct
        self.update_totals()

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

            final_total = subtotal - discount_amount
            self.total_amount = final_total

            selected_currency_id = self.currency_select.value
            currency_symbol = '$'
            for row in self.currency_rows:
                if row[0] == selected_currency_id:
                    currency_symbol = row[2]
                    break
            if hasattr(self, 'ttc_currency_label'):
                self.ttc_currency_label.text = currency_symbol

            self.subtotal_label.text = f"Total HT: {currency_symbol}{subtotal - total_vat:,.2f}"
            self.vat_label.text = f"Total VAT: {currency_symbol}{total_vat:,.2f}"
            
            if hasattr(self, 'total_input'):
                self.total_input.value = round(final_total, 2)
            elif hasattr(self, 'total_label'):
                self.total_label.text = f"Total TTC: {currency_symbol}{final_total:,.2f}"
            
            if hasattr(self, 'll_total_input') and self.ll_currency_id is not None:
                ll_rate = self.currency_exchange_rates.get(self.ll_currency_id, 1.0)
                selected_rate = self.currency_exchange_rates.get(selected_currency_id, 1.0)
                ll_amount = final_total * (ll_rate / selected_rate)
                self.ll_total_input.value = round(ll_amount, 2)
            
            ui.run_javascript(f'window.__invoice_is_open = {str(len(self.rows) > 0).lower()};')
        finally:
            self._updating_totals = False

    def on_discount_percent_change(self, e):
        """When user types a discount percentage, compute the equivalent amount and refresh total."""
        if getattr(self, '_updating_discount', False): return
        self._updating_discount = True
        try:
            subtotal = sum(row['subtotal'] for row in self.rows)
            pct = float(e.value or 0)
            amount = round(subtotal * pct / 100, 2)
            self.discount_amount_input.value = amount
            self.update_totals()
        finally:
            self._updating_discount = False

    def on_discount_amount_change(self, e):
        """When user types a discount amount, compute the equivalent percentage and refresh total."""
        if getattr(self, '_updating_discount', False): return
        self._updating_discount = True
        try:
            subtotal = sum(row['subtotal'] for row in self.rows)
            amount = float(e.value or 0)
            pct = round((amount / subtotal * 100) if subtotal > 0 else 0, 2)
            self.discount_percent_input.value = pct
            self.update_totals()
        finally:
            self._updating_discount = False


    def toggle_history(self):
        """Toggle the visibility of the sales history panel"""
        if hasattr(self, 'history_panel'):
            self.history_panel.visible = not self.history_panel.visible
            if hasattr(self, 'show_history_btn'):
                self.show_history_btn.visible = not self.history_panel.visible
            ui.notify('History ' + ('hidden' if not self.history_panel.visible else 'shown'), color='info', duration=1)

    def get_max_sale_id(self):
        try:
            max_id_result = []
            connection.contogetrows("SELECT MAX(id) FROM sales", max_id_result)
            return max_id_result[0][0] if max_id_result and max_id_result[0][0] else 0
        except Exception as e:
            return 0

    def show_undo_confirmation(self):
        with ui.dialog() as dialog, ui.card().classes('glass p-8 border border-white/10').style('background: rgba(15, 15, 25, 0.82); backdrop-filter: blur(20px); border-radius: 2rem; width: 400px;'):
            # Header
            with ui.row().classes('w-full items-center justify-between mb-4'):
                ui.label('Undo Changes').classes('text-2xl font-black text-white').style('font-family: "Outfit", sans-serif;')
                ui.icon('undo', size='1.5rem').classes('text-warning opacity-80')
            
            ui.label('Are you sure you want to clear the current invoice and undo all changes?').classes('text-sm text-gray-300 mb-8 block font-medium')

            with ui.row().classes('w-full justify-end gap-3'):
                ui.button('Cancel', on_click=dialog.close).props('flat text-color=grey-5').classes('px-4 rounded-xl hover:bg-white/5 font-bold text-xs uppercase tracking-widest')
                ui.button('Yes, Undo', on_click=lambda: self.perform_undo(dialog)).props('unelevated color=warning').classes('px-6 py-2 rounded-xl font-black text-xs uppercase tracking-widest shadow-xl shadow-warning/20')
        dialog.open()


    def delete_sale(self):
        """Show confirmation dialog before deleting a sale"""
        try:
            sale_id = self.current_sale_id or self.get_max_sale_id()
            if not sale_id:
                ui.notify('No sale data available to delete')
                return
            
            with ui.dialog() as dialog, ui.card().classes('glass p-8 border border-white/10').style('background: rgba(15, 15, 25, 0.82); backdrop-filter: blur(20px); border-radius: 2rem; width: 440px;'):
                # Header
                with ui.row().classes('w-full items-center justify-between mb-4'):
                    ui.label('Delete Sale').classes('text-2xl font-black text-white').style('font-family: "Outfit", sans-serif;')
                    ui.icon('warning', size='1.5rem').classes('text-red-500 opacity-80')
                
                ui.label(f'Are you sure you want to delete sale ID: {sale_id}?').classes('text-sm text-gray-300 font-bold mb-2 block')
                ui.label('This will permanently remove the sale and all its items from the database. This action cannot be undone.').classes('text-xs text-gray-400 mb-8 block leading-relaxed')

                with ui.row().classes('w-full justify-end gap-3'):
                    ui.button('No, keep it', on_click=dialog.close).props('flat text-color=grey-5').classes('px-4 rounded-xl hover:bg-white/5 font-bold text-xs uppercase tracking-widest')
                    ui.button('Yes, Delete', on_click=lambda: self.perform_delete_sale(sale_id, dialog)).props('unelevated color=negative').classes('px-6 py-2 rounded-xl font-black text-xs uppercase tracking-widest shadow-xl shadow-red-500/20')
            dialog.open()
            
        except Exception as e:
            ui.notify(f'Error preparing delete: {str(e)}')

    async def perform_delete_sale(self, sale_id, dialog):
        """Perform the actual deletion after confirmation"""
        async with loading_indicator.show_loading('delete_sale', 'Deleting sale...', overlay=True):
            try:
                # Get the sale status before deletion
                sale_data = []
                connection.contogetrows(
                    "SELECT status FROM sales WHERE id = ?",
                    sale_data,
                    [sale_id]
                )

                if sale_data:
                    sale_status = str(sale_data[0][0] or '')
                    is_performa = sale_status == 'Performa'

                    if not is_performa:
                        # --- STOCK UPDATE (DELETE branch) ---
                        # Restore stock by adding back quantities from sale_items
                        prev_items = []
                        connection.contogetrows(
                            "SELECT product_id, quantity FROM sale_items WHERE sales_id = ?",
                            prev_items,
                            [sale_id]
                        )
                        for item in prev_items:
                            prev_product_id = int(item[0])
                            prev_qty = int(item[1] or 0)
                            connection.insertingtodatabase(
                                "UPDATE products SET stock_quantity = stock_quantity + ? WHERE id = ?",
                                (prev_qty, prev_product_id)
                            )

                    # Always delete sale items and sale header
                    connection.deleterow("DELETE FROM sale_items WHERE sales_id = ?", [sale_id])

                    # For proforma: skip finance/accounting side effects
                    if not is_performa:
                        connection.deleterow("DELETE FROM sales_payment WHERE sales_id = ?", [sale_id])

                        # Clean up accounting entries
                        jvs = []
                        connection.contogetrows(
                            "SELECT jv_id FROM accounting_transactions WHERE reference_type IN ('Sale', 'Sale Receipt') AND reference_id = ?",
                            jvs,
                            [str(sale_id)]
                        )
                        for jv in jvs:
                            connection.deleterow("DELETE FROM accounting_transaction_lines WHERE jv_id = ?", (jv[0],))
                            connection.deleterow("DELETE FROM accounting_transactions WHERE jv_id = ?", (jv[0],))

                    connection.deleterow("DELETE FROM sales WHERE id = ?", [sale_id])

                ui.notify(f'Sale {sale_id} deleted successfully')
                dialog.close()

                # Refresh displays
                self.sales_aggrid.update()
                self.clear_inputs()
                await self.refresh_sales_table()

            except Exception as e:
                ui.notify(f'Error deleting sale: {str(e)}')
                dialog.close()

    def perform_undo(self, dialog):
        dialog.close()

        # Always activate history grid on undo (clear_inputs() may re-dim it).
        try:
            self.sales_aggrid.classes(remove='dimmed')
        except Exception:
            pass

        if getattr(self, 'all_sales_data', None):
            max_sale = max(self.all_sales_data, key=lambda x: x['id'])
            class MockEvent:
                args = {'data': max_sale}

            def _post_revert_activate():
                try:
                    self.sales_aggrid.classes(remove='dimmed')
                    self.sales_aggrid.update()
                except Exception:
                    pass

            ui.timer(0.01, lambda: self.handle_sales_aggrid_click_wrapper(MockEvent()), once=True)
            ui.timer(0.05, _post_revert_activate, once=True)
            ui.notify('Reverted to the latest sale')
        else:
            self.rows.clear()
            self.aggrid.options['rowData'] = self.rows
            self.aggrid.update()
            self.total_amount = 0
            self.update_totals()
            # clear_inputs() would normally dim history; for Undo we want history active
            self.clear_inputs(dim_history=False)
            self.sales_aggrid.classes(remove='dimmed')
            ui.notify('Undo fully cleared (No history)')
        
        if hasattr(self, 'action_bar'):
            self.action_bar.reset_state()

    async def refresh_sales_table(self):
        """Refresh sales table with loading indicator"""
        async with loading_indicator.show_loading('refresh_sales', 'Refreshing sales data...', overlay=True):
            try:
                raw_sales_data = []
                connection.contogetrows(
                     "SELECT s.id, s.sale_date, c.customer_name, s.total_amount, s.invoice_number, cur.currency_name, s.payment_status, s.currency_id, s.status, u.username "
                     "FROM sales s "
                     "INNER JOIN customers c ON c.id = s.customer_id "
                     "LEFT JOIN currencies cur ON cur.id = s.currency_id "
                     "LEFT JOIN users u ON u.id = s.user_id "
                      "ORDER BY s.id DESC",
                     raw_sales_data
                 )

                sales_data = []
                for row in raw_sales_data:
                    # Get exchange rate for this transaction to show original currency total
                    currency_id = row[7]
                    exchange_rate = float(self.currency_exchange_rates.get(currency_id, 1.0))
                    
                    sales_data.append({
                        'id': row[0],
                        'sale_date': str(row[1]),
                        'customer_name': str(row[2]),
                        'total_amount': float(row[3]) * exchange_rate,
                        'invoice_number': str(row[4]),
                        'currency_name': str(row[5]) if row[5] else '',
                        'payment_status': str(row[6]),
                        'currency_id': row[7],
                        'status': str(row[8]) if len(row) > 8 else 'Sale',
                        'username': str(row[9]) if len(row) > 9 else 'N/A'
                    })

                # Store full data for filtering
                self.all_sales_data = sales_data
                # Update the sales_aggrid with fresh data
                self.sales_aggrid.options['rowData'] = sales_data
                self.sales_aggrid.update()
                self.sales_aggrid.classes(remove='dimmed')
                # Update totals after refresh
                self.update_totals()

                ui.notify('Sales table refreshed successfully')

            except Exception as e:
                ui.notify(f'Error refreshing sales table: {str(e)}')

    async def save_sale(self, is_order=False):
        async with loading_indicator.show_loading('save_sale', 'Saving sale...', overlay=True):
            try:
                if not self.rows:
                    ui.notify('No items to save!')
                    return

                sale_date = str(self.date_input.value)
                created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                customer_name = self.customer_input.value or 'Cash Client'
                customer_id = connection.getid('select id from customers where customer_name = ?', [customer_name])

                # Get payment method and determine payment status
                payment_method = self.payment_method.value
                
                is_performa = getattr(self, 'sale_type', None) and self.sale_type.value == 'Performa'

                # If it's a proforma, persist as proforma with no payment status side-effects
                if is_performa:
                    status = 'Performa'
                    payment_status = ''  # stored but should not drive cash/on-account logic
                else:
                    # If it's an order, status is 'Order' and payment is always 'pending'
                    # If it's a sale, status is 'Sale' and payment depends on method
                    status = 'Order' if is_order else 'Sale'
                    payment_status = 'pending' if is_order or payment_method != 'Cash' else 'completed'

                # Get current user for tracing
                user = session_storage.get('user')
                user_id = user.get('user_id') if user else None

                subtotal = sum(row['subtotal'] for row in self.rows)
                discount_amount = float(self.discount_amount_input.value or 0)
                final_total = subtotal - discount_amount

                # Normalize values to USD for consistent database storage and profit calculation
                selected_currency_id = self.currency_select.value
                exchange_rate = float(self.currency_exchange_rates.get(selected_currency_id, 1.0))
                
                normalized_subtotal = subtotal / exchange_rate
                normalized_discount = discount_amount / exchange_rate
                normalized_total = final_total / exchange_rate

                if hasattr(self, 'current_sale_id') and self.current_sale_id:
                    # Retrieve previous payment status and total amount for reversal logic
                    previous_sale_data = []
                    connection.contogetrows(
                        "SELECT payment_status, total_amount FROM sales WHERE id = ?",
                        previous_sale_data,
                        (self.current_sale_id,)
                    )
                    previous_payment_status = previous_sale_data[0][0] if previous_sale_data else None
                    previous_total_amount = float(previous_sale_data[0][1]) if previous_sale_data else 0.0

                    # Reverse previous payment effects if payment method changed
                    # Proforma invoices are display-only: no cash/customer side-effects.
                    if not is_performa:
                        if previous_payment_status != payment_status:
                            if previous_payment_status == 'completed':  # Previously Cash
                                # Reverse cash drawer operation (subtract previous amount)
                                user = session_storage.get('user')
                                user_id = user.get('user_id') if user else None
                                notes = f"Sale update reversal {self.current_sale_id}"
                                success = connection.update_cash_drawer_balance(previous_total_amount, 'Out', user_id, notes)
                                if success:
                                    ui.notify(f'Reversed previous cash drawer operation of -${previous_total_amount:,.2f}')
                                else:
                                    ui.notify('Warning: Failed to reverse previous cash drawer operation', color='orange')
                            elif previous_payment_status == 'pending':  # Previously On Account
                                # Reverse customer balance (subtract previous amount)
                                if customer_id:
                                    connection.insertingtodatabase(
                                        "UPDATE customers SET balance = balance - ? WHERE id = ?",
                                        (previous_total_amount, customer_id)
                                    )
                                    ui.notify(f'Reversed previous customer balance of -${previous_total_amount:,.2f}')

                    # Fetch VAT values
                    normalized_total_vat = sum(row.get('vat_amount', 0) for row in self.rows) / exchange_rate
                    normalized_subtotal = (subtotal / exchange_rate) - normalized_total_vat
                    
                    sale_sql = """
                        UPDATE sales
                        SET sale_date = ?, customer_id = ?, subtotal = ?, discount_amount = ?,
                            total_amount = ?, created_at = ?, payment_status = ?, currency_id = ?,
                            user_id = ?, status = ?, total_vat = ?
                        WHERE id = ?
                    """
                    sale_values = (sale_date, customer_id, normalized_subtotal, normalized_discount, normalized_total, created_at, payment_status, selected_currency_id, user_id, status, normalized_total_vat, self.current_sale_id)
                    connection.insertingtodatabase(sale_sql, sale_values)

                    if not is_performa:
                        # --- STOCK UPDATE (UPDATE branch) ---
                        # Reverse previous saved stock (sale items increased? for sales it was decreased, so reverse by adding back)
                        prev_items = []
                        connection.contogetrows(
                            "SELECT product_id, quantity FROM sale_items WHERE sales_id = ?",
                            prev_items,
                            (self.current_sale_id,)
                        )
                        for item in prev_items:
                            prev_product_id = int(item[0])
                            prev_qty = int(item[1] or 0)
                            connection.insertingtodatabase(
                                "UPDATE products SET stock_quantity = stock_quantity + ? WHERE id = ?",
                                (prev_qty, prev_product_id)
                            )

                    delete_items_sql = "DELETE FROM sale_items WHERE sales_id = ?"
                    connection.insertingtodatabase(delete_items_sql, [self.current_sale_id])

                    for row in self.rows:
                        barcode = row['barcode']
                        product_id_from_barcode = connection.getid('select id from products where barcode = ?', [barcode])
                        if not product_id_from_barcode:
                            raise ValueError(f"Product not found for barcode: {barcode}")
                        final_product_id = product_id_from_barcode

                        sale_item_sql = """
                            INSERT INTO sale_items (sales_id, barcode, product_id, quantity, unit_price, total_price, discount_amount, vat_amount, vat_percentage)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """
                        sale_item_values = (
                            self.current_sale_id,
                            row['barcode'],
                            final_product_id,
                            row['quantity'],
                            row['price'] / exchange_rate,
                            row['subtotal'] / exchange_rate,
                            row['discount'] / exchange_rate,
                            row.get('vat_amount', 0) / exchange_rate,
                            row.get('vat_percentage', 0)
                        )
                        connection.insertingtodatabase(sale_item_sql, sale_item_values)

                        if not is_performa:
                            # Sales decreases stock
                            connection.insertingtodatabase(
                                "UPDATE products SET stock_quantity = stock_quantity - ? WHERE id = ?",
                                (int(row['quantity']), int(final_product_id))
                            )

                    # Clean up old payment record first (skip for proforma)
                    if not is_performa:
                        delete_payment_sql = "DELETE FROM sales_payment WHERE sales_id = ?"
                        connection.insertingtodatabase(delete_payment_sql, [self.current_sale_id])

                        # Insert into sales_payment table based on payment method
                        if payment_method == 'Cash':
                            debit = final_total
                            credit = final_total
                        else:  # On Account
                            debit = 0
                            credit = final_total

                        sales_payment_sql = """
                            INSERT INTO sales_payment (sales_id, customer_id, invoice_number, total_amount, sale_date, payment_status, debit, credit, notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """
                        sales_payment_values = (
                            self.current_sale_id,
                            customer_id,
                            self.invoicenumber,
                            normalized_total,
                            sale_date,
                            payment_status,
                            normalized_total if payment_method == 'Cash' else 0,
                            normalized_total,
                            f"Sale payment recorded for sale ID {self.current_sale_id}"
                        )
                        connection.insertingtodatabase(sales_payment_sql, sales_payment_values)

                        import accounting_helpers
                        import business_track_settings

                        # Ensure each customer has exactly ONE aux code
                        customer_name = ""
                        cust_res = []
                        connection.contogetrows("SELECT customer_name FROM customers WHERE id = ?", cust_res, (customer_id,))
                        if cust_res:
                            customer_name = cust_res[0][0]
                        customer_account = accounting_helpers.ensure_customer_auxiliary(
                            customer_id, customer_name=customer_name, fallback_account_number='4111'
                        )

                        vat_account = accounting_helpers.ensure_vat_auxiliary('Customer', customer_id, customer_name, customer_account)

                        # Determine revenue account based on VAT status
                        has_vat = any(row.get('vat_percentage', 0) > 0 for row in self.rows)
                        revenue_account_base = business_track_settings.get_sales_account(has_vat)
                        revenue_base_ledger = str(revenue_account_base).split('.')[0] if revenue_account_base else '7010'

                        # Derive a stable base account per sale invoice.
                        revenue_aux_number = str(revenue_base_ledger)
                        col = 0 if has_vat else 1
                        discount_aux_number = business_track_settings._get_account('sales', 1, col, '7090.000001') if normalized_discount > 0 else None

                        # Always debit customer and credit sales/VAT for the invoice
                        jv = [
                            {'account': customer_account,     'debit': normalized_total, 'credit': 0},
                            {'account': revenue_aux_number,  'debit': 0,                 'credit': normalized_subtotal},
                            {'account': vat_account,         'debit': 0,                 'credit': normalized_total_vat},
                        ]

                        # Add discount as separate debit line when present
                        if discount_aux_number:
                            jv.append({'account': discount_aux_number, 'debit': normalized_discount, 'credit': 0})

                        accounting_helpers.save_accounting_transaction(
                            'Sale', self.current_sale_id, jv, description=f"Sale {self.invoicenumber}"
                        )

                        # â”€â”€ Persist auxiliary linkage â”€â”€
                        try:
                            connection.insertingtodatabase(
                                "DELETE FROM sales_invoice_account_links WHERE sales_invoice_number = ?",
                                (str(self.invoicenumber),)
                            )
                        except Exception:
                            pass

                        try:
                            connection.insertingtodatabase(
                                """
                                INSERT INTO sales_invoice_account_links
                                (sales_invoice_number, sale_id, revenue_aux_number, discount_aux_number, vat_aux_number)
                                VALUES (?, ?, ?, ?, ?)
                                """,
                                (
                                    str(self.invoicenumber),
                                    int(self.current_sale_id),
                                    revenue_aux_number,
                                    discount_aux_number,
                                    vat_account
                                )
                            )
                        except Exception:
                            pass

                        if payment_method != 'On Account':
                            payment_aux = business_track_settings.get_payment_account(payment_method)

                            payment_lines = []
                            if str(payment_aux).strip() == '5300':
                                aux_id, _full_num = accounting_helpers._get_auxiliary_id_and_full_number_for_ledger_base('5300')
                                payment_lines = [
                                    {'account': '5300', 'auxiliary_id': aux_id, 'debit': normalized_total, 'credit': 0},
                                    {'account': customer_account, 'debit': 0, 'credit': normalized_total},
                                ]
                            else:
                                payment_lines = [
                                    {'account': payment_aux, 'debit': normalized_total, 'credit': 0},
                                    {'account': customer_account, 'debit': 0, 'credit': normalized_total},
                                ]

                            accounting_helpers.save_accounting_transaction(
                                'Sale Receipt', self.current_sale_id, payment_lines, description=f"{payment_method} Receipt for Sale {self.invoicenumber}"
                            )
                        else:
                            accounting_helpers.save_accounting_transaction('Sale Receipt', self.current_sale_id, [])

                        ui.notify(f'Sale updated successfully! ID: {self.current_sale_id}')

                        # Apply new payment effects
                        if customer_id and payment_method == 'On Account':
                            current_balance_result = []
                            connection.contogetrows("SELECT balance FROM customers WHERE id = ?", current_balance_result, (customer_id,))
                            current_balance = float(current_balance_result[0][0]) if current_balance_result else 0.0

                            new_balance = current_balance + normalized_total
                            connection.insertingtodatabase(
                                "UPDATE customers SET balance = ? WHERE id = ?",
                                (new_balance, customer_id)
                            )
                            ui.notify(f'Customer balance updated successfully! New balance: ${new_balance:,.2f}')
                        elif payment_method == 'Cash':
                            notes = f"Sale update {self.current_sale_id}"
                            success = connection.update_cash_drawer_balance(normalized_total, 'In', session_storage.get('user')['user_id'], notes)
                            if success:
                                ui.notify(f'Cash payment recorded! Cash drawer updated by +${normalized_total:,.2f}')
                            else:
                                ui.notify('Warning: Cash payment saved but cash drawer update failed', color='orange')
                    else:
                        ui.notify(f'Performa updated successfully (display-only)! ID: {self.current_sale_id}')

                else:
                    invoice_number = self.generate_invoice_number()

                    # Fetch VAT values
                    normalized_total_vat = sum(row.get('vat_amount', 0) for row in self.rows) / exchange_rate
                    normalized_subtotal = (subtotal / exchange_rate) - normalized_total_vat

                    sale_sql = """
                        INSERT INTO sales (sale_date, customer_id, subtotal, discount_amount, total_amount, invoice_number, created_at, payment_status, currency_id, user_id, status, total_vat)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    sale_values = (sale_date, customer_id, normalized_subtotal, normalized_discount, normalized_total, invoice_number, created_at, payment_status, selected_currency_id, user_id, status, normalized_total_vat)
                    connection.insertingtodatabase(sale_sql, sale_values)

                    last_sale_id = connection.getid("SELECT MAX(id) FROM sales", [])

                    for row in self.rows:
                        barcode = row['barcode']
                        product_id_from_barcode = connection.getid('select id from products where barcode = ?', [barcode])
                        if not product_id_from_barcode:
                            raise ValueError(f"Product not found for barcode: {barcode}")
                        final_product_id = product_id_from_barcode

                        sale_item_sql = """
                            INSERT INTO sale_items (sales_id, barcode, product_id, quantity, unit_price, total_price, discount_amount, vat_amount, vat_percentage)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """
                        sale_item_values = (
                            last_sale_id,
                            row['barcode'],
                            final_product_id,
                            row['quantity'],
                            row['price'] / exchange_rate,
                            row['subtotal'] / exchange_rate,
                            row['discount'] / exchange_rate,
                            row.get('vat_amount', 0) / exchange_rate,
                            row.get('vat_percentage', 0)
                        )
                        connection.insertingtodatabase(sale_item_sql, sale_item_values)

                        if not is_performa:
                            # Sales decreases stock
                            connection.insertingtodatabase(
                                "UPDATE products SET stock_quantity = stock_quantity - ? WHERE id = ?",
                                (int(row['quantity']), int(final_product_id))
                            )

                    if not is_performa:
                        # Insert into sales_payment table based on payment method
                        if payment_method == 'Cash':
                            debit = final_total
                            credit = final_total
                        else:  # On Account
                            debit = 0
                            credit = final_total

                        sales_payment_sql = """
                            INSERT INTO sales_payment (sales_id, customer_id, invoice_number, total_amount, sale_date, payment_status, debit, credit, notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """
                        sales_payment_values = (
                            last_sale_id,
                            customer_id,
                            invoice_number,
                            normalized_total,
                            sale_date,
                            payment_status,
                            normalized_total if payment_method == 'Cash' else 0,
                            normalized_total,
                            f"Sale payment recorded for sale ID {last_sale_id}"
                        )
                        connection.insertingtodatabase(sales_payment_sql, sales_payment_values)

                        import accounting_helpers
                        import business_track_settings

                        # Ensure each customer has exactly ONE aux code
                        customer_name = ""
                        cust_res = []
                        connection.contogetrows("SELECT customer_name FROM customers WHERE id = ?", cust_res, (customer_id,))
                        if cust_res:
                            customer_name = cust_res[0][0]
                        customer_account = accounting_helpers.ensure_customer_auxiliary(
                            customer_id, customer_name=customer_name, fallback_account_number='4111'
                        )

                        vat_account = accounting_helpers.ensure_vat_auxiliary('Customer', customer_id, customer_name, customer_account)

                        # Determine revenue account based on VAT status
                        has_vat = any(row.get('vat_percentage', 0) > 0 for row in self.rows)
                        revenue_account_base = business_track_settings.get_sales_account(has_vat)
                        revenue_base_ledger = str(revenue_account_base).split('.')[0] if revenue_account_base else '7010'

                        # Derive a stable base account per sale invoice.
                        revenue_aux_number = str(revenue_base_ledger)
                        col = 0 if has_vat else 1
                        discount_aux_number = business_track_settings._get_account('sales', 1, col, '7090.000001') if normalized_discount > 0 else None

                        # Always debit customer and credit sales/VAT for the invoice
                        jv = [
                            {'account': customer_account,     'debit': normalized_total, 'credit': 0},
                            {'account': revenue_aux_number,  'debit': 0,                 'credit': normalized_subtotal},
                            {'account': vat_account,         'debit': 0,                 'credit': normalized_total_vat},
                        ]

                        # Add discount as separate debit line when present
                        if discount_aux_number:
                            jv.append({'account': discount_aux_number, 'debit': normalized_discount, 'credit': 0})

                        accounting_helpers.save_accounting_transaction(
                            'Sale', last_sale_id, jv, description=f"Sale {invoice_number}"
                        )

                        # Persist auxiliary linkage (for /auxiliary & auditing)
                        try:
                            connection.insertingtodatabase(
                                "DELETE FROM sales_invoice_account_links WHERE sales_invoice_number = ?",
                                (str(invoice_number),)
                            )
                        except Exception:
                            pass

                        try:
                            connection.insertingtodatabase(
                                """
                                INSERT INTO sales_invoice_account_links
                                (sales_invoice_number, sale_id, revenue_aux_number, discount_aux_number, vat_aux_number)
                                VALUES (?, ?, ?, ?, ?)
                                """,
                                (
                                    str(invoice_number),
                                    int(last_sale_id),
                                    revenue_aux_number,
                                    discount_aux_number,
                                    vat_account
                                )
                            )
                        except Exception:
                            pass

                        if payment_method == 'Cash':
                            caisse_account = business_track_settings.get_payment_account(payment_method)
                            accounting_helpers.ensure_caisse_auxiliary(caisse_account)
                            payment_jv = [
                                {'account': caisse_account,    'debit': normalized_total, 'credit': 0},
                                {'account': customer_account, 'debit': 0, 'credit': normalized_total},
                            ]
                            accounting_helpers.save_accounting_transaction(
                                'Sale Receipt', last_sale_id, payment_jv, description=f"Cash Receipt for Sale {invoice_number}"
                            )

                        ui.notify(f'{"Order" if is_order else "Sale"} saved successfully! Invoice: {invoice_number}')

                        # Update customer balance only if payment method is "On Account"
                        if customer_id and payment_method == 'On Account':
                            connection.update_customerbalance(
                                "UPDATE customers SET balance = balance + ? WHERE id = ?",
                                (normalized_total, customer_id)
                            )
                            ui.notify(f'Customer balance updated successfully! Total: ${normalized_total:,.2f}')
                        elif payment_method == 'Cash':
                            # Update cash drawer balance (USD) for cash payment
                            notes = f"New sale {last_sale_id}"
                            success = connection.update_cash_drawer_balance(normalized_total, 'In', session_storage.get('user')['user_id'], notes)
                            if success:
                                ui.notify(f'Cash payment recorded! Cash drawer updated by +${normalized_total:,.2f}')
                            else:
                                ui.notify('Warning: Cash payment saved but cash drawer update failed', color='orange')
                    else:
                        ui.notify(f'Performa saved successfully! Invoice: {invoice_number}')

                await self.refresh_sales_table()
                await self.load_max_sale()
                self.sales_aggrid.classes(remove='dimmed')
                if hasattr(self, 'action_bar'):
                    self.action_bar.reset_state()
            except Exception as e:
                ui.notify(f'Error saving sale: {str(e)}')

    async def load_max_sale(self):
        """Automatically load the sale with the maximum ID when entering the interface."""
        async with loading_indicator.show_loading('load_max_sale', 'Loading latest sale...', overlay=True):
            try:
                max_id = self.get_max_sale_id()
                if max_id > 0:
                    # Fetch the sale data for the max ID
                    sale_data = []
                    connection.contogetrows(
                        f"SELECT s.id, s.sale_date, c.customer_name, s.total_amount, s.invoice_number, s.payment_status, s.currency_id, s.status FROM sales s INNER JOIN customers c ON c.id = s.customer_id WHERE s.id = {max_id}",
                        sale_data
                    )

                    if sale_data:
                        row_data = {
                            'id': sale_data[0][0],
                            'sale_date': sale_data[0][1],
                            'customer_name': sale_data[0][2],
                            'total_amount': sale_data[0][3],
                            'invoice_number': sale_data[0][4],
                            'payment_status': sale_data[0][5],
                            'currency_id': sale_data[0][6],
                            'status': str(sale_data[0][7]) if len(sale_data[0]) > 7 else 'Sale'
                        }

                        # Update customer name input with the customer from the max sale
                        self.customer_input.value = row_data['customer_name']

                        # Set the current sale ID
                        self.current_sale_id = max_id

                        # Fetch related sale items using the max sale_id
                        sale_items_data = []
                        connection.contogetrows(
                            f"SELECT p.barcode, p.product_name, si.quantity, ISNULL(si.discount_amount, 0), si.unit_price, si.total_price, ISNULL(si.vat_percentage,0), ISNULL(si.vat_amount,0) FROM sale_items si INNER JOIN products p ON p.id = si.product_id WHERE si.sales_id = {max_id}",
                            sale_items_data
                        )

                        # Clear and populate table with sale items
                        self.rows.clear()
                        
                        # Get exchange rate for the stored currency
                        sale_currency_id = row_data.get('currency_id', self.default_currency_id)
                        exchange_rate = float(self.currency_exchange_rates.get(sale_currency_id, 1.0))
                        
                        for item in sale_items_data:
                            self.rows.append({
                                'barcode': str(item[0]) if item[0] else '',
                                'product': str(item[1]) if item[1] else 'Unknown Product',
                                'quantity': int(item[2]) if item[2] else 0,
                                'discount': float(item[3]) * exchange_rate if item[3] else 0.0,
                                'price': float(item[4]) * exchange_rate if item[4] else 0.0,
                                'subtotal': float(item[5]) * exchange_rate if item[5] else 0.0,
                                'vat_percentage': float(item[6]) if item[6] else 0.0,
                                'vat_amount': float(item[7]) * exchange_rate if item[7] else 0.0,
                            })

                        # Update the table display
                        self.aggrid.options['rowData'] = self.rows
                        self.aggrid.update()

                        # --- Reset discount fields from the saved sale record ---
                        sale_discount_data = []
                        connection.contogetrows(
                            "SELECT ISNULL(discount_amount, 0) FROM sales WHERE id = ?",
                            sale_discount_data,
                            [max_id]
                        )
                        saved_discount_amount = float(sale_discount_data[0][0]) * exchange_rate if sale_discount_data else 0.0
                        self.discount_percent_input.value = 0
                        self.discount_amount_input.value = round(saved_discount_amount, 2)
                        if hasattr(self, 'discount_type_toggle'):
                            self.discount_type_toggle.value = 'Amount'
                            self.discount_percent_input.visible = False
                            self.discount_amount_input.visible = True

                        self.total_amount = sum(row['subtotal'] for row in self.rows)
                        self.update_totals()
                        self.invoicenumber = row_data["invoice_number"]
                        self.currency_select.value = row_data.get('currency_id', self.default_currency_id)

                        # Sync sale_type selector with the loaded record's status
                        sale_status = row_data.get('status', 'Sale')
                        if hasattr(self, 'sale_type'):
                            self.sale_type.value = 'Performa' if sale_status == 'Performa' else 'Standard'

                        ui.notify(f'✅ Automatically loaded sale ID: {max_id} - Invoice: {row_data["invoice_number"]}')
                    else:
                        ui.notify('No sales found in database')
                else:
                        ui.notify('No sales found in database')

            except Exception as e:
                ui.notify(f'Error loading max sale: {str(e)}')

    def create_ui(self):
        # Fetch session metadata for footer
        user = session_storage.get('user', {})
        company_info = connection.get_company_info()
        company_name = company_info.get('company_name', '') if company_info else ''

        """Create the main UI layout with premium design tokens."""
        # Add global styles
        uiAggridTheme.addingtheme()  # Apply AG Grid theme for proper row/header alignment
        ui.add_head_html(MDS.get_global_styles())
        ui.add_head_html(f'<script>{MDS.get_theme_switcher_js()}</script>')
        
        # Action buttons will be added inside the Invoice Editor panel (Right Side)

        with ui.element('div').classes('w-full mesh-gradient h-[calc(100vh-64px)] p-4 overflow-hidden'):
                    with ui.row().classes('w-full h-full gap-4 overflow-hidden'):
                        # --- MAIN CONTENT AREA ---
                        with ui.column().classes('flex-1 h-full gap-4 relative overflow-hidden'):
                            # --- TOP BAR: HEADER ---
                            # --- MIDDLE SECTION: DUAL PANEL ---
                            with ui.row().classes('w-full gap-3 overflow-hidden').style('height: 600px;'):
                        
                                # LEFT PANEL: Sales History (35%)
                                self.history_panel = ui.column().classes('w-[35%] h-full gap-4')
                                with self.history_panel:
                                    with ui.column().classes('w-full h-full glass p-4 rounded-3xl border border-white/10 gap-4'):
                                        # History Search Header (Modernized)
                                        with ui.row().classes('w-full items-center gap-3 glass p-3 rounded-2xl border border-white/10 hover:bg-white/5 transition-all'):
                                            ui.icon('history', size='1.25rem').classes('text-purple-400 ml-1')
                                            self.history_search = ui.input(placeholder='Search history...').props('borderless dense clearable dark')\
                                                .classes('flex-1 text-white font-bold')\
                                                .on_value_change(lambda e: self.filter_history_table(e.value))
                                            
                                            if self.can_hide_history:
                                                ui.button(icon='first_page', on_click=self.toggle_history).props('flat dense color=white').classes('ml-auto bg-purple-600/30 hover:bg-purple-600 rounded-lg transition-colors').tooltip('Hide History Panel')
                                            
                                            ui.icon('search', size='1.1rem').classes('text-gray-500 mr-2')
                                    
                                            self.history_search.on('focus', lambda: self.history_search.props('placeholder="Search Customer Ref"'))
                                            self.history_search.on('blur', lambda: self.history_search.props('placeholder="Search history..."') if not self.history_search.value else None)
                                
                                        # Sales History Grid (Paginated)
                                        self.sales_aggrid = ui.aggrid({
                                            'columnDefs': [
                                                {'headerName': 'ID', 'field': 'id', 'width': 60, 'sortable': True, 'filter': True},
                                                {'headerName': 'Date', 'field': 'sale_date', 'width': 100, 'sortable': True, 'filter': True},
                                                {'headerName': 'Ref', 'field': 'invoice_number', 'width': 110, 'sortable': True, 'filter': True},
                                                {'headerName': 'Customer', 'field': 'customer_name', 'width': 130, 'sortable': True, 'filter': True},
                                                {'headerName': 'Status', 'field': 'status', 'width': 80, 'sortable': True, 'filter': True},
                                                {'headerName': 'User', 'field': 'username', 'width': 80, 'sortable': True, 'filter': True},
                                                {'headerName': 'Total', 'field': 'total_amount', 'width': 90, 'sortable': True, 'filter': True, 'type': 'numericColumn'}
                                            ],
                                            'rowData': [],
                                            'rowSelection': 'single',
                                            'domLayout': 'normal',

                                            #'domLayout': 'autoHeight',
                                       # }).classes('w-full ag-theme-quartz-dark shadow-inner').style('background: transparent; border: none;')
                                        }).classes('w-full flex-1 ag-theme-quartz-dark shadow-inner').style('background: transparent; border: none; height: 490px;')
                                
                                        self.sales_aggrid.on('cellClicked', self.handle_sales_aggrid_click_wrapper)
                         
                       
                                # RIGHT PANEL: Invoice Editor (65%)
                                with ui.row().classes('flex-1 h-full gap-4 overflow-hidden relative'):
                                    if self.can_hide_history:
                                        self.show_history_btn = ui.button(icon='last_page', on_click=self.toggle_history)\
                                            .props('flat dense color=white').classes('absolute -left-2 top-1/2 z-50 bg-purple-600 rounded-r-xl shadow-lg border border-white/20 h-12 w-6')\
                                            .tooltip('View History')
                                        self.show_history_btn.visible = False
                                    # Column for Editor Content
                                    with ui.column().classes('flex-1 h-full gap-4 overflow-hidden'):
                                        # Merged Card: Type, Date, Currency, Customer, Contact, Payment + Barcode, Product, Qty, Price, Disc %
                                        with ui.row().classes('w-full glass p-6 rounded-2xl border border-white/10 gap-4 items-start'):
                                            with ui.column().classes('gap-3 flex-1'):
                                                # Row 1: Type, Date, Currency, Customer, Contact, Payment
                                                with ui.row().classes('w-full gap-3 items-center'):
                                                    with ui.column().classes('gap-1'):
                                                        ui.label('type').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest')
                                                        self.sale_type = ui.select(
                                                            ['Standard', 'Performa'],
                                                            value='Standard'
                                                        ).props('borderless dense').classes('bg-white/5 px-3 py-1 rounded-2xl border border-white/10 text-white text-[10px] font-bold w-[120px] h-[32px]')
                                                    
                                                    with ui.column().classes('gap-1'):
                                                        ui.label('Date').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest')
                                                        with ui.row().classes('items-center gap-2 bg-white/5 px-3 py-1 rounded-2xl h-[32px] w-[120px]'):
                                                            self.date_input = ui.input(value=datetime.now().strftime('%Y-%m-%d')).props('dark rounded type=date').classes('w-full glass-input text-xs font-bold')

                                                    with ui.column().classes('gap-1'):
                                                        ui.label('Currency').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest')
                                                        self.currency_select = ui.select(
                                                            {row[0]: f"{row[2]} {row[1]}" for row in self.currency_rows},
                                                            value=self.default_currency_id
                                                        ).props('borderless dense').classes('bg-white/5 px-3 py-1 rounded-2xl border border-white/10 text-white text-xs font-bold w-[130px] h-[32px]').on('change', self.on_currency_change)

                                                    with ui.column().classes('gap-1'):
                                                        ui.label('Customer').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest')
                                                        with ui.row().classes('items-center gap-3 bg-white/5 px-3 py-1 rounded-xl border border-white/10 hover:bg-white/10 transition-all cursor-pointer shadow-inner h-[32px] w-[160px]'):
                                                            self.customer_input = ui.input(placeholder='Select...').props('borderless dense dark').classes('flex-1 text-white font-black text-xs').on('click', self.open_customer_dialog)

                                                    with ui.column().classes('gap-1'):
                                                        ui.label('Contact').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest')
                                                        with ui.row().classes('items-center gap-3 bg-white/5 px-3 py-1 rounded-xl border border-white/10 h-[32px] w-[120px]'):
                                                            self.phone_input = ui.input(placeholder='Phone').props('borderless dense dark').classes('flex-1 text-white font-bold text-xs')

                                                    with ui.column().classes('gap-1'):
                                                        ui.label('Payment').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest')
                                                        with ui.row().classes('items-center gap-2 bg-white/5 px-3 py-1 rounded-xl border border-white/10 h-[32px]'):
                                                            self.payment_method = ui.radio(options=['Cash', 'On Account'], value='Cash').props('inline dark color=purple').classes('text-white text-[10px] font-black uppercase tracking-tighter')
                                                
                                                # Row 2: Barcode, Product, Qty, Price, Disc %, Add
                                                with ui.row().classes('w-full gap-3 items-end'):
                                                    with ui.column().classes('flex-[3] gap-1'):
                                                        ui.label('Barcode').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest')
                                                        with ui.row().classes('items-center gap-3 bg-white/5 px-3 py-1 rounded-xl border border-white/10 w-full'):
                                                            ui.icon('qr_code_scanner', size='1.25rem').classes('text-purple-400')
                                                            self.barcode_input = ui.input(placeholder='Scan or enter...').props('borderless dense dark').classes('flex-1 text-white font-bold').on('change', self.update_product_dropdown).on('keydown.enter', lambda: (self.quantity_input.run_method('focus'), ui.timer(0.1, lambda: self.quantity_input.run_method('select'), once=True)) if self.barcode_input.value else self.product_input.run_method('focus'))
                                    
                                                    with ui.column().classes('flex-[5] gap-1'):
                                                        ui.label('Product').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest')
                                                        with ui.row().classes('items-center gap-3 bg-white/5 px-3 py-1 rounded-xl border border-white/10 w-full'):
                                                            ui.icon('inventory_2', size='1.25rem').classes('text-purple-400')
                                                            self.product_input = ui.input(placeholder='Select Product...').props('borderless dense dark').classes('flex-1 text-white font-bold').on('click', self.open_product_dialog).on('keydown.enter', self.open_product_dialog)
                                    
                                                    with ui.column().classes('w-16 gap-1'):
                                                        ui.label('Qty').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest text-center')
                                                        with ui.row().classes('items-center gap-1 bg-white/5 px-2 py-2 rounded-2xl border border-white/10 w-full'):
                                                            self.quantity_input = ui.number(value=1).props('borderless dense dark').classes('w-full text-white font-black text-center').on(
                                                                'keydown.enter', 
                                                                lambda: (
                                                                    self.price_input.run_method('focus'),
                                                                    ui.timer(0.01, lambda: self.price_input.run_method('select'), once=True)
                                                                )
                                                            )
                                    
                                                    with ui.column().classes('w-24 gap-1'):
                                                        ui.label('Price').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest text-center')
                                                        with ui.row().classes('items-center gap-1 bg-white/5 px-2 py-2 rounded-2xl border border-white/10 w-full'):
                                                            self.price_input = ui.number(value=0.0).props('borderless dense dark').classes('w-full text-white font-black text-center').on(
                                                                'keydown.enter', 
                                                                lambda: (
                                                                    self.discount_input.run_method('focus'),
                                                                    ui.timer(0.01, lambda: self.discount_input.run_method('select'), once=True)
                                                                )
                                                            )
 
                                                    with ui.column().classes('w-16 gap-1'):
                                                        ui.label('Disc %').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest text-center')
                                                        with ui.row().classes('items-center gap-1 bg-white/5 px-2 py-2 rounded-2xl border border-white/10 w-full'):
                                                            self.discount_input = ui.number(value=0).props('borderless dense dark').classes('w-full text-white font-black text-center').on('keydown.enter', self.add_product)
                                    
                                                    ui.button(icon='add', on_click=self.add_product).props('elevated round size=md color=purple').classes('shadow-lg shadow-purple-500/30 hover:scale-110 transition-transform mb-1')

                       
                                        # Items Grid (Minimalist Initialization to prevent Quota issues)
                                        with ui.element('div').classes('w-full min-h-[400px] overflow-auto'):
                                            self.aggrid = ui.aggrid({
                                                'columnDefs': self.columns,
                                                'rowData': [], # Start empty to prevent initial crash
                                                'rowSelection': 'single',
                                                'domLayout': 'normal',
                                                'rowHeight': 30,
                                            }).classes('w-full h-full ag-theme-quartz-dark')
                                        
                                        # Use a separate update trigger to populate data
                                        def populate_aggrid():
                                            self.aggrid.options['rowData'] = self.rows
                                            self.aggrid.update()
                                        ui.timer(0.5, populate_aggrid, once=True)

                                        self.aggrid.on('cellClicked', self.handle_aggrid_click_wrapper)
                                        
                                    # Action Bar Panel (Right Side of Editor)
                                    with ui.column().classes('w-60px items-center shrink-0'):
                                        from modern_ui_components import ModernActionBar
                                        self.action_bar = ModernActionBar(
                                            on_new=self.clear_inputs,
                                            on_save=self.save_sale,
                                            on_undo=self.show_undo_confirmation,
                                            on_delete=self.delete_sale,
                                            on_print=self.print_sale_invoice,
                                            on_print_special=self.print_special_invoice,
                                            on_chatgpt=lambda: ui.run_javascript('window.open("https://chatgpt.com", "_blank");'),
                                            on_refresh=self.refresh_sales_table,
                                            on_view_transaction=self.view_sale_transactions,
                                            button_class='h-10',
                                            classes=' '                        
                                        ).style('position: static; width: 60px; border-radius: 12px; margin-top: 0;')

                            with ui.row().classes('w-full bg-black/80 backdrop-blur-xl border-t border-white/20 p-4 items-center justify-between shadow-2xl flex-nowrap gap-4'):
                                # 1. Operational Metrics
                                with ui.row().classes('items-center gap-3 shrink-0'):
                                    with ui.row().classes('items-center gap-2 bg-purple-500/10 px-3 py-1.5 rounded-xl border border-purple-500/20'):
                                        ui.icon('analytics', size='1rem').classes('text-purple-400')
                                        with ui.column().classes('gap-0'):
                                            ui.label('Commerce Pipeline').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest')
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

                                # Functional Hidden Inputs
                                with ui.element('div').classes('hidden'):
                                    self.tax_amount_input = ui.number(value=0, on_change=self.update_totals).props('dense borderless').classes('hidden')
                                    self.tax_percent_input = ui.number(value=0, on_change=self.update_totals).props('dense borderless').classes('hidden')

                    # Auto-load max sale and refresh table
                    ui.timer(0.1, self.load_max_sale, once=True)
                    ui.timer(0.2, self.refresh_sales_table, once=True)

    async def handle_sales_aggrid_click_wrapper(self, e):
        async with loading_indicator.show_loading('load_sale_items', 'Loading sale items...', overlay=True):
            try:
                selected_row = e.args.get('data')
                if selected_row and isinstance(selected_row, dict) and 'id' in selected_row:
                    sale_id = selected_row['id']
                    customer_name = selected_row['customer_name']
                    self.customer_input.value = customer_name
                    self.current_sale_id = sale_id
                    
                    sale_items_data = []
                    connection.contogetrows(
                        f"SELECT p.barcode, p.product_name, si.quantity, ISNULL(si.discount_amount, 0), si.unit_price, si.total_price, ISNULL(si.vat_percentage,0), ISNULL(si.vat_amount,0) FROM sale_items si INNER JOIN products p ON p.id = si.product_id WHERE si.sales_id = {sale_id}",
                        sale_items_data
                    )
                    
                    self.rows.clear()
                    
                    # Get exchange rate for the stored currency
                    sale_currency_id = selected_row.get('currency_id', self.default_currency_id)
                    exchange_rate = float(self.currency_exchange_rates.get(sale_currency_id, 1.0))
                    
                    for item in sale_items_data:
                        self.rows.append({
                            'barcode': str(item[0]) if item[0] else '',
                            'product': str(item[1]) if item[1] else 'Unknown',
                            'quantity': int(item[2]),
                            'discount': float(item[3]) * exchange_rate,
                            'price': float(item[4]) * exchange_rate,
                            'subtotal': float(item[5]) * exchange_rate,
                            'vat_percentage': float(item[6]) if item[6] else 0.0,
                            'vat_amount': float(item[7]) * exchange_rate if item[7] else 0.0,
                        })
                    
                    self.aggrid.options['rowData'] = self.rows
                    self.aggrid.update()
                    self.sales_aggrid.update()
                    if hasattr(self, 'action_bar'):
                        self.action_bar.enter_edit_mode()

                    # --- Reset discount fields from the saved sale record ---
                    sale_discount_data = []
                    connection.contogetrows(
                        "SELECT ISNULL(discount_amount, 0) FROM sales WHERE id = ?",
                        sale_discount_data,
                        [sale_id]
                    )
                    saved_discount_amount = float(sale_discount_data[0][0]) * exchange_rate if sale_discount_data else 0.0
                    # Reset discount inputs BEFORE update_totals so the correct total is displayed
                    self.discount_percent_input.value = 0
                    self.discount_amount_input.value = round(saved_discount_amount, 2)
                    if hasattr(self, 'discount_type_toggle'):
                        self.discount_type_toggle.value = 'Amount'
                        self.discount_percent_input.visible = False
                        self.discount_amount_input.visible = True

                    self.total_amount = sum(row['subtotal'] for row in self.rows)
                    self.update_totals()
                    self.invoicenumber = selected_row["invoice_number"]
                    self.currency_select.value = selected_row.get('currency_id', self.default_currency_id)

                    # Sync payment method radio with sale payment_status
                    # save_sale logic:
                    # - Cash => payment_status = 'completed'
                    # - On Account / Order => payment_status = 'pending'
                    payment_status = str(selected_row.get('payment_status', '')).lower()
                    self.payment_method.value = 'Cash' if payment_status == 'completed' else 'On Account'

                    # Sync sale_type selector with the loaded record's status
                    sale_status = str(selected_row.get('status', 'Sale'))
                    if hasattr(self, 'sale_type'):
                        self.sale_type.value = 'Performa' if sale_status == 'Performa' else 'Standard'
                    
                    ui.notify(f'Loaded {len(self.rows)} items from sale {sale_id}', color='positive')
            except Exception as ex:
                ui.notify(f'Error: {ex}')


    async def handle_aggrid_click_wrapper(self, e):
        try:
            selected_row = await self.aggrid.get_selected_row()
            if selected_row:
                self.open_edit_dialog(selected_row)
                self.update_totals()
                if hasattr(self, 'action_bar'):
                    self.action_bar.enter_edit_mode()
        except Exception as ex:
            ui.notify(f'Error: {ex}')

    def filter_history_table(self, query):
        """Filters the sales history grid by a search query with Python-side filtering for reliability."""
        # Use str(query) to handle potential objects if they slip through, though NiceGUI usually passes strings
        target_query = str(query if query is not None else "").lower()
        print(f"DEBUG: Filtering sales history with query: '{target_query}'")
        
        if hasattr(self, 'sales_aggrid') and hasattr(self, 'all_sales_data'):
            if not target_query:
                # If query is empty, show all data
                self.sales_aggrid.options['rowData'] = self.all_sales_data
            else:
                # Filter by ID, Customer Name, or Invoice Number
                filtered_data = [
                    row for row in self.all_sales_data 
                    if target_query in str(row['id']).lower() or 
                       target_query in str(row['customer_name']).lower() or 
                       target_query in str(row['invoice_number']).lower()
                ]
                self.sales_aggrid.options['rowData'] = filtered_data
            
            self.sales_aggrid.update()
            
            # Update placeholder based on search state
            if target_query:
                self.history_search.props('placeholder="Search Customer Ref"')
            else:
                self.history_search.props('placeholder="Sales History"')

    def print_special_invoice(self):
        """Open the Print Special report selector dialog."""
        from sales_reports import open_print_special_dialog
        customer_name = self.customer_input.value or 'Cash Client'
        customer_id = self.current_customer_id
        if customer_id is None:
            customer_id = connection.getid(
                'select id from customers where customer_name = ?', [customer_name])
        open_print_special_dialog(customer_id=customer_id, customer_name=customer_name)

    def view_sale_transactions(self):
        sale_id = getattr(self, 'current_sale_id', None)
        if not sale_id:
            return ui.notify('Select a sale to view its connected transaction', color='warning')
        import accounting_helpers
        accounting_helpers.show_transactions_dialog(reference_type="Sale", reference_id=sale_id)

    def load_default_customer(self):
        try:
            res = []
            connection.contogetrows("SELECT customer_name, phone FROM customers WHERE is_default = 1", res)
            if res:
                self.customer_input.value = res[0][0]
                self.phone_input.value = res[0][1]
            else:
                self.customer_input.value = 'Cash Client'
                self.phone_input.value = ''
        except Exception as e:
            print(f"Error loading default customer: {e}")
            self.customer_input.value = 'Cash Client'
            self.phone_input.value = ''

@ui.page('/sales')
def sales_page_route():
    SalesUI()
