from nicegui import ui, app
from datetime import datetime
from decimal import Decimal
import sqlite3
from typing import List, Dict, Any
from connection import connection

class NiceGUIPOS:
    def __init__(self):
        self.cart_items = []
        self.vat_rate = Decimal('0.11')  # 11% VAT
        self.customers = []
        self.products = []
        self.selected_customer = "Cash Client"
        self.selected_currency = "USD"
        
        self.load_data()
        self.setup_ui()
        
    def load_data(self):
        """Load customers and products from database"""
        try:
            # Load customers
            cursor = connection.contogetrows
            customers = []
            cursor('SELECT id, customerName FROM customer ORDER BY customerName', customers)
            self.customers = ["Cash Client"] + [row[1] for row in customers[0]]
            
            # Load products
            products = []
            cursor('SELECT id, productName, barcode, price FROM products ORDER BY productName', products)
            self.products = products[0]
            
        except Exception as e:
            print(f"Error loading data: {e}")
            self.customers = ["Cash Client"]
            self.products = []
            
    def setup_ui(self):
        """Setup the NiceGUI interface"""
        ui.page_title('Point of Sale System')
        
        # Header
        with ui.header(elevated=True).style('background-color: #1976D2'):
            ui.label('Point of Sale System').classes('text-h4 text-white')
            
        # Main container
        with ui.column().classes('w-full p-4'):
            
            # Transaction Details Card
            with ui.card().classes('w-full mb-4'):
                ui.label('Transaction Details').classes('text-h6 mb-2')
                
                with ui.row().classes('w-full items-center'):
                    # Date
                    self.date_input = ui.input(
                        label='Date',
                        value=datetime.now().strftime('%Y-%m-%d')
                    ).classes('w-32')
                    
                    # Customer
                    self.customer_select = ui.select(
                        self.customers,
                        label='Customer',
                        value=self.selected_customer
                    ).classes('w-48')
                    
                    # Currency
                    self.currency_select = ui.select(
                        ['USD', 'LBP'],
                        label='Currency',
                        value=self.selected_currency
                    ).classes('w-24')
                    
                    # Invoice Number
                    self.invoice_input = ui.input(
                        label='Invoice #',
                        value=self.generate_invoice_number()
                    ).classes('w-32')
            
            # Product Entry Card
            with ui.card().classes('w-full mb-4'):
                ui.label('Add Product').classes('text-h6 mb-2')
                
                with ui.row().classes('w-full items-center gap-2'):
                    # Barcode
                    self.barcode_input = ui.input(
                        label='Barcode',
                        placeholder='Scan barcode...'
                    ).classes('w-32').on('keydown.enter', self.lookup_product)
                    
                    # Product Name
                    product_names = [p[1] for p in self.products]
                    self.product_select = ui.select(
                        product_names,
                        label='Product',
                        with_input=True
                    ).classes('w-48').on_value_change(self.on_product_change)
                    
                    # Quantity
                    self.qty_input = ui.number(
                        label='Qty',
                        value=1,
                        min=1
                    ).classes('w-20')
                    
                    # Price
                    self.price_input = ui.number(
                        label='Price',
                        value=0.00,
                        format='%.2f'
                    ).classes('w-24')
                    
                    # VAT
                    self.vat_toggle = ui.toggle(['No VAT', 'VAT'], value='No VAT').classes('w-32')
                    
                    # Add Button
                    ui.button('Add to Cart', on_click=self.add_to_cart).classes('bg-green text-white')
            
            # Cart Display
            with ui.card().classes('w-full mb-4'):
                ui.label('Shopping Cart').classes('text-h6 mb-2')
                
                # Cart table
                columns = [
                    {'name': 'barcode', 'label': 'Barcode', 'field': 'barcode', 'align': 'left'},
                    {'name': 'product', 'label': 'Product', 'field': 'product', 'align': 'left'},
                    {'name': 'vat', 'label': 'VAT', 'field': 'vat', 'align': 'center'},
                    {'name': 'qty', 'label': 'Qty', 'field': 'quantity', 'align': 'center'},
                    {'name': 'price', 'label': 'Price', 'field': 'price', 'align': 'right'},
                    {'name': 'total', 'label': 'Total', 'field': 'total', 'align': 'right'},
                ]
                
                self.cart_table = ui.table(
                    columns=columns,
                    rows=[],
                    row_key='id',
                    pagination=10
                ).classes('w-full')
                
                # Action buttons
                with ui.row().classes('w-full justify-end gap-2 mt-2'):
                    ui.button('Clear Cart', on_click=self.clear_cart).classes('bg-red text-white')
                    ui.button('Save Sale', on_click=self.save_sale).classes('bg-green text-white')
            
            # Totals Display
            with ui.card().classes('w-full'):
                ui.label('Totals').classes('text-h6 mb-2')
                
                with ui.row().classes('w-full justify-end gap-8'):
                    self.subtotal_label = ui.label('Subtotal: $0.00').classes('text-h6')
                    self.vat_label = ui.label('VAT (11%): $0.00').classes('text-h6')
                    self.total_label = ui.label('Total: $0.00').classes('text-h4 text-bold')
    
    def generate_invoice_number(self) -> str:
        """Generate unique invoice number"""
        try:
            cursor = connection.contogetrows
            result = []
            cursor("SELECT COUNT(*) FROM sales", result)
            count = result[0][0][0] if result and result[0] else 0
            return f"INV-{datetime.now().strftime('%Y%m%d')}-{count + 1:04d}"
        except:
            return f"INV-{datetime.now().strftime('%Y%m%d')}-0001"
    
    def lookup_product(self, e=None):
        """Lookup product by barcode"""
        barcode = self.barcode_input.value
        if barcode:
            for product in self.products:
                if str(product[2]) == str(barcode):
                    self.product_select.value = product[1]
                    self.price_input.value = float(product[3])
                    break
    
    def on_product_change(self, value):
        """Handle product selection change"""
        if value:
            for product in self.products:
                if product[1] == value:
                    self.barcode_input.value = str(product[2])
                    self.price_input.value = float(product[3])
                    break
    
    def add_to_cart(self):
        """Add product to cart"""
        try:
            product_name = self.product_select.value
            barcode = self.barcode_input.value
            qty = int(self.qty_input.value)
            price = float(self.price_input.value)
            has_vat = self.vat_toggle.value == 'VAT'
            
            if not product_name or qty <= 0 or price <= 0:
                ui.notify('Please enter valid product details', type='negative')
                return
            
            # Calculate totals
            item_total = qty * price
            if has_vat:
                vat_amount = item_total * float(self.vat_rate)
                item_total += vat_amount
            
            # Add to cart
            self.cart_items.append({
                'id': len(self.cart_items) + 1,
                'barcode': barcode,
                'product': product_name,
                'vat': 'Yes' if has_vat else 'No',
                'quantity': qty,
                'price': f"${price:.2f}",
                'total': f"${item_total:.2f}'
            })
            
            self.update_cart_display()
            self.clear_product_entry()
            ui.notify('Product added to cart', type='positive')
            
        except Exception as e:
            ui.notify(f'Error adding product: {str(e)}', type='negative')
    
    def update_cart_display(self):
        """Update cart display and totals"""
        self.cart_table.rows = self.cart_items
        
        # Calculate totals
        subtotal = 0.0
        vat_total = 0.0
        
        for item in self.cart_items:
            price = float(item['price'].replace('$', ''))
            qty = item['quantity']
            item_subtotal = price * qty
            subtotal += item_subtotal
            
            if item['vat'] == 'Yes':
                vat_total += item_subtotal * float(self.vat_rate)
        
        total = subtotal + vat_total
        
        self.subtotal_label.text = f'Subtotal: ${subtotal:.2f}'
        self.vat_label.text = f'VAT (11%): ${vat_total:.2f}'
        self.total_label.text = f'Total: ${total:.2f}'
    
    def clear_product_entry(self):
        """Clear product entry fields"""
        self.barcode_input.value = ''
        self.product_select.value = None
        self.qty_input.value = 1
        self.price_input.value = 0.00
        self.vat_toggle.value = 'No VAT'
    
    def clear_cart(self):
        """Clear all items from cart"""
        self.cart_items.clear()
        self.update_cart_display()
        ui.notify('Cart cleared', type='info')
    
    def save_sale(self):
        """Save sale to database"""
        if not self.cart_items:
            ui.notify('No items in cart', type='negative')
            return
        
        try:
            customer = self.customer_select.value
            currency = self.currency_select.value
            total = float(self.total_label.text.split('$')[1])
            
            # Insert sale record
            cursor = connection.insertingtodatabase
            sale_sql = """
                INSERT INTO sales (date, customer, total_amount, currency, invoice_number)
                VALUES (?, ?, ?, ?, ?)
            """
            sale_values = (
                self.date_input.value,
                customer,
                total,
                currency,
                self.invoice_input.value
            )
            cursor(sale_sql, sale_values)
            
            # Get sale ID
            cursor2 = connection.contogetrows
            sale_id = cursor2("SELECT MAX(id) FROM sales")[0][0]
            
            # Insert sale items
            for item in self.cart_items:
                item_sql = """
                    INSERT INTO sale_items (sale_id, barcode, product_name, quantity, price, vat, total)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                item_values = (
                    sale_id,
                    item['barcode'],
                    item['product'],
                    item['quantity'],
                    float(item['price'].replace('$', '')),
                    1 if item['vat'] == 'Yes' else 0,
                    float(item['total'].replace('$', ''))
                )
                cursor(item_sql, item_values)
            
            ui.notify('Sale completed successfully!', type='positive')
            self.clear_cart()
            self.invoice_input.value = self.generate_invoice_number()
            
        except Exception as e:
            ui.notify(f'Error saving sale: {str(e)}', type='negative')

# Create and run the POS system
@ui.page('/pos')
def pos_page():
    pos = NiceGUIPOS()

# Run the application
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title='POS System', port=8080, reload=True)
