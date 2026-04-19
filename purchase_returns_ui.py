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
from color_palette import ColorPalette
from modern_design_system import ModernDesignSystem as MDS
from purchase_returns_service import PurchaseReturnService
from modern_ui_components import ModernActionBar
import asyncio

class PurchaseReturnsUI:
    def __init__(self, show_navigation=True):
        self.invoicenumber = ''

        # Check if user is logged in
        user = session_storage.get('user')
        if not user:
            ui.notify('Please login to access this page', color='red')
            ui.run_javascript('window.location.href = "/login"')
            return

        # Get user permissions
        permissions = connection.get_user_permissions(user['role_id'])
        allowed_pages = {page for page, can_access in permissions.items() if can_access}

        if show_navigation:
            # Create enhanced navigation instance
            navigation = EnhancedNavigation(permissions, user)
            navigation.create_navigation_drawer()  # Create drawer first
            navigation.create_navigation_header()  # Then create header with toggle button

        self.service = PurchaseReturnService()
        self.max_purchase_id = self.get_max_purchase_id()

        self.currency_rows = []
        self.currency_exchange_rates = {}
        self.currency_symbols = {}
        self.default_currency_id = 1
        self.load_currencies()
        self.previous_currency_id = self.default_currency_id

        # --- Global Variables ---
        self.columns = [
            {'headerName': 'Barcode', 'field': 'barcode', 'width': 100, 'headerClass': 'orange-header'},
            {'headerName': 'Product', 'field': 'product', 'width': 150, 'headerClass': 'orange-header'},
            {'headerName': 'Qty', 'field': 'quantity', 'width': 60,  'headerClass': 'orange-header'},
            {'headerName': 'Cost HT', 'field': 'cost', 'width': 80,  'headerClass': 'orange-header'},
            {'headerName': 'Retail TTC', 'field': 'price', 'width': 90,  'headerClass': 'orange-header'},
            {'headerName': 'Disc %', 'field': 'discount_pct', 'width': 70,  'headerClass': 'blue-header'},
            {'headerName': 'VAT %', 'field': 'vat_percentage', 'width': 70,  'headerClass': 'blue-header'},
            {'headerName': 'VAT Amt', 'field': 'vat_amount', 'width': 80,  'headerClass': 'blue-header'},
            {'headerName': 'Subtotal HT', 'field': 'subtotal', 'width': 100,  'headerClass': 'blue-header'}
        ]
        self.supplier_rows = []
        self.supplier_grid = None
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
            # Set default to L.L. if available
            for row in self.currency_rows:
                if row[2] == 'L.L.':
                    self.default_currency_id = row[0]
                    break
            else:
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
            # Retail price (TTC) logic for purchase items? 
            # We'll keep 'price' as passed from input which should be retail TTC.
            
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
            
            self.total_amount += subtotal
            self.update_totals()
            
            self.clear_inputs_inputs()
            self.aggrid.update()
            
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
        
        self.rows.clear()
        self.aggrid.options['rowData'] = self.rows
        self.aggrid.update()

        self.total_amount = 0
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
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-6xl glass p-6 border border-white/10').style('background: rgba(15, 15, 25, 0.8); backdrop-filter: blur(20px); border-radius: 2rem;'):
            ui.label('Product Catalog').classes('text-2xl font-black mb-6 text-white').style('font-family: "Outfit", sans-serif;')
            
            with ui.row().classes('w-full items-center gap-3 bg-white/5 px-4 py-2 rounded-xl border border-white/10 mb-4'):
                ui.icon('search', size='1.25rem').classes('text-purple-400')
                search_input = ui.input(placeholder='Search by name or barcode...').props('borderless dense').classes('flex-1 text-white text-sm').on('keydown.enter', lambda e: self.filter_product_rows(e.sender.value))
            
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
                {'headerName': 'Barcode', 'field': 'barcode', 'width': 120},
                {'headerName': 'Product', 'field': 'product_name', 'flex': 1},
                {'headerName': 'Stock', 'field': 'stock_quantity', 'width': 100},
                {'headerName': 'Cost', 'field': 'cost_price', 'width': 100},
                {'headerName': 'Retail', 'field': 'price', 'width': 100}
            ]
            
            self.product_grid = ui.aggrid({
                'columnDefs': columns,
                'rowData': self.product_rows,
                'rowSelection': 'single',
                'domLayout': 'normal',
            }).classes('w-full h-96 ag-theme-quartz-dark shadow-inner').style('background: transparent; border: none;')

            self.product_grid.on('cellClicked', lambda e: self.handle_product_grid_click(e, dialog))

            with ui.row().classes('w-full justify-end mt-6'):
                ui.button('Cancel', on_click=dialog.close).props('flat text-color=white').classes('px-6 rounded-xl hover:bg-white/5')
        dialog.open()

    def open_supplier_dialog(self):
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-4xl glass p-6 border border-white/10').style('background: rgba(15, 15, 25, 0.8); backdrop-filter: blur(20px); border-radius: 2rem;'):
            ui.label('Select Supplier').classes('text-2xl font-black mb-6 text-white').style('font-family: "Outfit", sans-serif;')
            
            with ui.row().classes('w-full items-center gap-3 bg-white/5 px-4 py-2 rounded-xl border border-white/10 mb-4'):
                ui.icon('search', size='1.25rem').classes('text-purple-400')
                search_input = ui.input(placeholder='Search by name or phone...').props('borderless dense').classes('flex-1 text-white text-sm').on('keydown.enter', lambda e: self.filter_supplier_rows(e.sender.value))
            
            data = []
            connection.contogetrows("SELECT id, name, phone, balance, balance_usd FROM suppliers", data)
            
            self.supplier_rows = []
            for row in data:
                self.supplier_rows.append({                   'id': row[0],                    'name': row[1],                   'phone': row[2],                   'balance_ll': row[3] or 0,                    'balance_usd': row[4] or 0                })
            
                columns = [ {'headerName': 'ID', 'field': 'id', 'width': 70},                {'headerName': 'Name', 'field': 'name', 'flex': 1},               {'headerName': 'Phone', 'field': 'phone', 'width': 150},              {'headerName': 'Balance LL', 'field': 'balance_ll', 'width': 100},                {'headerName': 'Balance USD', 'field': 'balance_usd', 'width': 110}            ]
            
            self.supplier_grid = ui.aggrid({
                'columnDefs': columns,
                'rowData': self.supplier_rows,
                'rowSelection': 'single',
                'domLayout': 'normal',
            }).classes('w-full h-80 ag-theme-quartz-dark shadow-inner').style('background: transparent; border: none;')
            
            self.supplier_grid.on('cellClicked', lambda e: self.handle_supplier_grid_click(e, dialog))
            
            with ui.row().classes('w-full justify-end mt-6'):
                ui.button('Cancel', on_click=dialog.close).props('flat text-color=white').classes('px-6 rounded-xl hover:bg-white/5')
        dialog.open()

    def filter_supplier_rows(self, search_text):
        if not search_text:
            filtered_rows = self.supplier_rows
        else:
            filtered_rows = [row for row in self.supplier_rows if any(search_text.lower() in str(value).lower() for value in row.values())]
        self.supplier_grid.options['rowData'] = filtered_rows
        self.supplier_grid.update()

    def filter_product_rows(self, search_text):
        if not search_text:
            filtered_rows = self.product_rows
        else:
            filtered_rows = [row for row in self.product_rows if any(search_text.lower() in str(value).lower() for value in row.values())]
        self.product_grid.options['rowData'] = filtered_rows
        self.product_grid.update()

    def handle_supplier_grid_click(self, e, dialog):
        try:
            row = e.args['data']
            self.supplier_input.value = row['name']
            self.phone_input.value = row['phone']
            dialog.close()
            ui.notify(f"Selected: {row['name']}")
        except Exception as ex:
            ui.notify(f"Selection error: {ex}")
            dialog.close()

    def handle_product_grid_click(self, e, dialog):
        try:
            row = e.args['data']
            self.product_input.value = row['product_name']
            self.barcode_input.value = row['barcode']
            self.discount_input.value = 0
            self.cost_input.value = row['cost_price']
            self.price_input.value = row['price']

            selected_currency_id = self.currency_select.value
            exchange_rate = float(self.currency_exchange_rates.get(selected_currency_id, 1.0))
            
            self.cost_input.value = float(self.cost_input.value) * exchange_rate
            self.price_input.value = float(self.price_input.value) * exchange_rate
            
            dialog.close()
            ui.notify(f"Added product: {row['product_name']}")
        except Exception as ex:
            ui.notify(f"Selection error: {ex}")
            dialog.close()

    def open_edit_dialog(self, row_data):
        with ui.dialog() as dialog, ui.card().classes('glass p-8 border border-white/10').style('background: rgba(15, 15, 25, 0.82); backdrop-filter: blur(20px); border-radius: 2rem; width: 420px;'):
            with ui.row().classes('w-full items-center justify-between mb-4'):
                ui.label('Edit Product').classes('text-2xl font-black text-white').style('font-family: "Outfit", sans-serif;')
                ui.icon('edit', size='1.5rem').classes('text-purple-400 opacity-80')
            
            ui.label(f"Modifying: {row_data.get('product', 'Unknown')}").classes('text-xs font-bold text-gray-400 uppercase tracking-widest mb-6 block')

            with ui.column().classes('w-full gap-5'):
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

    def update_totals(self):
        total_vat = sum(row.get('vat_amount', 0) for row in self.rows)
        subtotal = sum(row['subtotal'] for row in self.rows)
        total_quantity = sum(row['quantity'] for row in self.rows)

        self.summary_label.text = f"{len(self.rows)} items"
        self.quantity_total_label.text = f"Total Qty: {total_quantity}"

        discount_amount = float(self.discount_amount_input.value or 0)
        discount_percent = float(self.discount_percent_input.value or 0)
        
        total_ht_after_discount = subtotal * (1 - discount_percent / 100) - discount_amount
        # Re-verify VAT after global discount? Standard is HT + VAT.
        # But if total_vat was sum of items, we should keep it or scale it.
        # Let's keep it as sum of items for now.
        final_total = total_ht_after_discount + total_vat

        selected_currency_id = self.currency_select.value
        currency_symbol = '$'
        for row in self.currency_rows:
            if row[0] == selected_currency_id:
                currency_symbol = row[2]
                break

        self.subtotal_label.text = f"Total HT: {currency_symbol}{total_ht_after_discount:.2f}"
        self.vat_label.text = f"VAT: {currency_symbol}{total_vat:.2f}"
        self.total_label.text = f"Total TTC: {currency_symbol}{final_total:.2f}"
        self.total_amount = final_total

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
            self.date_input.value = details['purchase_date']
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
            self.update_totals()
            ui.notify(f'Loaded Purchase ID: {purchase_id}')
        except Exception as e:
            ui.notify(f'Error loading purchase details: {e}')

    def show_profit_dialog(self):
        """Show margin analysis (profit based on retail price)"""
        try:
            total_cost = sum(row['subtotal'] for row in self.rows)
            total_retail = sum(row['quantity'] * row['price'] for row in self.rows)
            profit = total_retail - total_cost
            margin = (profit / total_retail * 100) if total_retail > 0 else 0

            with ui.dialog() as dialog, ui.card().classes('glass p-8 border border-white/10').style('background: rgba(15, 15, 25, 0.82); backdrop-filter: blur(20px); border-radius: 2rem; width: 380px;'):
                with ui.row().classes('w-full items-center justify-between mb-4'):
                    ui.label('Margin Analysis').classes('text-2xl font-black text-white').style('font-family: "Outfit", sans-serif;')
                    ui.icon('trending_up', size='1.5rem').classes('text-green-400 opacity-80')
                
                with ui.column().classes('w-full gap-5'):
                    with ui.row().classes('w-full justify-between items-center bg-white/5 p-4 rounded-2xl border border-white/10 shadow-inner'):
                        with ui.column().classes('gap-0'):
                            ui.label('Potential Profit').classes('text-[9px] text-gray-400 font-bold uppercase tracking-tighter')
                            ui.label(f'${profit:,.2f}').classes('text-2xl font-black text-green-400')
                        
                        with ui.column().classes('gap-0 items-end'):
                            ui.label('Margin').classes('text-[9px] text-gray-400 font-bold uppercase tracking-tighter')
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
        """Open accounting transactions dialog for the current purchase."""
        ref_id = str(self.current_purchase_id) if self.current_purchase_id else None
        if not ref_id:
            ui.notify('Select a purchase to view its transaction', color='warning')
            return
        import accounting_helpers
        accounting_helpers.show_transactions_dialog(reference_type='Purchase Return', reference_id=ref_id)

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
            
            elements.append(Paragraph(f"Purchase Return (Debit Note)", styles['Heading1']))
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
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
            pdf_data_url = f"data:application/pdf;base64,{pdf_base64}"

            with ui.dialog() as pdf_dialog:
                with ui.card().classes('w-screen h-screen max-w-none max-h-none m-0 rounded-none'):
                    with ui.row().classes('w-full justify-between items-center p-4 bg-gray-100 border-b'):
                        ui.label('Purchase Invoice PDF').classes('text-xl font-bold')
                        ui.button('✕ Close', on_click=pdf_dialog.close).classes('bg-red-500 text-white px-4 py-2 rounded')
                    ui.html(f'<iframe src="{pdf_data_url}" width="100%" height="100%" style="border: none; min-height: calc(100vh - 80px);"></iframe>').classes('w-full flex-1')
            pdf_dialog.open()
        except Exception as e:
            ui.notify(f'Error generating PDF: {str(e)}')

    def create_ui(self):
        ui.add_head_html(MDS.get_global_styles())
        
        with ui.element('div').classes('w-full mesh-gradient h-[calc(100vh-64px)] p-0 overflow-hidden'):
                    with ui.row().classes('w-full h-full gap-0 overflow-hidden'):
                        with ui.column().classes('flex-1 h-full p-4 gap-4 relative overflow-hidden'):
                            with ui.row().classes('w-full justify-between items-center bg-white/5 p-4 rounded-3xl glass border border-white/10 mb-2'):
                                with ui.column().classes('gap-1'):
                                    ui.label('Procurement Engine').classes('text-xs font-black uppercase tracking-[0.2em] text-purple-400')
                                    ui.label('Purchase Return Invoice').classes('text-3xl font-black text-white').style('font-family: "Outfit", sans-serif;')
                
                                with ui.row().classes('gap-6 items-center'):
                                    with ui.row().classes('items-center gap-2 bg-white/5 px-4 py-2 rounded-xl border border-white/10'):
                                        ui.icon('event', size='1rem').classes('text-gray-400')
                                        self.date_input = ui.input(value=datetime.now().strftime('%Y-%m-%d')).props('borderless dense').classes('text-white text-xs font-bold w-24')
                    
                                    self.currency_select = ui.select(
                                        {row[0]: f"{row[2]} {row[1]}" for row in self.currency_rows}, 
                                        value=self.default_currency_id
                                    ).props('borderless dense').classes('glass px-4 py-2 rounded-xl text-white text-xs font-bold w-40').on('change', self.on_currency_change)

                            with ui.row().classes('w-full flex-1 gap-6 overflow-hidden'):
                                with ui.column().classes('w-[35%] h-full gap-4'):
                                    with ui.column().classes('w-full h-full glass p-3 rounded-3xl border border-white/10'):
                                        with ui.row().classes('w-full items-center gap-3 glass p-3 rounded-2xl border border-white/10 hover:bg-white/5 transition-all'):
                                            ui.icon('history', size='1.25rem').classes('text-purple-400 ml-1')
                                            self.history_search = ui.input(placeholder='Search history...').props('borderless dense clearable dark')\
                                                .classes('flex-1 text-white font-bold')\
                                                .on_value_change(lambda e: self.filter_history_table(e.value))
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
                                            'rowSelection': 'single',
                                            'pagination': True,
                                            'paginationPageSize': 15,
                                            'domLayout': 'normal',
                                        }).classes('w-full flex-1 ag-theme-quartz-dark shadow-inner').style('background: transparent; border: none; height: 100%;')
                        
                                        self.purchase_history_aggrid.on('cellClicked', lambda e: asyncio.create_task(self.load_purchase_details(e.args['data']['id'])))
                 
                                with ui.row().classes('flex-1 h-full gap-4 overflow-hidden'):
                                    with ui.column().classes('flex-1 h-full gap-2 overflow-hidden'):
                                        with ui.row().classes('w-full glass p-4 rounded-3xl border border-white/10 gap-5 items-center'):
                                            with ui.column().classes('flex-1 gap-1'):
                                                ui.label('Supplier Information').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                with ui.row().classes('items-center gap-3 bg-white/5 px-4 py-2 rounded-2xl border border-white/10 w-full hover:bg-white/10 transition-all cursor-pointer shadow-inner'):
                                                    ui.icon('local_shipping', size='1.25rem').classes('text-purple-400')
                                                    self.supplier_input = ui.input(placeholder='Select Supplier...').props('borderless dense dark').classes('flex-1 text-white font-black text-sm').on('click', self.open_supplier_dialog)
                                                    ui.icon('search', size='1rem').classes('text-gray-500 opacity-50')

                                            with ui.column().classes('w-48 gap-1'):
                                                ui.label('Contact').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                with ui.row().classes('items-center gap-3 bg-white/5 px-4 py-2 rounded-2xl border border-white/10 w-full'):
                                                    ui.icon('phone', size='1.25rem').classes('text-gray-400 opacity-40')
                                                    self.phone_input = ui.input(placeholder='Phone').props('borderless dense dark').classes('flex-1 text-white font-bold text-sm')

                                            with ui.column().classes('w-32 gap-1'):
                                                ui.label('Ref #').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                with ui.row().classes('items-center gap-3 bg-white/5 px-4 py-2 rounded-2xl border border-white/10 w-full'):
                                                    self.reference_input = ui.input(placeholder='Ref #').props('borderless dense dark').classes('flex-1 text-white font-bold text-sm')

                                            with ui.column().classes('gap-1'):
                                                ui.label('Payment').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                with ui.row().classes('items-center gap-2 bg-white/5 px-4 py-2 rounded-2xl border border-white/10 h-[44px]'):
                                                    self.payment_method = ui.radio(options=['Cash', 'On Account'], value='Cash').props('inline dark color=purple').classes('text-white text-[10px] font-black uppercase tracking-tighter')
                        
                                        with ui.row().classes('w-full glass p-4 rounded-3xl border border-white/10 gap-3 items-end mt-2 shrink-0'):
                                            with ui.column().classes('flex-[2] gap-1'):
                                                ui.label('Barcode').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                with ui.row().classes('items-center gap-3 bg-white/5 px-4 py-2 rounded-2xl border border-white/10 w-full'):
                                                    ui.icon('qr_code_scanner', size='1.25rem').classes('text-purple-400')
                                                    self.barcode_input = ui.input(placeholder='Barcode...').props('borderless dense dark').classes('flex-1 text-white font-bold').on('change', self.update_product_dropdown)
                            
                                            with ui.column().classes('flex-[3] gap-1'):
                                                ui.label('Product').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                with ui.row().classes('items-center gap-3 bg-white/5 px-4 py-2 rounded-2xl border border-white/10 w-full'):
                                                    ui.icon('inventory_2', size='1.25rem').classes('text-purple-400')
                                                    self.product_input = ui.input(placeholder='Product...').props('borderless dense dark').classes('flex-1 text-white font-bold').on('click', self.open_product_dialog)
                            
                                            with ui.column().classes('w-20 gap-1'):
                                                ui.label('Qty').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4 text-center')
                                                with ui.row().classes('items-center gap-1 bg-white/5 px-2 py-2 rounded-2xl border border-white/10 w-full'):
                                                    self.quantity_input = ui.number(value=1).props('borderless dense dark').classes('w-full text-white font-black text-center')
                            
                                            with ui.column().classes('w-24 gap-1'):
                                                ui.label('Disc %').classes('text-[9px] font-black text-orange-400 uppercase tracking-widest ml-4 text-center')
                                                with ui.row().classes('items-center gap-1 bg-white/5 px-2 py-2 rounded-2xl border border-white/10 w-full'):
                                                    self.discount_input = ui.number(value=0, min=0, max=100).props('borderless dense dark').classes('w-full text-white font-black text-center')

                                            with ui.column().classes('w-28 gap-1'):
                                                ui.label('Cost').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4 text-center')
                                                with ui.row().classes('items-center gap-1 bg-white/5 px-2 py-2 rounded-2xl border border-white/10 w-full'):
                                                    self.cost_input = ui.number(value=0.0).props('borderless dense dark').classes('w-full text-white font-black text-center')

                                            with ui.column().classes('w-28 gap-1'):
                                                ui.label('Retail').classes('text-[9px] font-black text-accent uppercase tracking-widest ml-4 text-center')
                                                with ui.row().classes('items-center gap-1 bg-white/5 px-2 py-2 rounded-2xl border border-white/10 w-full'):
                                                    self.price_input = ui.number(value=0.0).props('borderless dense dark').classes('w-full text-white font-black text-center')
                            
                                            ui.button(icon='add', on_click=self.add_product).props('elevated round size=lg color=purple').classes('shadow-lg shadow-purple-500/30 hover:scale-110 transition-transform mb-1')

                                        self.aggrid = ui.aggrid({
                                            'columnDefs': self.columns,
                                            'rowData': self.rows,
                                            'defaultColDef': {'flex': 1, 'minWidth': 40, 'sortable': True, 'filter': True},
                                            'rowSelection': 'single',
                                            'pagination': True,
                                            'paginationPageSize': 10,
                                            'domLayout': 'normal',
                                        }).classes('w-full ag-theme-quartz-dark shadow-inner').style('background: transparent; border: none; flex-grow: 1;')
                                        self.aggrid.on('cellClicked', self.on_row_click_edit_cells)

                                        with ui.row().classes('w-full glass p-4 rounded-3xl border border-white/10 items-center justify-between mt-2 shrink-0'):
                                            with ui.row().classes('gap-8 items-center'):
                                                ui.label('Procurement Pipeline').classes('text-[10px] font-black text-purple-400 uppercase tracking-widest opacity-50')
                                                ui.button('Margin Analytics', on_click=self.show_profit_dialog).props('flat rounded').classes('text-purple-400 font-bold uppercase tracking-wider text-xs')
                                
                                                with ui.row().classes('items-center gap-6 bg-white/5 px-5 py-2 rounded-2xl border border-white/10'):
                                                    with ui.column().classes('gap-0'):
                                                        ui.label('Items').classes('text-[9px] text-gray-400 font-bold uppercase tracking-tighter')
                                                        self.summary_label = ui.label('0 items').classes('text-sm font-black text-white')
                                    
                                                    with ui.column().classes('gap-0 border-l border-white/10 pl-6'):
                                                        ui.label('Quantity').classes('text-[9px] text-gray-400 font-bold uppercase tracking-tighter')
                                                        self.quantity_total_label = ui.label('Total Qty: 0').classes('text-sm font-black text-white')

                                            with ui.row().classes('gap-6 items-center'):
                                                with ui.column().classes('items-end gap-0'):
                                                    self.subtotal_label = ui.label('Base + VAT: $0.00').classes('text-[10px] font-bold text-gray-400 uppercase tracking-tighter')
                                                    self.vat_label = ui.label('VAT: $0.00').classes('text-[10px] font-black text-purple-400 uppercase tracking-tighter')
                                                    self.total_label = ui.label('Total: $0.00').classes('text-2xl font-black text-white px-2 rounded-lg bg-white/5')
                                
                                                with ui.element('div').classes('hidden'):
                                                    self.discount_percent_input = ui.number(value=0, on_change=self.update_totals).props('dense borderless').classes('hidden')
                                                    self.discount_amount_input = ui.number(value=0, on_change=self.update_totals).props('dense borderless').classes('hidden')
                    
                                    with ui.column().classes('w-80px items-center'):
                                        ModernActionBar(
                                            on_new=self.clear_inputs,
                                            on_save=self.save_purchase,
                                            on_undo=self.show_undo_confirmation,
                                            on_delete=self.delete_purchase,
                                            on_print=self.print_purchase_invoice,
                                            on_print_special=lambda: __import__('purchase_return_reports').open_print_special_dialog(),
                                            on_order=lambda: self.save_purchase(is_order=True),
                                            on_chatgpt=lambda: ui.run_javascript('window.open("https://chatgpt.com", "_blank");'),
                                            on_view_transaction=self.view_purchase_transaction,
                                            on_refresh=self.refresh_purchase_table,
                                            button_class='h-16',
                                            classes=' '
                                        ).style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

    
                    ui.timer(0.1, self.load_max_purchase, once=True)
                    ui.timer(0.2, self.refresh_purchase_table, once=True)


@ui.page('/purchasereturn')
def purchase_return_route():
    PurchaseReturnsUI()
