from nicegui import ui
from datetime import date as dt
from connection import connection

class SalesUI:
    def __init__(self):
        
        with ui.header().classes('items-center justify-between'):
            ui.label('Sales System').classes('text-2xl font-bold')
            ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).props('flat color=white')

        # --- Global Variables ---
        self.columns = [
            {'name': 'barcode', 'label': 'Barcode', 'field': 'barcode'},
            {'name': 'product', 'label': 'Product', 'field': 'product'},
            {'name': 'quantity', 'label': 'Qty', 'field': 'quantity'},
            {'name': 'discount', 'label': 'Discount', 'field': 'discount'},
            {'name': 'price', 'label': 'Price', 'field': 'price'},
            {'name': 'subtotal', 'label': 'Subtotal', 'field': 'subtotal'},
        ]
        self.rows = []
        self.total_amount = 0
        self.products = []
        self.customers = []
        
        # Load data from database
        self.load_data()
        
        # Initialize UI
        self.create_ui()

    def load_data(self):
        """Load products and customers from database"""
        # Load products
        products_data = []
        connection.contogetrows("SELECT barcode, name, price, stock FROM products WHERE stock > 0", products_data)
        
        for product in products_data:
            self.products.append({
                'barcode': str(product[0]),
                'product': product[1],
                'price': float(product[2]),
                'stock': int(product[3])
            })
        
        # Load customers
        customers_data = []
        connection.contogetrows("SELECT id, customer_name, phone FROM customers", customers_data)
        
        for customer in customers_data:
            self.customers.append({
                'id': customer[0],
                'customer_name': customer[1],
                'phone': customer[2]
            })

    def calculate_subtotal(self, quantity, price, discount):
        """Calculate subtotal considering quantity, price and discount."""
        return round((quantity * price) * (1 - discount / 100), 2)

    def add_product(self):
        """Add product to table and update total."""
        try:
            # Get values from inputs
            barcode = self.barcode_input.value
            product_name = self.product_input.value
            quantity = int(self.quantity_input.value) if self.quantity_input.value else 0
            discount = float(self.discount_input.value) if self.discount_input.value else 0
            price = float(self.price_input.value) if self.price_input.value else 0
            
            if not barcode or not product_name or quantity <= 0 or price <= 0:
                ui.notify('Please fill in all required fields with valid values')
                return
            
            # Calculate subtotal
            subtotal = self.calculate_subtotal(quantity, price, discount)
            
            # Add to table
            self.rows.append({
                'barcode': barcode,
                'product': product_name,
                'quantity': quantity,
                'discount': discount,
                'price': price,
                'subtotal': subtotal
            })
            
            # Update total
            self.total_amount += subtotal
            self.total_label.text = f"Total: ${self.total_amount:.2f}"
            
            # Clear inputs
            self.clear_inputs()
            
            # Update table
            self.table.update()
            
        except ValueError as e:
            ui.notify(f'Invalid input: {str(e)}')

    def clear_inputs(self):
        """Clear all input fields."""
        self.barcode_input.value = ''
        self.product_input.value = ''
        self.quantity_input.value = 1
        self.discount_input.value = 0
        self.price_input.value = 0.0

    def update_product_dropdown(self, e):
        """Update product dropdown based on barcode."""
        try:
            barcode = self.barcode_input.value
            if barcode:
                product = next((p for p in self.products if str(p['barcode']) == str(barcode)), None)
                if product:
                    self.product_input.value = product['product']
                    self.price_input.value = product['price']
        except Exception as e:
            ui.notify(f'Error updating product: {str(e)}')

    def on_row_click(self, e):
        """Handle row click events."""
        print('Row clicked:', e.args)

    def create_ui(self):
        """Create the main UI layout."""
        with ui.element('div').classes('flex w-full h-screen'):
            # === LEFT SIDE BUTTONS ===
            with ui.element('div').classes('w-1/12 bg-gray-100 p-2 flex flex-col gap-2'):
                ui.button('🆕 New', on_click=self.clear_inputs)
                ui.button('💾 Save')
                ui.button('↩️ Undo')
                ui.button('🗑️ Delete')
                ui.button('🖨️ Print')
                ui.button('🔄 Refresh')

            # === RIGHT SIDE CONTENT ===
            with ui.element('div').classes('w-11/12 p-4 flex flex-col gap-4 overflow-y-auto'):
                # --- CARD 1: Date + Customer Info ---
                with ui.card().classes('w-full'):
                    with ui.expansion('Order & Customer Info', icon='person', value=True):
                        with ui.row().classes('items-center w-full gap-4'):
                            # DATE PICKER with icon menu
                            with ui.input('Date', value=str(dt.today())) as date_input:
                                with ui.menu().props('no-parent-event') as menu:
                                    with ui.date().bind_value(date_input):
                                        with ui.row().classes('justify-end'):
                                            ui.button('Close', on_click=menu.close).props('flat')
                                with date_input.add_slot('append'):
                                    ui.icon('edit_calendar').on('click', menu.open).classes('cursor-pointer')
                            
                            # Customer selection with dialog
                            self.customer_input = ui.input('Customer', placeholder='Select customer')
                            self.phone_input = ui.input('Phone', placeholder='Customer phone')
                            
                            with ui.dialog() as dialog, ui.card():
                                headers = []
                                connection.contogetheaders("SELECT id, customer_name, phone FROM customers", headers)
                                columns = [{'name': header, 'label': header.title(), 'field': header, 'sortable': True} for header in headers]
                                
                                # Fetch data from database
                                data = []
                                connection.contogetrows("SELECT id, customer_name, phone FROM customers", data)
                                # Convert data to list of dictionaries
                                rows = []
                                for row in data:
                                    row_dict = {}
                                    for i, header in enumerate(headers):
                                        row_dict[header] = row[i]
                                    rows.append(row_dict)
                                
                                table = ui.table(columns=columns, rows=rows, pagination=5).classes('w-parent')
                                ui.input('Search').bind_value(table, 'filter')
                                
                                def on_row_click(row_data):
                                    selected_row = row_data.args[1]
                                    self.customer_input.value = selected_row['customer_name']
                                    self.phone_input.value = selected_row['phone']
                                    dialog.close()
                                    
                                table.on('rowClick', on_row_click)
                            
                            # Open dialog when clicking on customer input
                            self.customer_input.on('click', dialog.open)
                            ui.input('Currency', value='Lebanese Lira')

                # --- CARD 2: Product Entry ---
                with ui.card().classes('w-full'):
                    with ui.row().classes('items-center w-full gap-4'):
                        self.barcode_input = ui.input('Barcode', placeholder='Enter barcode').on('change', lambda e: self.update_product_dropdown(e))
                        self.product_input = ui.input('Product Name', placeholder='Product name')
                        self.quantity_input = ui.number('Quantity', value=1, min=1)
                        self.discount_input = ui.number('Discount', value=0, min=0, max=100)
                        self.price_input = ui.number('Price', value=0.0, min=0)
                        ui.button('Add', on_click=self.add_product)

                # --- CARD 3: Product Table ---
                with ui.card().classes('w-full'):
                    self.table = ui.table(columns=self.columns, rows=self.rows, row_key='barcode').on('rowClick', lambda e: self.on_row_click(e))
                    self.total_label = ui.label("Total: $0.00").classes("font-bold text-lg mt-2")

# Create and run the application
@ui.page('/sales')
def sales_page_route():
    SalesUI()
        self.products = []
