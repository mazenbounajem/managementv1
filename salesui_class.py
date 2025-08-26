from nicegui import ui
from datetime import date as dt
from connection import connection

class SalesUI:
    def __init__(self):
        with ui.header().classes('items-center justify-between'):
            ui.label('Sales Management').classes('text-2xl font-bold')
            ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).props('flat color=white')

        # --- Mock Data ---
        self.products = [
            {'barcode': '123456789', 'product': 'iPhone 15', 'price': 1200.00},
            {'barcode': '987654321', 'product': 'Samsung Galaxy S24', 'price': 1000.00},
            {'barcode': '456789123', 'product': 'MacBook Pro', 'price': 2500.00},
            {'barcode': '321654987', 'product': 'iPad Air', 'price': 800.00},
            {'barcode': '789123456', 'product': 'AirPods Pro', 'price': 250.00},
        ]
        self.datacustomers=[]

        self.customers = connection.contogetrows("select customer_name,phone from customers",self.datacustomers)

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

        # Initialize UI
        self.create_ui()

    def calculate_subtotal(self, quantity, price, discount):
        """Calculate subtotal considering quantity, price and discount."""
        return round((quantity * price) * (1 - discount / 100), 2)

    def add_product(self):
        """Add product to table and update total."""
        # Get values from inputs
        barcode = self.barcode_input.value
        product_name = self.product_input.value
        quantity = int(self.quantity_input.value)
        discount = float(self.discount_input.value)
        price = float(self.price_input.value)
        
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

    def clear_inputs(self):
        """Clear all input fields."""
        self.barcode_input.value = ''
        self.product_input.value = ''
        self.quantity_input.value = 1
        self.discount_input.value = 0
        self.price_input.value = 0.0

    def update_product_dropdown(self, e):
        """Update product dropdown based on barcode."""
        barcode = self.barcode_input.value
        product = next((p for p in self.products if p['barcode'] == barcode), None)
        if product:
            self.product_input.value = product['product']
            self.price_input.value = product['price']

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
                            ui.input('Customer Name', value='Cash Client')
                            ui.input('Phone', value='000000')
                            ui.input('Currency', value='Lebanese Lira')
                            with ui.dialog() as dialog, ui.card():
                                datah=[]
                                connection.contogetheaders('select * from customers',datah)
                                rows=[]
                                connection.contogetrows('select * from customers',rows)
                                ui.table(columns=datah,rows=rows)
                            ui.input('Customers', on_change=dialog.open)
                                        
                # --- CARD 2: Product Entry ---
                with ui.card().classes('w-full'):
                    with ui.row().classes('items-center w-full gap-4'):
                        self.barcode_input = ui.input('Barcode', placeholder='Enter barcode').on('change', self.update_product_dropdown)
                        self.product_input = ui.input('Product Name', placeholder='Product name')
                        self.quantity_input = ui.number('Quantity', value=1, min=1)
                        self.discount_input = ui.number('Discount', value=0, min=0, max=100)
                        self.price_input = ui.number('Price', value=0.0, min=0)
                        ui.button('Add', on_click=self.add_product)

                # --- CARD 3: Product Table ---
                with ui.card().classes('w-full'):
                    self.table = ui.table(columns=self.columns, rows=self.rows, row_key='barcode').on('rowClick', self.on_row_click)
                    self.total_label = ui.label("Total: $0.00").classes("font-bold text-lg mt-2")

# Create and run the application
@ui.page('/sales')
def sales_page_route():
     SalesUI()
    
