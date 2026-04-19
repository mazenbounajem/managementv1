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
from color_palette import ColorPalette
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
        permissions = connection.get_user_permissions(user['role_id'])
        allowed_pages = {page for page, can_access in permissions.items() if can_access}

        if show_navigation:
            # Create enhanced navigation instance
            navigation = EnhancedNavigation(permissions, user)
            navigation.create_navigation_drawer()  # Create drawer first
            navigation.create_navigation_header()  # Then create header with toggle button

        self.max_sale_id = self.get_max_sale_id()

        self.currency_rows = []
        self.currency_exchange_rates = {}
        self.currency_symbols = {}
        self.default_currency_id = 1
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
            
            # Check if product has sufficient stock
            product_id = connection.getid('select id from products where product_name = ?', [product_name])
            stock_result = []
            connection.contogetrows(f"SELECT stock_quantity FROM products WHERE id = {product_id}", stock_result)
            
            if stock_result and stock_result[0][0] < quantity:
                ui.notify(f'Insufficient stock! Available: {stock_result[0][0]}, Requested: {quantity}')
                return
            
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
            
            # Add stock quantity for the product
            connection.insertingtodatabase("UPDATE products SET stock_quantity = stock_quantity + ? WHERE id = ?", (quantity, product_id))
            
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
        self.price_input.value = 0.0
    
    def clear_inputs(self):
        self.sales_aggrid.classes('dimmed')
        #ui.run_javascript(f'document.getElementById({self.sales_aggrid.id}).disabled = true;')
        self.customer_input.value = 'Cash Client'
        self.phone_input.value = ''
        self.barcode_input.value = ''
        self.product_input.value = ''
        self.quantity_input.value = 1
        self.discount_input.value = 0
        self.price_input.value = 0.0
        self.discount_percent_input.value = 0
        self.discount_amount_input.value = 0
        
        self.rows.clear()
        self.aggrid.options['rowData'] = self.rows
        self.aggrid.update()

        self.total_amount = 0
        self.subtotal_label.text = f"Subtotal: {self.get_current_currency_symbol()}0.00"
        self.total_label.text = f"Total: {self.get_current_currency_symbol()}0.00"
        
        self.current_sale_id = None
        self.new_mode=True
        
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
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-6xl glass p-6 border border-white/10').style('background: rgba(15, 15, 25, 0.8); backdrop-filter: blur(20px); border-radius: 2rem;'):
            ui.label('Inventory Catalog').classes('text-2xl font-black mb-6 text-white').style('font-family: "Outfit", sans-serif;')
            
            with ui.row().classes('w-full items-center gap-3 bg-white/5 px-4 py-2 rounded-xl border border-white/10 mb-4'):
                ui.icon('search', size='1.25rem').classes('text-purple-400')
                search_input = ui.input(placeholder='Search by name or barcode...').props('borderless dense').classes('flex-1 text-white text-sm').on('keydown.enter', lambda e: self.filter_product_rows(e.sender.value))
            
            headers = ['barcode', 'product_name', 'stock_quantity', 'price', 'cost_price']
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
                {'headerName': 'Barcode', 'field': 'barcode', 'width': 120},
                {'headerName': 'Product', 'field': 'product_name', 'flex': 1},
                {'headerName': 'Stock', 'field': 'stock_quantity', 'width': 100},
                {'headerName': 'Price', 'field': 'price', 'width': 100},
                {'headerName': 'Cost', 'field': 'cost_price', 'width': 100}
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

    def open_customer_dialog(self):
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-4xl glass p-6 border border-white/10').style('background: rgba(15, 15, 25, 0.8); backdrop-filter: blur(20px); border-radius: 2rem;'):
            ui.label('Select Customer').classes('text-2xl font-black mb-6 text-white').style('font-family: "Outfit", sans-serif;')
            
            with ui.row().classes('w-full items-center gap-3 bg-white/5 px-4 py-2 rounded-xl border border-white/10 mb-4'):
                ui.icon('search', size='1.25rem').classes('text-purple-400')
                search_input = ui.input(placeholder='Search by name or phone...').props('borderless dense').classes('flex-1 text-white text-sm').on('keydown.enter', lambda e: self.filter_customer_rows(e.sender.value))
            
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
                {'headerName': 'ID', 'field': 'id', 'width': 70},
                {'headerName': 'Name', 'field': 'customer_name', 'flex': 1},
                {'headerName': 'Phone', 'field': 'phone', 'width': 150},
                {'headerName': 'Balance', 'field': 'balance', 'width': 120}
            ]
            
            self.customer_grid = ui.aggrid({
                'columnDefs': columns,
                'rowData': self.customer_rows,
                'rowSelection': 'single',
                'domLayout': 'normal',
            }).classes('w-full h-80 ag-theme-quartz-dark shadow-inner').style('background: transparent; border: none;')
            
            self.customer_grid.on('cellClicked', lambda e: self.handle_customer_grid_click(e, dialog))
            
            with ui.row().classes('w-full justify-end mt-6'):
                ui.button('Cancel', on_click=dialog.close).props('flat text-color=white').classes('px-6 rounded-xl hover:bg-white/5')
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
            discount_percent = float(self.discount_percent_input.value or 0)
            discount_amount = float(self.discount_amount_input.value or 0)
            total_after_percent = subtotal * (1 - discount_percent / 100)
            final_total = total_after_percent - discount_amount

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
        self.customer_grid.options['rowData'] = filtered_rows
        self.customer_grid.update()

    def filter_product_rows(self, search_text):
        if not search_text:
            filtered_rows = self.product_rows
        else:
            filtered_rows = [row for row in self.product_rows if any(search_text.lower() in str(value).lower() for value in row.values())]
        self.product_grid.options['rowData'] = filtered_rows
        self.product_grid.update()

    def handle_customer_grid_click(self, e, dialog):
        try:
            row = e.args['data']
            self.customer_input.value = row['customer_name']
            self.phone_input.value = row['phone']
            dialog.close()
            ui.notify(f"Selected: {row['customer_name']}")
        except Exception as ex:
            ui.notify(f"Selection error: {ex}")
            dialog.close()

    def handle_product_grid_click(self, e, dialog):
        try:
            row = e.args['data']
            self.product_input.value = row['product_name']
            self.barcode_input.value = row['barcode']
            self.price_input.value = row['price']

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
            ui.notify(f"Added product: {row['product_name']}")
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
            total_ttc = (int(new_quantity) * float(new_price)) * (1 - float(new_discount) / 100)
            vat_amount = total_ttc * (vat_pct / 100)
            
            self.rows[row_index]['vat_percentage'] = vat_pct
            self.rows[row_index]['vat_amount'] = vat_amount
            self.rows[row_index]['subtotal'] = round(total_ttc, 2)
            
            self.total_amount = self.total_amount - old_subtotal + self.rows[row_index]['subtotal']
            self.update_totals()
            
            # Update stock quantity for the product (Sales Return: add back to stock)
            connection.insertingtodatabase("UPDATE products SET stock_quantity = stock_quantity - ? WHERE id = ?", (old_quantity, product_id))
            connection.insertingtodatabase("UPDATE products SET stock_quantity = stock_quantity + ? WHERE id = ?", (int(new_quantity), product_id))
            
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
            
            # Restore stock quantity for the product (Decrement since we are removing a return item)
            product_id = connection.getid('select id from products where product_name = ?', [row_data['product']])
            connection.insertingtodatabase("UPDATE products SET stock_quantity = stock_quantity - ? WHERE id = ?", (quantity_to_restore, product_id))
            
            del self.rows[row_index]
            self.aggrid.options['rowData'] = self.rows
            self.aggrid.update()
            
            dialog.close()
            ui.notify('Product removed successfully')
            
        except Exception as e:
            ui.notify(f'Error removing product: {str(e)}')

    def update_totals(self):
        total_quantity = sum(row['quantity'] for row in self.rows)
        total_vat = sum(row.get('vat_amount', 0) for row in self.rows)
        subtotal = sum(row['subtotal'] for row in self.rows)

        self.summary_label.text = f"{len(self.rows)} items"
        self.quantity_total_label.text = f"Total Qty: {total_quantity}"

        tax_percent = float(self.tax_percent_input.value or 0)
        tax_amount = float(self.tax_amount_input.value or 0)
        discount_percent = float(self.discount_percent_input.value or 0)
        discount_amount = float(self.discount_amount_input.value or 0)

        calculated_tax_amount = total_vat
        if tax_amount > 0:
            calculated_tax_amount = tax_amount

        total_after_tax = subtotal # subtotal is already sum of TTC items
        total_after_discount_percent = total_after_tax * (1 - discount_percent / 100)
        final_total = total_after_discount_percent - discount_amount

        # Get currency symbol
        selected_currency_id = self.currency_select.value
        currency_symbol = '$'
        for row in self.currency_rows:
            if row[0] == selected_currency_id:
                currency_symbol = row[2]
                break

        self.subtotal_label.text = f"Total HT: {currency_symbol}{subtotal - total_vat:.2f}"
        self.vat_label.text = f"Total VAT: {currency_symbol}{total_vat:.2f}"
        self.total_label.text = f"Total TTC: {currency_symbol}{final_total:.2f}"

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
                # Get the sale total and customer ID before deletion
                sale_data = []
                connection.contogetrows(
                    f"SELECT customer_id, total_amount FROM sales_returns WHERE id = {sale_id}",
                    sale_data
                )

                if sale_data:
                    customer_id = sale_data[0][0]
                    total_amount = float(sale_data[0][1])

                    # Delete sale items and sale
                    connection.deleterow("DELETE FROM sales_return_items WHERE sales_return_id = ?", [sale_id])
                    connection.deleterow("DELETE FROM sales_payment WHERE sales_return_id = ?", [sale_id])
                    
                    # Clean up accounting entries
                    jvs = []
                    connection.contogetrows("SELECT jv_id FROM accounting_transactions WHERE reference_type IN ('Sale', 'Sale Receipt') AND reference_id = ?", jvs, [str(sale_id)])
                    for jv in jvs:
                        connection.deleterow("DELETE FROM accounting_transaction_lines WHERE jv_id = ?", (jv[0],))
                        connection.deleterow("DELETE FROM accounting_transactions WHERE jv_id = ?", (jv[0],))
                        
                    connection.deleterow("DELETE FROM sales_returns WHERE id = ?", [sale_id])

                    # Reduce customer balance
                    if customer_id:
                        connection.insertingtodatabase(
                            "UPDATE customers SET balance = balance - ? WHERE id = ?",
                            (total_amount, customer_id)
                        )
                        ui.notify(f'Customer balance reduced by ${total_amount:.2f}')

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
                status = 'Order' if is_order else 'Sale'
                payment_status = 'pending' if is_order or payment_method != 'Cash' else 'completed'

                # Get current user for tracing
                user = session_storage.get('user')
                user_id = user.get('user_id') if user else None

                subtotal = sum(row['subtotal'] for row in self.rows)
                discount_percent = float(self.discount_percent_input.value or 0)
                discount_amount = float(self.discount_amount_input.value or 0)
                total_after_percent = subtotal * (1 - discount_percent / 100)
                final_total = total_after_percent - discount_amount

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
                        "SELECT payment_status, total_amount FROM sales_returns WHERE id = ?",
                        previous_sale_data,
                        (self.current_sale_id,)
                    )
                    previous_payment_status = previous_sale_data[0][0] if previous_sale_data else None
                    previous_total_amount = float(previous_sale_data[0][1]) if previous_sale_data else 0.0

                    # Reverse previous payment effects if payment method changed
                    if previous_payment_status != payment_status:
                        if previous_payment_status == 'completed':  # Previously Cash
                            # Reverse cash drawer operation (subtract previous amount)
                            user = session_storage.get('user')
                            user_id = user.get('user_id') if user else None
                            notes = f"Sale update reversal {self.current_sale_id}"
                            success = connection.update_cash_drawer_balance(previous_total_amount, 'Out', user_id, notes)
                            if success:
                                ui.notify(f'Reversed previous cash drawer operation of -${previous_total_amount:.2f}')
                            else:
                                ui.notify('Warning: Failed to reverse previous cash drawer operation', color='orange')
                        elif previous_payment_status == 'pending':  # Previously On Account
                            # Reverse customer balance (subtract previous amount)
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

                    for row in self.rows:
                        product_id = connection.getid('select id from products where product_name = ?', [row['product']])
                        barcode = row['barcode']
                        product_id_from_barcode = connection.getid('select id from products where barcode = ?', [barcode])
                        final_product_id = product_id_from_barcode or product_id

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
                    cust_res = []
                    connection.contogetrows("SELECT id, customer_name, auxiliary_number FROM customers WHERE id = ?", cust_res, (customer_id,))
                    customer_name = cust_res[0][1] if cust_res else "Cash Client"
                    customer_account = cust_res[0][2] if cust_res and cust_res[0][2] else '4111.000001'
                    
                    vat_account = accounting_helpers.ensure_vat_auxiliary('Customer', customer_id, customer_name, customer_account)

                    # REVERSED for Return: Debit Sales/VAT, Credit Customer
                    jv = [
                        {'account': customer_account, 'debit': 0, 'credit': normalized_total},
                        {'account': '7011.000001',    'debit': normalized_subtotal, 'credit': 0},
                        {'account': vat_account,      'debit': normalized_total_vat, 'credit': 0},
                    ]

                    accounting_helpers.save_accounting_transaction(
                        'Sale Return', self.current_sale_id, jv, description=f"Sale Return {self.invoicenumber}"
                    )
                    
                    if payment_method == 'Cash':
                        # REVERSED for Return: Debit Customer, Credit Cash
                        payment_jv = [
                            {'account': '5300.000001',    'debit': 0, 'credit': normalized_total},
                            {'account': customer_account, 'debit': normalized_total, 'credit': 0},
                        ]
                        accounting_helpers.save_accounting_transaction(
                            'Sale Return Receipt', self.current_sale_id, payment_jv, description=f"Cash Payment for Sale Return {self.invoicenumber}"
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
                        success = connection.update_cash_drawer_balance(normalized_total, 'In', session_storage.get('user')['user_id'], notes)
                        if success:
                            ui.notify(f'Cash payment recorded! Cash drawer updated by +${normalized_total:.2f}')
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
                        product_id = connection.getid('select id from products where product_name = ?', [row['product']])
                        barcode = row['barcode']
                        product_id_from_barcode = connection.getid('select id from products where barcode = ?', [barcode])
                        final_product_id = product_id_from_barcode or product_id

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
                    cust_res = []
                    connection.contogetrows("SELECT id, customer_name, auxiliary_number FROM customers WHERE id = ?", cust_res, (customer_id,))
                    customer_name = cust_res[0][1] if cust_res else "Cash Client"
                    customer_account = cust_res[0][2] if cust_res and cust_res[0][2] else '4111.000001'
                    
                    vat_account = accounting_helpers.ensure_vat_auxiliary('Customer', customer_id, customer_name, customer_account)

                    # REVERSED for Return: Debit Sales/VAT, Credit Customer
                    jv = [
                        {'account': customer_account, 'debit': 0, 'credit': normalized_total},
                        {'account': '7011.000001',    'debit': normalized_subtotal, 'credit': 0},
                        {'account': vat_account,      'debit': normalized_total_vat, 'credit': 0},
                    ]

                    accounting_helpers.save_accounting_transaction(
                        'Sale Return', last_sale_id, jv, description=f"Sale Return {invoice_number}"
                    )
                    
                    if payment_method == 'Cash':
                        # REVERSED for Return: Debit Customer, Credit Cash
                        payment_jv = [
                            {'account': '5300.000001',    'debit': 0, 'credit': normalized_total},
                            {'account': customer_account, 'debit': normalized_total, 'credit': 0},
                        ]
                        accounting_helpers.save_accounting_transaction(
                            'Sale Return Receipt', last_sale_id, payment_jv, description=f"Cash Payment for Sale Return {invoice_number}"
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

                await self.refresh_sales_table()
                await self.load_max_sale()
                self.sales_aggrid.classes(remove='dimmed')
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
                        f"SELECT s.id, s.sale_date, c.customer_name, s.total_amount, s.invoice_number, s.payment_status, s.currency_id FROM sales_returns s INNER JOIN customers c ON c.id = s.customer_id WHERE s.id = {max_id}",
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
                            'currency_id': sale_data[0][6]
                        }

                        # Update customer name input with the customer from the max sale
                        self.customer_input.value = row_data['customer_name']

                        # Set the current sale ID
                        self.current_sale_id = max_id

                        # Fetch related sale items using the max sale_id
                        sale_items_data = []
                        connection.contogetrows(
                            f"SELECT p.barcode, p.product_name, si.quantity, ISNULL(si.discount_amount, 0), si.unit_price, si.total_price, ISNULL(si.vat_percentage,0), ISNULL(si.vat_amount,0) FROM sales_return_items si INNER JOIN products p ON p.id = si.product_id WHERE si.sales_id = {max_id}",
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
        # Add global styles
        ui.add_head_html(MDS.get_global_styles())
        
        # Action buttons will be added inside the Invoice Editor panel (Right Side)

        with ui.element('div').classes('w-full mesh-gradient h-[calc(100vh-64px)] p-0 overflow-hidden'):
                    with ui.row().classes('w-full h-full gap-0 overflow-hidden'):
                        # --- MAIN CONTENT AREA ---
                        with ui.column().classes('flex-1 h-full p-4 gap-4 relative overflow-hidden'):
                            # --- TOP BAR: HEADER ---
                            with ui.row().classes('w-full justify-between items-center bg-white/5 p-4 rounded-3xl glass border border-white/10 mb-2'):
                                with ui.column().classes('gap-1'):
                                    ui.label('Commerce Engine').classes('text-xs font-black uppercase tracking-[0.2em] text-purple-400')
                                    ui.label('Sales Return Invoice').classes('text-3xl font-black text-white').style('font-family: "Outfit", sans-serif;')
                        
                                with ui.row().classes('gap-6 items-center'):
                                    # Date picker - compact
                                    with ui.row().classes('items-center gap-2 bg-white/5 px-4 py-2 rounded-xl border border-white/10'):
                                        ui.icon('event', size='1rem').classes('text-gray-400')
                                        self.date_input = ui.input(value=datetime.now().strftime('%Y-%m-%d')).props('borderless dense').classes('text-white text-xs font-bold w-24')
                            
                                    # Currency Select
                                    self.currency_select = ui.select(
                                        {row[0]: f"{row[2]} {row[1]}" for row in self.currency_rows}, 
                                        value=self.default_currency_id
                                    ).props('borderless dense').classes('glass px-4 py-2 rounded-xl text-white text-xs font-bold w-40').on('change', self.on_currency_change)

                            # --- MIDDLE SECTION: DUAL PANEL ---
                            with ui.row().classes('w-full flex-1 gap-6 overflow-hidden'):
                        
                                # LEFT PANEL: Sales History (35%)
                                with ui.column().classes('w-[35%] h-full gap-4'):
                                    with ui.column().classes('w-full h-full glass p-3 rounded-3xl border border-white/10'):
                                        # History Search Header (Modernized)
                                        with ui.row().classes('w-full items-center gap-3 glass p-3 rounded-2xl border border-white/10 hover:bg-white/5 transition-all'):
                                            ui.icon('history', size='1.25rem').classes('text-purple-400 ml-1')
                                            self.history_search = ui.input(placeholder='Search history...').props('borderless dense clearable dark')\
                                                .classes('flex-1 text-white font-bold')\
                                                .on_value_change(lambda e: self.filter_history_table(e.value))
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
                                            'pagination': True,
                                            'paginationPageSize': 15,
                                            'domLayout': 'normal',
                                        }).classes('w-full flex-1 ag-theme-quartz-dark shadow-inner').style('background: transparent; border: none; height: 100%;')
                                
                                        self.sales_aggrid.on('cellClicked', self.handle_sales_aggrid_click_wrapper)
                         
                       
                                # RIGHT PANEL: Invoice Editor (65%)
                                with ui.row().classes('flex-1 h-full gap-4 overflow-hidden'):
                                    # Column for Editor Content
                                    with ui.column().classes('flex-1 h-full gap-2 overflow-hidden'):
                                        # Customer & Payment Row
                                        with ui.row().classes('w-full glass p-4 rounded-3xl border border-white/10 gap-5 items-center'):
                                            with ui.column().classes('flex-1 gap-1'):
                                                ui.label('Customer Information').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                with ui.row().classes('items-center gap-3 bg-white/5 px-4 py-2 rounded-2xl border border-white/10 w-full hover:bg-white/10 transition-all cursor-pointer shadow-inner'):
                                                    ui.icon('person', size='1.25rem').classes('text-purple-400')
                                                    self.customer_input = ui.input(placeholder='Select Customer...').props('borderless dense dark').classes('flex-1 text-white font-black text-sm').on('click', self.open_customer_dialog)
                                                    ui.icon('search', size='1rem').classes('text-gray-500 opacity-50')

                                            with ui.column().classes('w-48 gap-1'):
                                                ui.label('Contact').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                with ui.row().classes('items-center gap-3 bg-white/5 px-4 py-2 rounded-2xl border border-white/10 w-full'):
                                                    ui.icon('phone', size='1.25rem').classes('text-gray-400 opacity-40')
                                                    self.phone_input = ui.input(placeholder='Phone').props('borderless dense dark').classes('flex-1 text-white font-bold text-sm')

                                            with ui.column().classes('gap-1'):
                                                ui.label('Payment').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                with ui.row().classes('items-center gap-2 bg-white/5 px-4 py-2 rounded-2xl border border-white/10 h-[44px]'):
                                                    self.payment_method = ui.radio(options=['Cash', 'On Account'], value='Cash').props('inline dark color=purple').classes('text-white text-[10px] font-black uppercase tracking-tighter')
                                        # Modern Product Entry Area
                                        with ui.row().classes('w-full glass p-4 rounded-3xl border border-white/10 gap-3 items-end mt-2'):
                                            with ui.column().classes('flex-[2] gap-1'):
                                                ui.label('Barcode').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                with ui.row().classes('items-center gap-3 bg-white/5 px-4 py-2 rounded-2xl border border-white/10 w-full'):
                                                    ui.icon('qr_code_scanner', size='1.25rem').classes('text-purple-400')
                                                    self.barcode_input = ui.input(placeholder='Scan or enter...').props('borderless dense dark').classes('flex-1 text-white font-bold').on('change', self.update_product_dropdown)
                                    
                                            with ui.column().classes('flex-[3] gap-1'):
                                                ui.label('Product').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4')
                                                with ui.row().classes('items-center gap-3 bg-white/5 px-4 py-2 rounded-2xl border border-white/10 w-full'):
                                                    ui.icon('inventory_2', size='1.25rem').classes('text-purple-400')
                                                    self.product_input = ui.input(placeholder='Select Product...').props('borderless dense dark').classes('flex-1 text-white font-bold').on('click', self.open_product_dialog)
                                    
                                            with ui.column().classes('w-20 gap-1'):
                                                ui.label('Qty').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4 text-center')
                                                with ui.row().classes('items-center gap-1 bg-white/5 px-2 py-2 rounded-2xl border border-white/10 w-full'):
                                                    self.quantity_input = ui.number(value=1).props('borderless dense dark').classes('w-full text-white font-black text-center')
                                    
                                            with ui.column().classes('w-28 gap-1'):
                                                ui.label('Price').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4 text-center')
                                                with ui.row().classes('items-center gap-1 bg-white/5 px-2 py-2 rounded-2xl border border-white/10 w-full'):
                                                    self.price_input = ui.number(value=0.0).props('borderless dense dark').classes('w-full text-white font-black text-center')

                                            with ui.column().classes('w-20 gap-1'):
                                                ui.label('Disc %').classes('text-[9px] font-black text-purple-400 uppercase tracking-widest ml-4 text-center')
                                                with ui.row().classes('items-center gap-1 bg-white/5 px-2 py-2 rounded-2xl border border-white/10 w-full'):
                                                    self.discount_input = ui.number(value=0).props('borderless dense dark').classes('w-full text-white font-black text-center')
                                    
                                            ui.button(icon='add', on_click=self.add_product).props('elevated round size=lg color=purple').classes('shadow-lg shadow-purple-500/30 hover:scale-110 transition-transform mb-1')

                       
                                        # Items Grid (Auto-filling Height)
                                        self.aggrid = ui.aggrid({
                                            'columnDefs': self.columns,
                                            'rowData': self.rows,
                                            'defaultColDef': {'flex': 1, 'minWidth': 40, 'sortable': True, 'filter': True},
                                            'rowSelection': 'single',
                                            'pagination': True,
                                            'paginationPageSize': 10,
                                            'domLayout': 'normal',
                                        }).classes('w-full ag-theme-quartz-dark shadow-inner').style('background: transparent; border: none; flex-grow: 1;')
                                        self.aggrid.on('cellClicked', self.handle_aggrid_click_wrapper)

                               
                                        # --- BOTTOM BAR: SUMMARY AND TOTALS (Subtotal + Metrics) ---
                                        with ui.row().classes('w-full glass p-4 rounded-3xl border border-white/10 items-center justify-between'):
                                            with ui.row().classes('gap-8 items-center'):
                                                ui.label('Inventory Pipeline').classes('text-[10px] font-black text-purple-400 uppercase tracking-widest opacity-50')
                                                ui.button('Profit Analytics', on_click=self.show_profit_dialog).props('flat rounded').classes('text-purple-400 font-bold uppercase tracking-wider text-xs')
                                        
                                                with ui.row().classes('items-center gap-6 bg-white/5 px-5 py-2 rounded-2xl border border-white/10'):
                                                    with ui.column().classes('gap-0'):
                                                        ui.label('Balance').classes('text-[9px] text-gray-400 font-bold uppercase tracking-tighter')
                                                        self.summary_label = ui.label('0 items').classes('text-sm font-black text-white')
                                            
                                                    with ui.column().classes('gap-0 border-l border-white/10 pl-6'):
                                                        ui.label('Velocity').classes('text-[9px] text-gray-400 font-bold uppercase tracking-tighter')
                                                        self.quantity_total_label = ui.label('Total Qty: 0').classes('text-sm font-black text-white')

                                            with ui.row().classes('gap-6 items-center'):
                                                with ui.column().classes('items-end gap-0'):
                                                    self.subtotal_label = ui.label('Base + VAT: $0.00').classes('text-[10px] font-bold text-gray-400 uppercase tracking-tighter')
                                                    self.vat_label = ui.label('VAT: $0.00').classes('text-[10px] font-black text-purple-400 uppercase tracking-tighter')
                                                    self.total_label = ui.label('Total: $0.00').classes('text-2xl font-black text-white px-2 rounded-lg bg-white/5')
                                        
                                                # Hidden inputs for math remains same
                                                with ui.element('div').classes('hidden'):
                                                    self.discount_percent_input = ui.number(value=0, on_change=self.update_totals).props('dense borderless').classes('hidden')
                                                    self.discount_amount_input = ui.number(value=0, on_change=self.update_totals).props('dense borderless').classes('hidden')
                                                    self.tax_amount_input = ui.number(value=0, on_change=self.update_totals).props('dense borderless').classes('hidden')
                                                    self.tax_percent_input = ui.number(value=0, on_change=self.update_totals).props('dense borderless').classes('hidden')
                            
                                    # Action Bar Panel (Right Side of Editor)
                                    with ui.column().classes('w-80px items-center'):
                                        from modern_ui_components import ModernActionBar
                                        ModernActionBar(
                                            on_new=self.clear_inputs,
                                            on_save=self.save_sale,
                                            on_undo=self.show_undo_confirmation,
                                            on_delete=self.delete_sale,
                                            on_print=self.print_sale_invoice,
                                            on_print_special=self.print_special_invoice,
                                            on_order=lambda: self.save_sale(is_order=True),
                                            on_chatgpt=lambda: ui.run_javascript('window.open("https://chatgpt.com", "_blank");'),
                                            on_view_transaction=self.view_sale_transactions,
                                            on_refresh=self.refresh_sales_table,
                                            button_class='h-16',
                                            classes=' '
                                        ).style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')
            
                    # Auto-load max sale and refresh table
                    ui.timer(0.1, self.load_max_sale, once=True)
                    ui.timer(0.2, self.refresh_sales_table, once=True)

    async def handle_sales_aggrid_click_wrapper(self, e):
        async with loading_indicator.show_loading('load_sale_items', 'Loading sale items...', overlay=True):
            try:
                selected_row = await self.sales_aggrid.get_selected_row()
                if selected_row and isinstance(selected_row, dict) and 'id' in selected_row:
                    sale_id = selected_row['id']
                    customer_name = selected_row['customer_name']
                    self.customer_input.value = customer_name
                    self.current_sale_id = sale_id
                    
                    sale_items_data = []
                    connection.contogetrows(
                        f"SELECT p.barcode, p.product_name, si.quantity, ISNULL(si.discount_amount, 0), si.unit_price, si.total_price, ISNULL(si.vat_percentage,0), ISNULL(si.vat_amount,0) FROM sales_return_items si INNER JOIN products p ON p.id = si.product_id WHERE si.sales_return_id = {sale_id}",
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

                    self.total_amount = sum(row['subtotal'] for row in self.rows)
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
