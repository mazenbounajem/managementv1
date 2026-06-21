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
class SalesReturnsUI:
    
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
                "SELECT invoice_number FROM sales_returns WHERE invoice_number IS NOT NULL", []
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
            
            # For sales returns, we ALWAYS add back quantity to stock.
            # Do NOT block by current stock levels.
            product_id = connection.getid('select id from products where product_name = ?', [product_name])
            
            # Fetch VAT info
            product_vat_data = []
            connection.contogetrows(f"SELECT is_vat_subjected, vat_percentage FROM products WHERE id = {product_id}", product_vat_data)
            is_vat_subjected = product_vat_data[0][0] if product_vat_data else False
            vat_percentage = float(product_vat_data[0][1] or 0) if product_vat_data else 0.0
            
            # VAT is 11% if subjected, otherwise 0
            vat_percentage = 11.0 if is_vat_subjected else 0.0
            
            total_ttc = (quantity * price) * (1 - discount / 100)
            vat_amount = total_ttc * (vat_percentage / 100)
            subtotal = total_ttc # Price includes VAT
            
            # If product already exists in cart, merge by incrementing quantity
            existing = None
            for row in self.rows:
                if row['barcode'] == barcode:
                    existing = row
                    break

            if existing:
                existing['quantity'] += quantity
                existing['discount'] = (existing['discount'] + discount) / 2
                new_total_ttc = (existing['quantity'] * price) * (1 - existing['discount'] / 100)
                existing['vat_amount'] = new_total_ttc * (vat_percentage / 100)
                existing['subtotal'] = new_total_ttc
                self.total_amount = sum(r['subtotal'] for r in self.rows)
            else:
                self.rows.append({
                    'barcode': barcode,
                    'product': product_name,
                    'quantity': quantity,
                    'discount': discount,
                    'price': price,
                    'vat_percentage': vat_percentage if is_vat_subjected else 0,
                    'vat_amount': vat_amount,
                    'subtotal': subtotal,
                })
                self.total_amount += subtotal
            self.update_totals()
            
            # Stock update moved to save/update/delete (persisted invoice) only.
            # Cart add must NOT mutate inventory stock.

            # IMPORTANT: ensure AG Grid is bound to the updated rowData reference
            try:
                self.aggrid.options['rowData'] = self.rows
            except Exception:
                pass
            self.clear_inputs_inputs()
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
    
    def load_default_customer(self):
        """Set customer_input/phone_input from the default customer (customers.is_default=1)."""
        try:
            res = []
            connection.contogetrows(
                "SELECT customer_name, phone FROM customers WHERE is_default = 1",
                res
            )
            if res:
                self.customer_input.value = res[0][0] or 'Cash Client'
                self.phone_input.value = res[0][1] or ''
            else:
                self.customer_input.value = 'Cash Client'
                self.phone_input.value = ''
        except Exception:
            self.customer_input.value = 'Cash Client'
            self.phone_input.value = ''

    def clear_inputs(self):
        if hasattr(self, 'action_bar'):
            self.action_bar.enter_new_mode()
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
        if hasattr(self, 'll_total_input'):
            self.ll_total_input.value = 0
        self.update_totals()
        
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
                    f"SELECT barcode, product_name, price FROM products WHERE barcode = '{barcode}'", 
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
            connection.contogetrows("SELECT barcode, product_name, stock_quantity, price, cost_price FROM products", data)
            
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
                try:
                    args = e.args if hasattr(e, 'args') else e
                    row_data = None
                    if isinstance(args, (list, tuple)):
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

            ui.timer(0.05, select_and_scroll, once=True)

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
                search_input = ui.input(placeholder='Search by name or phone...').props('borderless dense autocomplete="off"').classes('flex-1 text-white text-sm').on_value_change(lambda e: self.filter_customer_rows(e.value))\
                    .on('keydown.down', lambda: self._customer_search_arrow_down(dialog))\
                    .on('keydown.enter', lambda: self._customer_search_enter(dialog))
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

            ui.timer(0.05, select_and_scroll, once=True)

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

    def show_profit_dialog(self):
        """Calculate and display profit in a dialog dynamically based on current cart items."""
        try:
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
            discount_amount = float(self.discount_amount_input.value or 0)
            
            final_revenue = total_revenue_local - discount_amount

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
                            ui.label('Net Profit').classes('text-[9px] text-gray-400 font-bold uppercase tracking-tighter')
                            ui.label(f'{selected_currency_symbol}{profit_value:,.2f}').classes('text-2xl font-black text-green-400')
                        
                        with ui.column().classes('gap-0 items-end'):
                            ui.label('Margin').classes('text-[9px] text-gray-400 font-bold uppercase tracking-tighter')
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
        """Generate and display sales invoice PDF directly"""
        try:
            if not self.rows:
                ui.notify('No items to print!')
                return

            # Generate invoice number if not exists
            invoice_number = self.invoicenumber or self.generate_invoice_number()

            # Update invoice number if it was generated
            if not self.invoicenumber:
                self.invoicenumber = invoice_number

            # Calculate totals
            subtotal = sum(row['subtotal'] for row in self.rows)
            discount_amount = float(self.discount_amount_input.value or 0)
            final_total = subtotal - discount_amount

            # Get company info
            company_info = connection.get_company_info()
            company_name = company_info.get('company_name') if company_info else 'Company Name'

            # Get currency symbol for the current sale
            selected_currency_id = self.currency_select.value
            currency_symbol = '$'
            for row in self.currency_rows:
                if row[0] == selected_currency_id:
                    currency_symbol = row[2]
                    break

            # Prepare invoice data for PDF
            invoice_data = []
            for item in self.rows:
                invoice_data.append({
                    'Barcode': str(item['barcode']),
                    'Product': str(item['product']),
                    'Quantity': str(item['quantity']),
                    'Price': f"{currency_symbol}{item['price']:.2f}",
                    'Discount': f"{item['discount']:.1f}%",
                    'Subtotal': f"{currency_symbol}{item['subtotal']:.2f}"
                })

            # Directly generate and display PDF
            self.print_invoice_pdf(invoice_number, invoice_data, subtotal, discount_percent, discount_amount, final_total, company_name, currency_symbol)

        except Exception as e:
            ui.notify(f'Error generating invoice: {str(e)}')
            print(f'Print invoice error: {str(e)}')

    def filter_customer_rows(self, search_text):
        if not search_text:
            filtered_rows = self.customer_rows
        else:
            filtered_rows = [row for row in self.customer_rows if any(search_text.lower() in str(value).lower() for value in row.values())]

        self.customer_grid.rows = filtered_rows

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
            dialog.close()
            ui.notify(f"Selected: {row['customer_name']}")
            ui.timer(0.05, lambda: self.barcode_input.run_method('focus'), once=True)
        except Exception as ex:
            ui.notify(f"Selection error: {ex}")
            dialog.close()

    def handle_product_grid_click(self, e, dialog):
        try:
            row = None

            if isinstance(e, dict):
                if 'args' in e and isinstance(e.get('args'), dict):
                    row = e['args'].get('data')
                if row is None and all(k in e for k in ('barcode', 'product_name')):
                    row = e

            if row is None:
                args_obj = getattr(e, 'args', None)
                if isinstance(args_obj, dict):
                    row = args_obj.get('data') or args_obj.get('item') or args_obj.get('row')

            if row is None:
                data_obj = getattr(e, 'data', None)
                if isinstance(data_obj, dict):
                    row = data_obj

            if not isinstance(row, dict):
                ui.notify(f"Selection error: unexpected event payload ({type(e)})", color='negative')
                return

            self.product_input.value = row.get('product_name', '')
            self.barcode_input.value = row.get('barcode', '')
            self.price_input.value = row.get('price', 0)

            selected_currency_id = self.currency_select.value
            exchange_rate = float(self.currency_exchange_rates.get(selected_currency_id, 1.0))
            
            selected_currency_symbol = '$'
            for c_row in self.currency_rows:
                if c_row[0] == selected_currency_id:
                    selected_currency_symbol = c_row[2]
                    break

            if selected_currency_symbol != '$':
                self.price_input.value = float(self.price_input.value) * exchange_rate
            
            dialog.close()
            ui.notify(f"Product selected: {row.get('product_name', 'Unknown')}")

            self.quantity_input.run_method('focus')
            ui.timer(0.01, lambda: self.quantity_input.run_method('select'), once=True)

            def auto_add():
                try:
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
        """Generate and display PDF invoice"""
        try:
            import base64
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from io import BytesIO

            # Create PDF buffer with reduced margins for better table visibility
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter,
                                  leftMargin=20, rightMargin=20,
                                  topMargin=30, bottomMargin=30)
            elements = []

            # Styles
            styles = getSampleStyleSheet()
            title_style = styles['Heading1']

            # Title
            title = Paragraph(f"{company_name} - Sales Invoice", title_style)
            elements.append(title)
            elements.append(Spacer(1, 12))

            # Invoice details
            customer_name = self.customer_input.value or 'Cash Client'
            invoice_info = Paragraph(f"Invoice #: {invoice_number}<br/>Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>Customer: {customer_name}", styles['Normal'])
            elements.append(invoice_info)
            elements.append(Spacer(1, 12))

            # Prepare table data
            table_data = [['Barcode', 'Product', 'Quantity', 'Price', 'Discount', 'Subtotal']]
            for item in invoice_data:
                table_data.append([
                    item['Barcode'],
                    item['Product'],
                    item['Quantity'],
                    item['Price'],
                    item['Discount'],
                    item['Subtotal']
                ])

            # Create table with adjusted width for margins
            page_width, page_height = letter
            available_width = page_width - 40  # Subtract left and right margins (20 + 20)
            col_widths = [available_width * 0.15, available_width * 0.25, available_width * 0.15, available_width * 0.15, available_width * 0.15, available_width * 0.15]
            table = Table(table_data, colWidths=col_widths)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            elements.append(table)
            elements.append(Spacer(1, 12))

            # Totals section
            totals_data = []
            if discount_percent > 0 or discount_amount > 0:
                totals_data.append(['Subtotal:', f"{currency_symbol}{subtotal:.2f}"])
                if discount_percent > 0:
                    totals_data.append([f'Discount ({discount_percent}%):', f"-{currency_symbol}{subtotal * discount_percent / 100:.2f}"])
                if discount_amount > 0:
                    totals_data.append(['Discount Amount:', f"-{currency_symbol}{discount_amount:.2f}"])

            totals_data.append(['Grand Total:', f"{currency_symbol}{final_total:.2f}"])

            available_width = page_width - 40  # Subtract left and right margins (20 + 20)
            totals_table = Table(totals_data, colWidths=[available_width * 0.7, available_width * 0.3])
            totals_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (-1, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (-1, -1), (-1, -1), 14),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            elements.append(totals_table)

            # Build PDF
            doc.build(elements)

            # Get PDF bytes
            pdf_bytes = buffer.getvalue()
            buffer.close()

            # Convert to base64 for inline display
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
            pdf_data_url = f"data:application/pdf;base64,{pdf_base64}"

            # Create full-screen modal dialog to display PDF
            with ui.dialog() as pdf_dialog:
                with ui.card().classes('w-screen h-screen max-w-none max-h-none m-0 rounded-none'):
                    # Header with close button
                    with ui.row().classes('w-full justify-between items-center p-4 bg-gray-100 border-b'):
                        ui.label('Sales Invoice PDF').classes('text-xl font-bold')
                        ui.button('✕ Close', on_click=pdf_dialog.close).classes('bg-red-500 hover:bg-red-700 text-white px-4 py-2 rounded')

                    # PDF display area
                    ui.html(f'''
                        <iframe src="{pdf_data_url}"
                                width="100%"
                                height="100%"
                                style="border: none; min-height: calc(100vh - 80px);">
                            <p>Your browser does not support iframes.
                            <a href="{pdf_data_url}" target="_blank">Click here to view the PDF</a></p>
                        </iframe>
                    ''').classes('w-full flex-1')

            pdf_dialog.open()
            ui.notify('Sales invoice PDF generated and displayed', color='green')

        except Exception as e:
            ui.notify(f'Error generating PDF: {str(e)}')
            print(f'PDF generation error: {str(e)}')
   
    
                            
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
            
            # For sales returns, stock adjustments happen only on save/update/delete (persisted invoice).
            product_id = connection.getid('select id from products where product_name = ?', [original_row['product']])
            
            self.rows[row_index]['quantity'] = int(new_quantity)
            self.rows[row_index]['discount'] = float(new_discount)
            self.rows[row_index]['price'] = float(new_price)
            
            # Fetch VAT status for the product
            product_id = connection.getid('select id from products where product_name = ?', [self.rows[row_index]['product']])
            vat_chk = []
            connection.contogetrows(f"SELECT is_vat_subjected FROM products WHERE id = {product_id}", vat_chk)
            is_vat_subjected = vat_chk[0][0] if vat_chk else False
            
            vat_pct = 11.0 if is_vat_subjected else 0.0
            total_ttc = (int(new_quantity) * float(new_price)) * (1 - float(new_discount) / 100)
            vat_amount = total_ttc * (vat_pct / 100)
            
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

            self.subtotal_label.text = f"Total HT: {currency_symbol}{subtotal - total_vat:.2f}"
            self.vat_label.text = f"Total VAT: {currency_symbol}{total_vat:.2f}"
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
            target_val = float(e.value or 0)
            discount_amt = max(0.0, subtotal - target_val)
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
            discount_amt = max(0.0, subtotal - target_total)
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

    def get_max_sale_id(self):
        try:
            max_id_result = []
            connection.contogetrows("SELECT MAX(id) FROM sales_returns", max_id_result)
            return max_id_result[0][0] if max_id_result and max_id_result[0][0] else 0
        except Exception:
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
                # IMPORTANT for stock:
                # Before deleting the return, restore stock by the quantities in sales_return_items.
                prev_items = []
                connection.contogetrows(
                    "SELECT product_id, quantity FROM sales_return_items WHERE sales_return_id = ?",
                    prev_items,
                    [sale_id]
                )

                for item in prev_items:
                    product_id = int(item[0])
                    qty = int(item[1] or 0)
                    # Sales return increases stock when saved.
                    # When deleting the return, we must reverse it => decrease stock by the returned qty.
                    connection.insertingtodatabase(
                        "UPDATE products SET stock_quantity = stock_quantity - ? WHERE id = ?",
                        (qty, product_id)
                    )

                # Get the sale total and customer ID before deletion (kept for accounting cleanup)
                sale_data = []
                connection.contogetrows(
                    f"SELECT customer_id, total_amount FROM sales_returns WHERE id = {sale_id}",
                    sale_data
                )

                if sale_data:
                    # Delete sale items and sale
                    connection.deleterow("DELETE FROM sales_return_items WHERE sales_return_id = ?", [sale_id])
                    connection.deleterow("DELETE FROM sales_payment WHERE sales_return_id = ?", [sale_id])
                    
                    # Clean up accounting entries (Sales Return + Cash receipt JV)
                    jvs = []
                    connection.contogetrows(
                        "SELECT jv_id FROM accounting_transactions WHERE reference_type IN ('Sale Return', 'Sale Return Receipt') AND reference_id = ?",
                        jvs,
                        [str(sale_id)]
                    )
                    for jv in jvs:
                        connection.deleterow("DELETE FROM accounting_transaction_lines WHERE jv_id = ?", (jv[0],))
                        connection.deleterow("DELETE FROM accounting_transactions WHERE jv_id = ?", (jv[0],))
                        
                    connection.deleterow("DELETE FROM sales_returns WHERE id = ?", [sale_id])

                    # IMPORTANT:
                    # Deleting a sales return must NOT affect customer's balance per requirements.

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

        self.rows.clear()
        self.aggrid.options['rowData'] = self.rows
        self.aggrid.update()

        self.total_amount = 0
        self.update_totals()

        self.clear_inputs()
        dialog.close()
        self.sales_aggrid.classes(remove='dimmed')
        ui.notify('Undo completed successfully')
        if hasattr(self, 'action_bar'):
            self.action_bar.reset_state()

    def toggle_history(self):
        """Toggle the visibility of the sales return history panel"""
        if hasattr(self, 'history_panel'):
            self.history_panel.visible = not self.history_panel.visible
            if hasattr(self, 'show_history_btn'):
                self.show_history_btn.visible = not self.history_panel.visible
            ui.notify('History ' + ('hidden' if not self.history_panel.visible else 'shown'), color='info', duration=1)

    async def refresh_sales_table(self):
        """Refresh sales table with loading indicator"""
        async with loading_indicator.show_loading('refresh_sales', 'Refreshing sales data...', overlay=True):
            try:
                raw_sales_data = []
                connection.contogetrows(
"SELECT s.id, s.sale_date, c.customer_name, s.total_amount, s.invoice_number, cur.currency_name, s.payment_status, s.currency_id, s.status, u.username "
                     "FROM sales_returns s "
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
                
                # If it's an order, status is 'Order' and payment is always 'pending'
                # If it's a sale, status is 'Sale' and payment depends on method
                status = 'Order' if is_order else 'Sales Return'
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
                    # =========================
                    # UPDATE: reverse previous stock, then apply new stock
                    # =========================

                    # 1) Reverse previous saved quantities (stock was increased on create/save)
                    prev_items = []
                    connection.contogetrows(
                        "SELECT product_id, quantity FROM sales_return_items WHERE sales_return_id = ?",
                        prev_items,
                        (self.current_sale_id,)
                    )
                    for item in prev_items:
                        prev_product_id = item[0]
                        prev_qty = item[1] or 0
                        # Reverse: previously increased, so subtract now
                        connection.insertingtodatabase(
                            "UPDATE products SET stock_quantity = stock_quantity - ? WHERE id = ?",
                            (int(prev_qty), int(prev_product_id))
                        )

                    # Retrieve previous payment status and total amount for reversal logic
                    previous_sale_data = []
                    connection.contogetrows(
                        "SELECT payment_status, total_amount FROM sales_returns WHERE id = ?",
                        previous_sale_data,
                        (self.current_sale_id,)
                    )
                    previous_payment_status = previous_sale_data[0][0] if previous_sale_data else None
                    previous_total_amount = float(previous_sale_data[0][1]) if previous_sale_data else 0.0

                    # Reverse previous payment effects if payment method changed
                    if previous_payment_status != payment_status:
                        if previous_payment_status == 'completed':  # Previously Cash
                            user = session_storage.get('user')
                            user_id = user.get('user_id') if user else None
                            notes = f"Sale update reversal {self.current_sale_id}"
                            # Reversing a previous Cash transaction:
                            # previous cash-out must be undone => cash goes back (In)
                            success = connection.update_cash_drawer_balance(previous_total_amount, 'In', user_id, notes)
                            if success:
                                ui.notify(f'Reversed previous cash drawer operation of +${previous_total_amount:.2f}')
                            else:
                                ui.notify('Warning: Failed to reverse previous cash drawer operation', color='orange')
                        elif previous_payment_status == 'pending':  # Previously On Account
                            if customer_id:
                                connection.insertingtodatabase(
                                    "UPDATE customers SET balance = balance - ? WHERE id = ?",
                                    (previous_total_amount, customer_id)
                                )
                                ui.notify(f'Reversed previous customer balance of -${previous_total_amount:.2f}')

                    # Fetch VAT values
                    normalized_total_vat = sum(row.get('vat_amount', 0) for row in self.rows) / exchange_rate
                    normalized_subtotal = (self.total_amount / exchange_rate) - normalized_total_vat
                    
                    sale_sql = """
                        UPDATE sales_returns
                        SET sale_date = ?, customer_id = ?, subtotal = ?, discount_amount = ?,
                            total_amount = ?, created_at = ?, payment_status = ?, currency_id = ?,
                            user_id = ?, status = ?, total_vat = ?
                        WHERE id = ?
                    """
                    sale_values = (sale_date, customer_id, normalized_subtotal, normalized_discount, normalized_total, created_at, payment_status, selected_currency_id, user_id, status, normalized_total_vat, self.current_sale_id)
                    connection.insertingtodatabase(sale_sql, sale_values)

                    delete_items_sql = "DELETE FROM sales_return_items WHERE sales_return_id = ?"
                    connection.insertingtodatabase(delete_items_sql, [self.current_sale_id])

                    # 2) Insert new items + apply stock increases
                    # IMPORTANT: stock reversal and stock application must use the SAME product_id
                    # that we store in sales_return_items. We derive product_id only from barcode.
                    for row in self.rows:
                        barcode = row['barcode']
                        final_product_id = connection.getid(
                            'select id from products where barcode = ?',
                            [barcode]
                        )
                        if not final_product_id:
                            raise ValueError(f"Product not found for barcode: {barcode}")

                        sale_item_sql = """
                            INSERT INTO sales_return_items (sales_return_id, barcode, product_id, quantity, unit_price, total_price, discount_amount, vat_amount, vat_percentage)
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

                        # Sales return increases stock by returned quantity (products table)
                        connection.insertingtodatabase(
                            "UPDATE products SET stock_quantity = stock_quantity + ? WHERE id = ?",
                            (int(row['quantity']), int(final_product_id))
                        )

                        # Also log into stock operations so it appears in stock transaction/print reports
                        try:
                            op_date = sale_date
                            u_id = user_id if user_id else (session_storage.get('user') or {}).get('user_id') or 1
                            # Create a stock operation header per saved sale (only once would be better, but this is safe)
                            sql_header = """
                                INSERT INTO stock_operations
                                    (operation_date, user_id, operation_type, total_items, reference_number)
                                VALUES (?, ?, ?, ?, ?)
                            """
                            # total_items is informational; keep per-item quantity
                            connection.insertingtodatabase(
                                sql_header,
                                (op_date, int(u_id), 'return', int(row['quantity']), str(self.invoicenumber or ''))
                            )
                            op_id = connection.getid("SELECT MAX(id) FROM stock_operations", [])

                            sql_item = """
                                INSERT INTO stock_operation_items
                                    (operation_id, product_id, barcode, product_name, previous_quantity, adjusted_quantity, operation_type, reason)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """

                            curr_stock_res = []
                            connection.contogetrows(
                                "SELECT stock_quantity FROM products WHERE id = ?",
                                curr_stock_res,
                                (int(final_product_id),)
                            )
                            prev_qty = float(curr_stock_res[0][0]) if curr_stock_res else 0.0

                            # For return operations, stockoperationui treats negative as abs, so keep positive here.
                            connection.insertingtodatabase(
                                sql_item,
                                (
                                    int(op_id),
                                    int(final_product_id),
                                    row['barcode'],
                                    row['product'],
                                    prev_qty,
                                    int(row['quantity']),
                                    'return',
                                    f"Sale Return #{self.invoicenumber}"
                                )
                            )
                        except Exception as op_ex:
                            ui.notify(f"Warning: stock operation log failed: {op_ex}", color='orange')

                    # Clean up old payment record first
                    delete_payment_sql = "DELETE FROM sales_payment WHERE sales_return_id = ?"
                    connection.insertingtodatabase(delete_payment_sql, [self.current_sale_id])

                    # Insert into sales_payment table based on payment method
                    if payment_method == 'Cash':
                        debit = final_total
                        credit = final_total
                    else:  # On Account
                        debit = 0
                        credit = final_total

                    sales_payment_sql = """
                        INSERT INTO sales_payment (sales_return_id, customer_id, invoice_number, total_amount, sale_date, payment_status, debit, credit, notes)
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
                    revenue_account = business_track_settings.get_sales_return_account(has_vat)

                    # REVERSED for Return: Debit Sales/VAT, Credit Customer
                    jv = [
                        {'account': customer_account, 'debit': 0, 'credit': normalized_total},
                        {'account': revenue_account,  'debit': normalized_subtotal, 'credit': 0},
                        {'account': vat_account,      'debit': normalized_total_vat, 'credit': 0},
                    ]

                    accounting_helpers.save_accounting_transaction(
                        'Sale Return', self.current_sale_id, jv, description=f"Sale Return {self.invoicenumber}"
                    )
                    
                    if payment_method == 'Cash':
                        # REVERSED for Return: Debit Customer, Credit Cash
                        # Reuse the existing cash/GL auxiliary row for base '5300' (suffix "1" style, no increment).
                        aux_id, _full_num = accounting_helpers._get_auxiliary_id_and_full_number_for_ledger_base('5300')
                        caisse_aux_id = aux_id

                        payment_jv = [
                            {'account': '5300', 'auxiliary_id': caisse_aux_id, 'debit': 0, 'credit': normalized_total},
                            {'account': customer_account, 'debit': normalized_total, 'credit': 0},
                        ]
                        accounting_helpers.save_accounting_transaction(
                            'Sale Return Receipt', self.current_sale_id, payment_jv,
                            description=f"Cash Payment (Caisse) for Sale Return {self.invoicenumber}"
                        )
                    else:
                        # Clean up any potential 'Sale Return Receipt'
                        accounting_helpers.save_accounting_transaction('Sale Return Receipt', self.current_sale_id, [])

                    ui.notify(f'Sale updated successfully! ID: {self.current_sale_id}')

                    # Apply new payment effects
                    if customer_id and payment_method == 'On Account':
                        # Get current customer balance
                        current_balance_result = []
                        connection.contogetrows("SELECT balance FROM customers WHERE id = ?", current_balance_result, (customer_id,))
                        current_balance = float(current_balance_result[0][0]) if current_balance_result else 0.0

                        # Add sale amount (normalized to USD) to current balance
                        new_balance = current_balance + normalized_total
                        connection.insertingtodatabase(
                            "UPDATE customers SET balance = ? WHERE id = ?",
                            (new_balance, customer_id)
                        )
                        ui.notify(f'Customer balance updated successfully! New balance: ${new_balance:.2f}')
                    elif payment_method == 'Cash':
                        notes = f"Sale update {self.current_sale_id}"
                        # Use normalized total for cash drawer balance (base currency)
                        # Cash sale return => customer gives money back to business:
                        # cash drawer must DECREASE for "Sale Return" (same convention as your create branch uses 'Out')
                        success = connection.update_cash_drawer_balance(normalized_total, 'Out', session_storage.get('user')['user_id'], notes)
                        if success:
                            ui.notify(f'Cash payment recorded! Cash drawer updated by -${normalized_total:.2f}')
                        else:
                            ui.notify('Warning: Cash payment saved but cash drawer update failed', color='orange')

                else:
                    invoice_number = self.generate_invoice_number()

                    # Fetch VAT values
                    normalized_total_vat = sum(row.get('vat_amount', 0) for row in self.rows) / exchange_rate
                    normalized_subtotal = (self.total_amount / exchange_rate) - normalized_total_vat

                    sale_sql = """
                        INSERT INTO sales_returns (sale_date, customer_id, subtotal, discount_amount, total_amount, invoice_number, created_at, payment_status, currency_id, user_id, status, total_vat)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    sale_values = (sale_date, customer_id, normalized_subtotal, normalized_discount, normalized_total, invoice_number, created_at, payment_status, selected_currency_id, user_id, status, normalized_total_vat)
                    connection.insertingtodatabase(sale_sql, sale_values)

                    last_sale_id = connection.getid("SELECT MAX(id) FROM sales_returns", [])

                    for row in self.rows:
                        # IMPORTANT: store/apply stock using product_id derived only from barcode
                        barcode = row['barcode']
                        final_product_id = connection.getid(
                            'select id from products where barcode = ?',
                            [barcode]
                        )
                        if not final_product_id:
                            raise ValueError(f"Product not found for barcode: {barcode}")

                        sale_item_sql = """
                            INSERT INTO sales_return_items (sales_return_id, barcode, product_id, quantity, unit_price, total_price, discount_amount, vat_amount, vat_percentage)
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

                        # Also log stock operation for returns
                        try:
                            u_id = user_id if user_id else (session_storage.get('user') or {}).get('user_id') or 1
                            connection.insertingtodatabase(
                                """
                                INSERT INTO stock_operations
                                    (operation_date, user_id, operation_type, total_items, reference_number)
                                VALUES (?, ?, ?, ?, ?)
                                """,
                                (sale_date, int(u_id), 'return', int(row['quantity']), str(invoice_number or ''))
                            )
                            op_id = connection.getid("SELECT MAX(id) FROM stock_operations", [])

                            sql_item = """
                                INSERT INTO stock_operation_items
                                    (operation_id, product_id, barcode, product_name, previous_quantity, adjusted_quantity, operation_type, reason)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """
                            curr_stock_res = []
                            connection.contogetrows(
                                "SELECT stock_quantity FROM products WHERE id = ?",
                                curr_stock_res,
                                (int(final_product_id),)
                            )
                            prev_qty = float(curr_stock_res[0][0]) if curr_stock_res else 0.0

                            connection.insertingtodatabase(
                                sql_item,
                                (
                                    int(op_id),
                                    int(final_product_id),
                                    row['barcode'],
                                    row['product'],
                                    prev_qty,
                                    int(row['quantity']),
                                    'return',
                                    f"Sale Return #{invoice_number}"
                                )
                            )
                        except Exception as op_ex:
                            ui.notify(f"Warning: stock operation log failed: {op_ex}", color='orange')

                    # Sales return increases stock by returned quantity
                    connection.insertingtodatabase(
                        "UPDATE products SET stock_quantity = stock_quantity + ? WHERE id = ?",
                        (int(row['quantity']), int(final_product_id))
                    )

                    # Insert into sales_payment table based on payment method
                    if payment_method == 'Cash':
                        debit = final_total
                        credit = final_total
                    else:  # On Account
                        debit = 0
                        credit = final_total

                    sales_payment_sql = """
                        INSERT INTO sales_payment (sales_return_id, customer_id, invoice_number, total_amount, sale_date, payment_status, debit, credit, notes)
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
                    revenue_account = business_track_settings.get_sales_return_account(has_vat)

                    # REVERSED for Return: Debit Sales/VAT, Credit Customer
                    jv = [
                        {'account': customer_account, 'debit': 0, 'credit': normalized_total},
                        {'account': revenue_account,  'debit': normalized_subtotal, 'credit': 0},
                        {'account': vat_account,      'debit': normalized_total_vat, 'credit': 0},
                    ]

                    accounting_helpers.save_accounting_transaction(
                        'Sale Return', last_sale_id, jv, description=f"Sale Return {invoice_number}"
                    )
                    
                    if payment_method == 'Cash':
                        # REVERSED for Return: Debit Customer, Credit Cash
                        caisse_rows = []
                        # Reuse the existing cash/GL auxiliary row for base '5300' (suffix "1" style, no increment).
                        aux_id, _full_num = accounting_helpers._get_auxiliary_id_and_full_number_for_ledger_base('5300')
                        caisse_aux_id = aux_id

                        payment_jv = [
                            {'account': '5300', 'auxiliary_id': caisse_aux_id, 'debit': 0, 'credit': normalized_total},
                            {'account': customer_account, 'debit': normalized_total, 'credit': 0},
                        ]
                        accounting_helpers.save_accounting_transaction(
                            'Sale Return Receipt', last_sale_id, payment_jv,
                            description=f"Cash Payment (Caisse) for Sale Return {invoice_number}"
                        )

                    ui.notify(f'{"Order" if is_order else "Sale"} saved successfully! Invoice: {invoice_number}')

                    # Update customer balance only if payment method is "On Account"
                    if customer_id and payment_method == 'On Account':
                        connection.update_customerbalance(
                            "UPDATE customers SET balance = balance - ? WHERE id = ?",
                            (normalized_total, customer_id)
                        )
                        ui.notify(f'Customer balance updated successfully! Total: -${normalized_total:.2f}')
                    elif payment_method == 'Cash':
                        # Update cash drawer balance (USD) for cash payment
                        notes = f"New sale return {last_sale_id}"
                        success = connection.update_cash_drawer_balance(normalized_total, 'Out', session_storage.get('user')['user_id'], notes)
                        if success:
                            ui.notify(f'Cash payment recorded! Cash drawer updated by -${normalized_total:.2f}')
                        else:
                            ui.notify('Warning: Cash payment saved but cash drawer update failed', color='orange')

                self.action_bar.reset_state()
                await self.refresh_sales_table()
                await self.load_max_sale()
                self.sales_aggrid.classes(remove='dimmed')
            except Exception as e:
                ui.notify(f'Error saving sale: {str(e)}')

    async def load_max_sale(self):
        """Automatically load the sale with the maximum ID when entering the interface."""
        # If user already selected a sale for editing, do not overwrite it.
        if getattr(self, 'current_sale_id', None):
            return
        async with loading_indicator.show_loading('load_max_sale', 'Loading latest sale...', overlay=True):
            try:
                max_id = self.get_max_sale_id()
                if max_id > 0:
                    # Fetch the sale data for the max ID
                    sale_data = []
                    connection.contogetrows(
                        f"SELECT s.id, s.sale_date, c.customer_name, s.total_amount, s.invoice_number, s.payment_status, s.currency_id, ISNULL(s.discount_amount, 0) FROM sales_returns s INNER JOIN customers c ON c.id = s.customer_id WHERE s.id = {max_id}",
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
                            'discount_amount': sale_data[0][7]
                        }

                        # Update customer name input with the customer from the max sale
                        self.customer_input.value = row_data['customer_name']

                        # Set the current sale ID
                        self.current_sale_id = max_id

                        # Fetch related sale items using the max sale_id
                        sale_items_data = []
                        connection.contogetrows(
                            f"SELECT p.barcode, p.product_name, si.quantity, ISNULL(si.discount_amount, 0), si.unit_price, si.total_price, ISNULL(si.vat_percentage,0), ISNULL(si.vat_amount,0) FROM sales_return_items si INNER JOIN products p ON p.id = si.product_id WHERE si.sales_return_id = {max_id}",
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

                        self.total_amount = sum(row['subtotal'] for row in self.rows)
                        saved_discount = float(row_data.get('discount_amount', 0)) * exchange_rate
                        self.discount_amount_input.value = saved_discount
                        self.discount_type_toggle.value = 'Amount'
                        self.update_totals()
                        self.invoicenumber = row_data["invoice_number"]
                        self.currency_select.value = row_data.get('currency_id', self.default_currency_id)

                        ui.notify(f'✅ Automatically loaded sale ID: {max_id} - Invoice: {row_data["invoice_number"]}')
                    else:
                        ui.notify('No sales found in database')
                else:
                        ui.notify('No sales found in database')

            except Exception as e:
                ui.notify(f'Error loading max sale: {str(e)}')

    def create_ui(self):
        """Create the main UI layout with premium design tokens."""
        # Fetch session metadata for footer
        user = session_storage.get('user', {})
        company_info = connection.get_company_info()
        company_name = company_info.get('company_name', '') if company_info else ''

        # Add global styles
        ui.add_head_html(MDS.get_global_styles())
        ui.add_head_html(f'<script>{MDS.get_theme_switcher_js()}</script>')
        
        with ui.element('div').classes('w-full mesh-gradient h-[calc(100vh-64px)] p-0 overflow-hidden'):
                    with ui.row().classes('w-full h-full gap-0 overflow-hidden'):
                        # --- MAIN CONTENT AREA ---
                        with ui.column().classes('flex-1 h-full p-4 gap-4 relative overflow-hidden'):
                            # --- TOP BAR: HEADER ---
                            with ui.row().classes('w-full justify-between items-center bg-white/5 p-4 rounded-3xl glass border border-white/10 mb-2'):
                                # Title removed to keep the top bar compact (no empty card/column)
                                pass

                            # --- MIDDLE SECTION: DUAL PANEL ---
                            with ui.row().classes('w-full gap-6 overflow-hidden').style('height: 600px;'):
                        
                                # LEFT PANEL: Sales History (35%)
                                self.history_panel = ui.column().classes('w-[35%] h-full gap-4')
                                with self.history_panel:
                                    with ui.column().classes('w-full h-full glass p-3 rounded-3xl border border-white/10'):
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
                                            'pagination': False,
                                            'domLayout': 'normal',
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
                                    with ui.column().classes('flex-1 h-full gap-2 overflow-hidden'):
                                        # Customer & Payment Row (match compact card style from salesui_aggrid_compact.py)
                                        with ui.row().classes('w-full glass p-2 rounded-2xl border border-white/10 gap-3 items-center'):
                                            # Date
                                            with ui.column().classes('w-32 gap-1'):
                                                ui.label('Date').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                with ui.row().classes('items-center gap-2 bg-white/5 px-3 py-1 rounded-2xl border border-white/10 h-[36px]'):
                                                    self.date_input = ui.input(value=datetime.now().strftime('%Y-%m-%d')).props('borderless dense').classes('text-white text-xs font-bold w-full')

                                            # Currency
                                            with ui.column().classes('w-40 gap-1'):
                                                ui.label('Currency').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                self.currency_select = ui.select(
                                                    {row[0]: f"{row[2]} {row[1]}" for row in self.currency_rows},
                                                    value=self.default_currency_id
                                                ).props('borderless dense').classes('bg-white/5 px-4 py-1 rounded-2xl border border-white/10 text-white text-xs font-bold w-full h-[36px]').on('change', self.on_currency_change)

                                            # Customer
                                            with ui.column().classes('w-48 gap-1'):
                                                ui.label('Customer').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                with ui.row().classes('items-center gap-3 bg-white/5 px-3 py-1 rounded-xl border border-white/10 w-full hover:bg-white/10 transition-all cursor-pointer shadow-inner h-[36px]'):
                                                    ui.icon('person', size='1.05rem').classes('text-purple-400')
                                                    self.customer_input = ui.input(placeholder='Select...').props('borderless dense dark').classes('flex-1 text-white font-black text-xs').on('click', self.open_customer_dialog)

                                            # Contact
                                            with ui.column().classes('w-32 gap-1'):
                                                ui.label('Contact').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                with ui.row().classes('items-center gap-3 bg-white/5 px-3 py-1 rounded-xl border border-white/10 w-full h-[36px]'):
                                                    ui.icon('phone', size='1.1rem').classes('text-gray-400 opacity-40')
                                                    self.phone_input = ui.input(placeholder='Phone').props('borderless dense dark').classes('flex-1 text-white font-bold text-xs')

                                            # Payment
                                            with ui.column().classes('flex-1 gap-1'):
                                                ui.label('Payment').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                with ui.row().classes('items-center gap-2 bg-white/5 px-3 py-1 rounded-xl border border-white/10 h-[36px]'):
                                                    self.payment_method = ui.radio(options=['Cash', 'On Account'], value='Cash').props('inline dark color=purple').classes('text-white text-[10px] font-black uppercase tracking-tighter')

                                        # Modern Product Entry Area (compact)
                                        with ui.row().classes('w-full glass p-2 rounded-2xl border border-white/10 gap-2 items-end mt-1'):
                                            with ui.column().classes('flex-[2] gap-1'):
                                                ui.label('Barcode').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                with ui.row().classes('items-center gap-3 bg-white/5 px-3 py-1 rounded-xl border border-white/10 w-full'):
                                                    ui.icon('qr_code_scanner', size='1.25rem').classes('text-purple-400')
                                                    self.barcode_input = ui.input(placeholder='Scan or enter...').props('borderless dense dark').classes('flex-1 text-white font-bold').on('change', self.update_product_dropdown).on('keydown.enter', lambda: (self.quantity_input.run_method('focus'), ui.timer(0.1, lambda: self.quantity_input.run_method('select'), once=True)) if self.barcode_input.value else self.product_input.run_method('focus'))

                                            with ui.column().classes('flex-[3] gap-1'):
                                                ui.label('Product').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                with ui.row().classes('items-center gap-3 bg-white/5 px-3 py-1 rounded-xl border border-white/10 w-full'):
                                                    ui.icon('inventory_2', size='1.25rem').classes('text-purple-400')
                                                    self.product_input = ui.input(placeholder='Select Product...').props('borderless dense dark').classes('flex-1 text-white font-bold').on('click', self.open_product_dialog).on('keydown.enter', self.open_product_dialog)

                                            with ui.column().classes('w-20 gap-1'):
                                                ui.label('Qty').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest ml-4 text-center')
                                                with ui.row().classes('items-center gap-1 bg-white/5 px-2 py-2 rounded-2xl border border-white/10 w-full'):
                                                    self.quantity_input = ui.number(value=1).props('borderless dense dark').classes('w-full text-white font-black text-center').on('keydown.enter', lambda: (self.price_input.run_method('focus'), ui.timer(0.01, lambda: self.price_input.run_method('select'), once=True)))

                                            with ui.column().classes('w-28 gap-1'):
                                                ui.label('Price').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest ml-4 text-center')
                                                with ui.row().classes('items-center gap-1 bg-white/5 px-2 py-2 rounded-2xl border border-white/10 w-full'):
                                                    self.price_input = ui.number(value=0.0).props('borderless dense dark').classes('w-full text-white font-black text-center').on('keydown.enter', lambda: (self.discount_input.run_method('focus'), ui.timer(0.01, lambda: self.discount_input.run_method('select'), once=True)))

                                            with ui.column().classes('w-20 gap-1'):
                                                ui.label('Disc %').classes('text-[8px] font-black text-purple-400 uppercase tracking-widest ml-4 text-center')
                                                with ui.row().classes('items-center gap-1 bg-white/5 px-2 py-2 rounded-2xl border border-white/10 w-full'):
                                                    self.discount_input = ui.number(value=0).props('borderless dense dark').classes('w-full text-white font-black text-center').on('keydown.enter', self.add_product)

                                            ui.button(icon='add', on_click=self.add_product).props('elevated round size=lg color=purple').classes('shadow-lg shadow-purple-500/30 hover:scale-110 transition-transform mb-1')

                       
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


                               
                            # --- FOOTER: Consolidated High-Visibility Row ---
                            with ui.row().classes('w-full bg-black/80 backdrop-blur-xl border-t border-white/20 p-2 items-center justify-between shadow-2xl flex-nowrap'):
                                # 1. Operational Metrics
                                with ui.row().classes('items-center gap-3 shrink-0'):
                                    with ui.row().classes('items-center gap-2 bg-purple-500/10 px-3 py-1.5 rounded-xl border border-purple-500/20'):
                                        ui.icon('analytics', size='1rem').classes('text-purple-400')
                                        with ui.column().classes('gap-0'):
                                            ui.label('Commerce Pipeline').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest')
                                    
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
            
                    # Auto-load max sale, refresh history, then auto-select the max id row in the history grid
                    ui.timer(0.1, self.load_max_sale, once=True)
                    ui.timer(0.2, self.refresh_sales_table, once=True)

                    def _auto_select_max_history():
                        try:
                            sale_id = getattr(self, 'current_sale_id', None)
                            if not sale_id:
                                return

                            grid_id = getattr(self.sales_aggrid, 'id', None)
                            if not grid_id:
                                return

                            # Best-effort: find visible ag-grid row and click it.
                            # This triggers the existing `self.handle_sales_aggrid_click_wrapper`.
                            ui.run_javascript(f"""
(function() {{
  const root = document.getElementById({repr(str(grid_id))});
  if (!root) return;

  const targetId = String({int(sale_id)});

  // ag-grid marks rows like: .ag-row (inside virtual container)
  const rows = root.querySelectorAll('.ag-center-cols-container .ag-row');
  for (const r of rows) {{
    // Each row is backed by data; safest is to read the ID cell text.
    const idCell = r.querySelector('.ag-cell[data-col-id="id"]') || r.querySelector('.ag-cell[data-field="id"]');
    const txt = idCell ? idCell.textContent.trim() : '';
    if (txt === targetId) {{
      r.dispatchEvent(new MouseEvent('click', {{ bubbles: true, cancelable: true, view: window }}));
      return;
    }}
  }}
}})();
""")
                        except Exception:
                            pass

                    ui.timer(0.35, _auto_select_max_history, once=True)

    async def handle_sales_aggrid_click_wrapper(self, e):
        async with loading_indicator.show_loading('load_sale_items', 'Loading sale items...', overlay=True):
            try:
                selected_row = await self.sales_aggrid.get_selected_row()
                if selected_row and isinstance(selected_row, dict) and 'id' in selected_row:
                    sale_id = selected_row['id']
                    customer_name = selected_row['customer_name']
                    self.customer_input.value = customer_name
                    self.current_sale_id = sale_id
                    self.new_mode = False
                    
                    sale_items_data = []
                    connection.contogetrows(
                        f"SELECT p.barcode, p.product_name, si.quantity, ISNULL(si.discount_amount, 0), si.unit_price, si.total_price, ISNULL(si.vat_percentage,0), ISNULL(si.vat_amount,0) FROM sales_return_items si INNER JOIN products p ON p.id = si.product_id WHERE si.sales_return_id = {sale_id}",
                        sale_items_data
                    )
                    
                    self.rows.clear()
                    
                    # Get exchange rate for the stored currency
                    sale_currency_id = selected_row.get('currency_id', self.default_currency_id)
                    exchange_rate = float(self.currency_exchange_rates.get(sale_currency_id, 1.0))

                    discount_rows = []
                    connection.contogetrows("SELECT ISNULL(discount_amount, 0) FROM sales_returns WHERE id = ?", discount_rows, (sale_id,))
                    saved_discount = float(discount_rows[0][0]) * exchange_rate if discount_rows else 0.0
                    
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

                    self.total_amount = sum(row['subtotal'] for row in self.rows)
                    self.discount_amount_input.value = saved_discount
                    self.discount_type_toggle.value = 'Amount'
                    self.update_totals()
                    self.invoicenumber = selected_row["invoice_number"]
                    self.currency_select.value = selected_row.get('currency_id', self.default_currency_id)
                    
                    ui.notify(f'Loaded {len(self.rows)} items from sale {sale_id}', color='positive')
            except Exception as ex:
                ui.notify(f'Error: {ex}')

    async def handle_aggrid_click_wrapper(self, e):
        try:
            selected_row = await self.aggrid.get_selected_row()
            if selected_row:
                self.open_edit_dialog(selected_row)
                self.update_totals()
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
        from sales_return_reports import open_print_special_dialog
        open_print_special_dialog()

    def view_sale_transactions(self):
        sale_id = getattr(self, 'current_sale_id', None)
        if not sale_id:
            return ui.notify('Select a sale to view its connected transaction', color='warning')
        import accounting_helpers
        accounting_helpers.show_transactions_dialog(reference_type="Sale Return", reference_id=sale_id)

@ui.page('/salesreturn')
def sales_return_route():
    SalesReturnsUI()
