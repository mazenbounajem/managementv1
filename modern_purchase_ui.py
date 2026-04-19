"""
Modern Purchase UI
Complete redesign with modern components and interactions, matching the Sales UI style.
"""

from nicegui import ui
from datetime import date as dt
from connection import connection
from modern_design_system import ModernDesignSystem as MDS
from modern_ui_components import (
    ModernCard, ModernCardHeader, ModernCardBody, ModernButton, ModernInput, ModernTable, 
    ModernStats, ModernBadge, ModernToast, ModernSearchBar
)
from session_storage import session_storage
from purchase_service import PurchaseService
from datetime import datetime
import asyncio

@ui.page('/modern-purchase')
def modern_purchase_page():
    ModernPurchaseUI()

class ModernPurchaseUI:
    def __init__(self):
        # Check authentication
        user = session_storage.get('user')
        if not user:
            ui.notify('Please login to access this page', color='red')
            ui.run_javascript('window.location.href = "/login"')
            return
        
        # Initialize services and data
        self.service = PurchaseService()
        self.user = user
        self.rows = []
        self.total_amount = 0
        self.current_purchase_id = None
        self.currency_id = 2  # Default USD
        
        # Load data
        self.product_map = {}
        self.supplier_map = {}
        self.currency_map = {}
        self.load_initial_data()
        
        # Create UI
        self.create_ui()
    
    def load_initial_data(self):
        """Load initial data for selects"""
        try:
            # Load products
            headers, prods = self.service.get_all_products()
            for p in prods:
                self.product_map[p['product_name']] = p['barcode'] # Using barcode as key for product entry

            # Load suppliers
            headers, sups = self.service.get_all_suppliers()
            self.supplier_options = [s['name'] for s in sups]
            for s in sups:
                self.supplier_map[s['name']] = s['id']

            # Load currencies
            headers, curs = self.service.get_all_currencies()
            self.currency_options = [c['currency_code'] for c in curs]
            for c in curs:
                self.currency_map[c['currency_code']] = c['id']

        except Exception as e:
            ui.notify(f"Error loading initial data: {e}", color='red')

    def create_ui(self):
        """Create the modern purchase interface using the reusable layout"""
        from modern_page_layout import ModernPageLayout
        
        # Create the page content
        def build_purchase_content():
            with ui.element('div').classes('w-full min-h-screen p-8 mesh-gradient animate-fade-in'):
                # Dashboard stats
                #self.create_stats_section()
                
                # Purchase form and table
                with ui.column().classes('w-full gap-8'):
                    # Full width: Purchase history 
                    with ui.column().classes('gap-6').style('width: 100%;'):
                        self.create_purchase_history()
                    
                    # Below: Invoice form (centered)
                    with ui.column().classes('gap-6 max-w-4xl mx-auto').style('width: 100%;'):
                        self.create_invoice_form()
        
        # Use the modern page layout
        ModernPageLayout.create_page_header()
        build_purchase_content()

        # Universal Action Bar
        from modern_ui_components import ModernActionBar
        ModernActionBar(
            on_new=self.clear_form,
            on_save=self.save_purchase,
            on_delete=self.delete_purchase,
            on_refresh=self.refresh_data,
            on_chatgpt=lambda: ui.run_javascript('window.open("https://chatgpt.com", "_blank");'),
            button_class='h-16'
        )

    def refresh_data(self):
        """Refresh history and initial data"""
        self.load_initial_data()
        self.history_data = self.service.get_all_purchases()
        self.purchase_aggrid.options['rowData'] = self.history_data
        self.purchase_aggrid.update()
        ui.notify("Data refreshed")

   
    def create_purchase_history(self):
        """Creates the purchase history section (Left Column)."""
        with ModernCard(glass=True).classes('w-full h-full p-6').style('border-radius: 2rem;'):
            ModernCardHeader("Purchase History")
            with ModernCardBody():
                # Search / Filter Bar
                with ui.row().classes('w-full mb-4'):
                    self.history_search = ModernSearchBar("Search invoices, suppliers...")\
                        .classes('flex-grow')
                    self.history_search.on('update:modelValue', lambda e: self.filter_history(e))

                # Purchase Data Grid
                purchase_columns = [
                    {'headerName': 'ID', 'field': 'id', 'width': 60, 'sortable': True, 'filter': True},
                    {'headerName': 'Date', 'field': 'purchase_date', 'width': 100, 'sortable': True, 'filter': True},
                    {'headerName': 'Supplier', 'field': 'supplier_name', 'width': 150, 'sortable': True, 'filter': True},
                    {'headerName': 'Total', 'field': 'total_amount', 'width': 90, 'sortable': True, 'filter': True},
                    {'headerName': 'Status', 'field': 'payment_status', 'width': 90, 'sortable': True, 'filter': True}
                ]
                
                self.history_data = self.service.get_all_purchases()

                self.purchase_aggrid = ui.aggrid({
                    'columnDefs': purchase_columns,
                    'rowData': self.history_data,
                    'rowSelection': 'single',
                    'domLayout': 'autoHeight',
                }).classes('w-full ag-theme-quartz-custom rounded-md border border-gray-200').style('min-height: 400px; max-height: 60vh; overflow-y: auto;')
                
                self.purchase_aggrid.on('cellClicked', lambda e: self.load_purchase_details(e.args['data']['id']))

    def filter_history(self, query):
        if not query:
            self.purchase_aggrid.options['rowData'] = self.history_data
        else:
            q = query.lower()
            filtered = [r for r in self.history_data if q in str(r['id']) or q in r['supplier_name'].lower() or q in r['invoice_number'].lower()]
            self.purchase_aggrid.options['rowData'] = filtered
        self.purchase_aggrid.update()

    def create_invoice_form(self):
        """Creates the invoice form for new purchases (Right Column)."""
        with ModernCard(glass=True).classes('w-full h-full p-6 flex flex-col').style('border-radius: 2rem;'):
            ModernCardHeader("Purchase / Invoice Entry")
            with ModernCardBody():
                # --- Top: Supplier & Order Details ---
                with ui.row().classes('w-full gap-4 mb-6'):
                    self.supplier_select = ui.select(self.supplier_options, label="Supplier", with_input=True).classes('flex-1')
                    self.date_input = ModernInput("Date", value=dt.today().strftime('%Y-%m-%d')).classes('w-40')
                    
                    # Payment method / Status selector
                    with ui.column().classes('justify-center'):
                        ui.label("Status").classes('text-xs text-gray-500 mb-1')
                        self.payment_status = ui.radio(options=['completed', 'pending'], value='completed').props('inline dense color="primary"')

                # --- Middle: Product Entry ---
                with ui.row().classes('w-full gap-2 items-end mb-4 bg-gray-100/50 p-4 rounded-xl border border-gray-100'):
                    self.barcode_input = ModernInput("Barcode", placeholder="Scan...").classes('w-32')
                    self.product_input = ui.select(list(self.product_map.keys()), label="Product", with_input=True).classes('flex-1')
                    self.quantity_input = ui.number('Qty', value=1, min=1).props('outlined dense').classes('w-20 bg-white rounded-md')
                    self.cost_input = ui.number('Cost', value=0.0, min=0).props('outlined dense').classes('w-24 bg-white rounded-md')
                    self.price_input = ui.number('Retail Price', value=0.0, min=0).props('outlined dense').classes('w-24 bg-white rounded-md')
                    
                    ModernButton("Add", icon="add", variant="primary", on_click=self.add_item).classes('mb-1')

                # --- Center: Invoice Items Grid ---
                self.item_columns = [
                    {'headerName': 'Barcode', 'field': 'barcode', 'width': 100},
                    {'headerName': 'Product', 'field': 'product', 'flex': 1},
                    {'headerName': 'Qty', 'field': 'quantity', 'width': 80},
                    {'headerName': 'Cost', 'field': 'cost', 'width': 100},
                    {'headerName': 'Retail', 'field': 'price', 'width': 100},
                    {'headerName': 'Subtotal', 'field': 'subtotal', 'width': 100}
                ]
                
                self.items_aggrid = ui.aggrid({
                    'columnDefs': self.item_columns,
                    'rowData': self.rows,
                    'rowSelection': 'single',
                    'domLayout': 'autoHeight',
                }).classes('w-full ag-theme-quartz-custom rounded-md border border-gray-200 flex-1').style('min-height: 250px;')

                # --- Bottom: Summary Section ---
                with ui.row().classes('w-full justify-end items-end border-t border-gray-100 pt-4 mt-auto'):
                    
                    # Right Totals
                    with ui.column().classes('items-end gap-1'):
                        with ui.row().classes('items-center gap-4 text-gray-500'):
                            ui.label("Subtotal:")
                            self.subtotal_label = ui.label("$0.00").classes('font-mono font-medium')
                        with ui.row().classes('items-center gap-4 text-gray-500'):
                            ui.label("Discount Val:")
                            self.discount_input = ui.number(value=0, min=0, on_change=self.calculate_totals).props('outlined dense borderless').classes('w-24 bg-blue-50/50 rounded-md text-right font-mono')
                        with ui.row().classes('items-center gap-4 text-2xl font-bold text-gray-800 mt-2'):
                            ui.label("Total:")
                            self.total_label = ui.label("$0.00").classes('font-mono text-primary-dark')
                        
                        # Save Sale Button removed in favor of Sidebar

    def add_item(self):
        """Add item to the current purchase items list"""
        try:
            product_name = self.product_input.value
            if not product_name:
                return ui.notify("Please select a product", color='warning')
            
            barcode = self.barcode_input.value or self.product_map.get(product_name, '')
            qty = self.quantity_input.value or 0
            cost = self.cost_input.value or 0
            price = self.price_input.value or 0
            
            subtotal = qty * cost
            
            item = {
                'barcode': barcode,
                'product': product_name,
                'quantity': qty,
                'cost': cost,
                'price': price,
                'subtotal': subtotal,
                'discount': 0,
                'profit': price - cost
            }
            
            self.rows.append(item)
            self.items_aggrid.options['rowData'] = self.rows
            self.items_aggrid.update()
            self.calculate_totals()
            
            # Reset inputs
            self.barcode_input.set_value('')
            self.product_input.set_value(None)
            self.quantity_input.set_value(1)
            self.cost_input.set_value(0)
            self.price_input.set_value(0)
            
        except Exception as e:
            ui.notify(f"Error adding item: {e}", color='red')

    def calculate_totals(self):
        """Calculate and update total labels"""
        subtotal = sum(item['subtotal'] for item in self.rows)
        discount = self.discount_input.value or 0
        total = subtotal - discount
        
        self.total_amount = total
        self.subtotal_label.set_text(f"${subtotal:,.2f}")
        self.total_label.set_text(f"${total:,.2f}")

    def clear_form(self):
        """Reset the form to initial state"""
        self.current_purchase_id = None
        self.rows = []
        self.items_aggrid.options['rowData'] = self.rows
        self.items_aggrid.update()
        self.supplier_select.set_value(None)
        self.discount_input.set_value(0)
        self.calculate_totals()
        ui.notify("Form cleared")

    def save_purchase(self):
        """Save the purchase record via PurchaseService"""
        try:
            if not self.rows:
                return ui.notify("No items in purchase", color='warning')
            
            supplier_id = self.supplier_map.get(self.supplier_select.value)
            if not supplier_id:
                return ui.notify("Please select a supplier", color='warning')

            data = {
                'purchase_date': self.date_input.value,
                'supplier_id': supplier_id,
                'subtotal': sum(item['subtotal'] for item in self.rows),
                'discount_amount': self.discount_input.value or 0,
                'final_total': self.total_amount,
                'payment_status': self.payment_status.value,
                'payment_method': 'Cash' if self.payment_status.value == 'completed' else 'On Account',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'user': self.user,
                'session_id': session_storage.get('session_id', 'Unknown'),
                'currency_id': self.currency_id
            }

            self.service.save_purchase(data, self.rows, self.current_purchase_id)
            ui.notify("Purchase saved successfully!", color='positive')
            
            # Refresh history and clear form
            self.history_data = self.service.get_all_purchases()
            self.purchase_aggrid.options['rowData'] = self.history_data
            self.purchase_aggrid.update()
            self.clear_form()

        except Exception as e:
            ui.notify(f"Error saving purchase: {e}", color='red')

    def load_purchase_details(self, purchase_id):
        """Load an existing purchase for editing"""
        try:
            details = self.service.get_purchase_details(purchase_id)
            self.current_purchase_id = purchase_id
            
            self.supplier_select.set_value(details['supplier_name'])
            self.date_input.set_value(details['purchase_date'])
            self.payment_status.set_value(details['payment_status'])
            
            self.rows = details['rows']
            self.items_aggrid.options['rowData'] = self.rows
            self.items_aggrid.update()
            
            # We need to find the discount amount. PurchaseService doesn't return it directly in details
            # but we can get it from the header if we add a method or calculate it.
            # For now, let's assume discount is 0 or needs to be fetched.
            # header = self.service.repository.get_purchase_header_data(purchase_id) ...
            
            self.calculate_totals()
            ui.notify(f"Loaded Purchase #{purchase_id}")
            
        except Exception as e:
            ui.notify(f"Error loading purchase: {e}", color='red')

    def delete_purchase(self):
        """Delete the currently selected purchase"""
        if not self.current_purchase_id:
            return ui.notify("No purchase selected to delete", color='warning')
        
        try:
            msg = self.service.delete_purchase(self.current_purchase_id, self.user['user_id'])
            ui.notify(msg, color='positive')
            
            # Refresh history and clear form
            self.history_data = self.service.get_all_purchases()
            self.purchase_aggrid.options['rowData'] = self.history_data
            self.purchase_aggrid.update()
            self.clear_form()
            
        except Exception as e:
            ui.notify(f"Error deleting purchase: {e}", color='red')

# Alias for app.py import
#modern_purchase_page = modern_purchase_page
