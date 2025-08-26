# from nicegui import ui
# from connection import connection
# from datetime import datetime
# import uuid

# class SalesUI:
#     def __init__(self):
#         self.cart = []
#         self.total = 0.0
#         self.customer_name = ""
#         self.invoice_number = ""
#         self.payment_method = "Cash"
#         self.currency = "USD"
        
#     def create_sales_ui(self):
#         """Create the sales interface using NiceGUI"""
        
#         # Header
#         with ui.header().style('background-color: #1976D2; color: white'):
#             ui.label('POS Sales System').classes('text-h4')
#             ui.space()
#             ui.label(f'Invoice: {self.generate_invoice()}').classes('text-subtitle1')
        
#         # Main layout
#         with ui.row().classes('w-full q-pa-md'):
#             # Left panel - Product selection
#             with ui.column().classes('col-8'):
#                 self.create_product_section()
                
#             # Right panel - Cart and checkout
#             with ui.column().classes('col-4'):
#                 self.create_cart_section()
#                 self.create_checkout_section()
    
#     def create_product_section(self):
#         """Create product selection interface"""
#         ui.label('Available Products').classes('text-h5 q-mb-md')
        
#         # Search bar above product grid in a row
#         with ui.row().classes('w-full q-mb-md'):
#             self.search_input = ui.input('Search Products...').classes('col-12')
#             self.search_input.on('input', self.filter_products)
        
#         # Product grid
#         with ui.row().classes('w-full'):
#             self.load_products()
    
#     def create_cart_section(self):
#         """Create shopping cart interface"""
#         ui.label('Shopping Cart').classes('text-h5 q-mb-md')
        
#         # Customer name, payment method, and currency above the cart table in a row
#         with ui.row().classes('q-mb-md'):
#             self.customer_input = ui.input('Customer Name').classes('col-6')
#             self.payment_method_select = ui.select(['Cash', 'Card', 'Online'], label='Payment Method').classes('col-3')
#             self.currency_select = ui.select(['USD', 'Lebanese Lira'], label='Currency').classes('col-3')
        
#         # Cart items table
#         self.cart_table = ui.table(
#             columns=[
#                 {'name': 'product', 'label': 'Product', 'field': 'product', 'align': 'left'},
#                 {'name': 'price', 'label': 'Price', 'field': 'price', 'align': 'right'},
#                 {'name': 'quantity', 'label': 'Qty', 'field': 'quantity', 'align': 'center'},
#                 {'name': 'total', 'label': 'Total', 'field': 'total', 'align': 'right'},
#                 {'name': 'actions', 'label': 'Actions', 'field': 'actions', 'align': 'center'}
#             ],
#             rows=[],
#             row_key='id'
#         ).classes('w-full')
        
#         # Total display
#         self.total_label = ui.label('Total: $0.00').classes('text-h6 q-mt-md')
    
#     def create_checkout_section(self):
#         """Create checkout interface"""
#         ui.label('Checkout').classes('text-h5 q-mb-md')
        
#         # Checkout button
#         ui.button('Complete Sale', on_click=self.complete_sale).classes('w-full bg-positive text-white')
    
#     def load_products(self):
#         """Load products from database"""
#         try:
#             self.all_products = []
#             cursor = connection.contogetrows
#             cursor("SELECT id, product_name, price FROM products", self.all_products)
            
#             self.filtered_products = self.all_products.copy()
            
#             self.display_products()
                    
#         except Exception as e:
#             ui.notify(f'Error loading products: {str(e)}', type='negative')
    
#     def add_to_cart(self, product):
#         """Add product to cart"""
#         product_id, name, price = product
        
#         # Check if product already in cart
#         for item in self.cart:
#             if item['id'] == product_id:
#                 item['quantity'] += 1
#                 item['total'] = item['quantity'] * item['price']
#                 self.update_cart_display()
#                 return
#         self.cart.append({
#             'id': product_id,
#             'product': name,
#             'price': price,
#             'quantity': 1,
#             'total': price
#         })
        
#         self.update_cart_display()
    
#     def update_cart_display(self):
#         """Update cart display"""
#         self.cart_table.rows = self.cart
#         self.total = sum(item['total'] for item in self.cart)
#         currency_symbol = '$' if self.currency == 'USD' else 'L.L.'
#         self.total_label.text = f'Total: {currency_symbol}{self.total:.2f}'
    
#     def remove_from_cart(self, item_id):
#         """Remove item from cart"""
#         self.cart = [item for item in self.cart if item['id'] != item_id]
#         self.update_cart_display()
    
#     def complete_sale(self):
#         """Complete the sale and save to database"""
#         if not self.cart:
#             ui.notify('Cart is empty!', type='warning')
#             return
            
#         self.customer_name = self.customer_input.value
#         if not self.customer_name:
#             ui.notify('Please enter customer name!', type='warning')
#             return
        
#         self.payment_method = self.payment_method_select.value
#         self.currency = self.currency_select.value or 'USD'
            
#         try:
#             # Generate invoice number
#             self.invoice_number = self.generate_invoice()
            
#             # Insert sale
#             cursor = connection.insertingtodatabase
#             sale_sql = """
#             INSERT INTO sales (date, customer, total_amount, invoice_number, payment_method, currency) 
#             VALUES (?, ?, ?, ?, ?, ?)
#             """
#             cursor(sale_sql, (datetime.now(), self.customer_name, self.total, self.invoice_number, self.payment_method, self.currency))
            
#             # Get sale ID
#             cursor = connection.getid
#             sale_id = cursor("SELECT TOP 1 id FROM sales WHERE invoice_number = ?", self.invoice_number)
            
#             # Insert sale items
#             cursor = connection.insertingtodatabase
#             item_sql = """
#             INSERT INTO sale_items (sale_id, product_name, quantity, price, total) 
#             VALUES (?, ?, ?, ?, ?)
#             """
#             for item in self.cart:
#                 cursor(item_sql, (sale_id, item['product'], item['quantity'], item['price'], item['total']))
            
#             # Clear cart
#             self.cart.clear()
#             self.update_cart_display()
#             self.customer_input.value = ''
#             self.payment_method_select.value = 'Cash'
#             self.currency_select.value = 'USD'
            
#             ui.notify(f'Sale completed! Invoice: {self.invoice_number}', type='positive')
            
#         except Exception as e:
#             ui.notify(f'Error completing sale: {str(e)}', type='negative')
    
#     def generate_invoice(self):
#         """Generate unique invoice number"""
#         return f"INV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    
#     def show_sales_history(self):
#         """Display sales history"""
#         with ui.dialog() as dialog, ui.card():
#             ui.label('Sales History').classes('text-h5')
            
#             try:
#                 sales = []
#                 cursor = connection.contogetrows
#                 cursor("""
#                     SELECT s.id, s.date, s.customer, s.total_amount, s.invoice_number,
#                            COUNT(si.id) as item_count
#                     FROM sales s
#                     LEFT JOIN sale_items si ON s.id = si.sale_id
#                     GROUP BY s.id, s.date, s.customer, s.total_amount, s.invoice_number
#                     ORDER BY s.date DESC
#                 """, sales)
                
#                 history_table = ui.table(
#                     columns=[
#                         {'name': 'date', 'label': 'Date', 'field': 'date'},
#                         {'name': 'customer', 'label': 'Customer', 'field': 'customer'},
#                         {'name': 'total', 'label': 'Total', 'field': 'total'},
#                         {'name': 'invoice', 'label': 'Invoice', 'field': 'invoice'},
#                         {'name': 'items', 'label': 'Items', 'field': 'items'}
#                     ],
#                     rows=[{
#                         'date': str(sale[1]),
#                         'customer': sale[2],
#                         'total': f"${sale[3]:.2f}",
#                         'invoice': sale[4],
#                         'items': sale[5]
#                     } for sale in sales],
#                     row_key='invoice'
#                 ).classes('w-full')
                
#                 ui.button('Close', on_click=dialog.close)
                
#             except Exception as e:
#                 ui.label(f'Error loading sales history: {str(e)}')
#                 ui.button('Close', on_click=dialog.close)





