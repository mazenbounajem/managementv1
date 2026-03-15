from nicegui import ui
from pathlib import Path
from datetime import date as dt
from connection import connection
from datetime import datetime
from decimal import Decimal
from invoice_pdf_cairo import generate_sales_invoice_pdf
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
from loading_indicator import loading_indicator
from connection_cashdrawer import connection_cashdrawer
from color_palette import ColorPalette
import asyncio

@ui.page('/sales')
def sales_page_route():
    SalesUI()

class SalesUI:
    
    def __init__(self):
        self.invoicenumber = ''

        # Check if user is logged in
        user = session_storage.get('user')
        if not user:
            ui.notify('Please login to access this page', color='red')
            ui.run_javascript('window.location.href = "/login"')
            return

        # Get user permissions
        permissions = connection.get_user_permissions(user['role_id'])

        # Create enhanced navigation instance
        navigation = EnhancedNavigation(permissions, user)
        navigation.create_navigation_drawer()
        navigation.create_navigation_header()

        self.max_sale_id = self.get_max_sale_id()
        self.load_currencies()
        self.currency_id = 2  # Default to USD

        # --- Global Variables ---
        self.columns = [
            {'headerName': 'Barcode', 'field': 'barcode', 'width': 100, 'headerClass': 'blue-header'},
            {'headerName': 'Product', 'field': 'product', 'width': 150, 'headerClass': 'blue-header'},
            {'headerName': 'Qty', 'field': 'quantity', 'width': 60,  'headerClass': 'blue-header'},
            {'headerName': 'Discount', 'field': 'discount', 'width': 80,  'headerClass': 'blue-header'},
            {'headerName': 'Price', 'field': 'price', 'width': 80,  'headerClass': 'blue-header'},
            {'headerName': 'Subtotal', 'field': 'subtotal', 'width': 100,  'headerClass': 'blue-header'}
        ]
        self.customer_rows = []
        self.customer_grid = None
        self.product_rows = []
        self.product_grid = None
        self.rows = []
        self.total_amount = 0

        # Initialize UI
        self.create_ui()

    def calculate_subtotal(self, quantity, price, discount):
        return round((quantity * price) * (1 - discount / 100), 2)

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
            
            # Check if product has sufficient stock
            product_id = connection.getid('select id from products where product_name = ?', [product_name])
            stock_result = []
            connection.contogetrows(f"SELECT stock_quantity FROM products WHERE id = {product_id}", stock_result)
            
            if stock_result and stock_result[0][0] < quantity:
                ui.notify(f'Insufficient stock! Available: {stock_result[0][0]}, Requested: {quantity}')
                return
            
            subtotal = self.calculate_subtotal(quantity, price, discount)
            
            self.rows.append({
                'barcode': barcode,
                'product': product_name,
                'quantity': quantity,
                'discount': discount,
                'price': price,
                'subtotal': subtotal,
            })
            
            self.total_amount += subtotal
            self.total_label.text = f"Total: ${self.total_amount:.2f}"
            
            # Deduct stock quantity for the product
            connection.insertingtodatabase("UPDATE products SET stock_quantity = stock_quantity - ? WHERE id = ?", (quantity, product_id))
            
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
        self.customer_input.value = 'Cash Client'
        self.phone_input.value = ''
        self.rows.clear()
        self.aggrid.options['rowData'] = self.rows
        self.aggrid.update()
        self.total_amount = 0
        self.update_totals()
        self.current_sale_id = None
        self.currency_id = 2  # Reset to USD default
        if hasattr(self, 'currency_select'):
            self.currency_select.value = 2

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
                    ui.notify(f"Product loaded: {product[1]}")
                else:
                    ui.notify("Product not found for this barcode")
        except Exception as e:
            ui.notify(f'Error updating product: {str(e)}')

    def open_customer_dialog(self):
        self.customer_dialog.open()

    def open_product_dialog(self):
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-6xl').style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}'):
            ui.label('Select Product').classes('text-lg font-bold mb-4').style(f'color: {ColorPalette.MAIN_TEXT}')

            search_input = ui.input('Search').classes('text-xs mb-4').style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}; border: 1px solid {ColorPalette.BORDER_LIGHT}').on('keydown.enter', lambda e: self.filter_product_rows(e.sender.value))

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
            
            columns = [{'headerName': header, 'field': header, 'sortable': True, 'filter': True} for header in headers]
            self.product_grid = ui.aggrid({
                'columnDefs': columns,
                'rowData': self.product_rows,
                'domLayout': 'autoHeight'
            }).classes('w-full ag-theme-quartz-custom')

            self.product_grid.on('cellClicked', lambda e, d=dialog: self.handle_product_grid_click(e, d))

            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('Cancel', on_click=dialog.close).style(f'background-color: {ColorPalette.BUTTON_SECONDARY_BG}; color: {ColorPalette.BUTTON_SECONDARY_TEXT}')
        dialog.open()

    def open_edit_dialog(self, row_data):
        with ui.dialog() as dialog, ui.card().style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}'):
            ui.label('Edit Product').classes('text-lg font-bold mb-4').style(f'color: {ColorPalette.MAIN_TEXT}')
            with ui.column():
                quantity = ui.number('Quantity', value=row_data['quantity']).style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}; border: 1px solid {ColorPalette.BORDER_LIGHT}')
                discount = ui.number('Discount', value=row_data['discount']).style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}; border: 1px solid {ColorPalette.BORDER_LIGHT}')
                price = ui.number('Price', value=row_data['price']).style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}; border: 1px solid {ColorPalette.BORDER_LIGHT}')
                
                def save():
                    self.save_edited_row(row_data, quantity.value, discount.value, price.value, dialog)

                def delete():
                    self.delete_row(row_data, dialog)

                with ui.row().classes('w-full justify-end mt-4'):
                    ui.button('Save', on_click=save).style(f'background-color: {ColorPalette.SUCCESS}; color: white')
                    ui.button('Delete', on_click=delete).style(f'background-color: {ColorPalette.ERROR}; color: white')
                    ui.button('Cancel', on_click=dialog.close).style(f'background-color: {ColorPalette.BUTTON_SECONDARY_BG}; color: {ColorPalette.BUTTON_SECONDARY_TEXT}')
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
            self.rows[row_index]['subtotal'] = self.calculate_subtotal(
                int(new_quantity), 
                float(new_price), 
                float(new_discount)
            )
            
            # Update stock quantity for the product
            connection.insertingtodatabase("UPDATE products SET stock_quantity = stock_quantity + ? WHERE id = ?", (old_quantity, product_id))
            connection.insertingtodatabase("UPDATE products SET stock_quantity = stock_quantity - ? WHERE id = ?", (int(new_quantity), product_id))
            
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
            
            # Get the quantity to restore to stock
            quantity_to_restore = self.rows[row_index]['quantity']
            
            # Restore stock quantity for the product
            product_id = connection.getid('select id from products where product_name = ?', [row_data['product']])
            connection.insertingtodatabase("UPDATE products SET stock_quantity = stock_quantity + ? WHERE id = ?", (quantity_to_restore, product_id))
            
            del self.rows[row_index]
            self.aggrid.options['rowData'] = self.rows
            self.aggrid.update()
            self.update_totals()
            
            dialog.close()
            ui.notify('Product removed successfully')
            
        except Exception as e:
            ui.notify(f'Error removing product: {str(e)}')

    def update_totals(self):
        subtotal = sum(row['subtotal'] for row in self.rows)
        total_quantity = sum(row['quantity'] for row in self.rows)

        self.summary_label.text = f"{len(self.rows)} items"
        self.quantity_total_label.text = f"Total Qty: {total_quantity}"

        tax_percent = float(self.tax_percent_input.value or 0)
        tax_amount = float(self.tax_amount_input.value or 0)
        discount_percent = float(self.discount_percent_input.value or 0)
        discount_amount = float(self.discount_amount_input.value or 0)

        calculated_tax_amount = subtotal * (tax_percent / 100)
        if tax_amount > 0:
            calculated_tax_amount = tax_amount

        total_after_tax = subtotal + calculated_tax_amount
        total_after_discount_percent = total_after_tax * (1 - discount_percent / 100)
        final_total = total_after_discount_percent - discount_amount

        self.total_label.text = f"Total: ${max(0, round(final_total, 2)):.2f}"

    def get_max_sale_id(self):
        try:
            max_id_result = []
            connection.contogetrows("SELECT MAX(id) FROM sales", max_id_result)
            return max_id_result[0][0] if max_id_result and max_id_result[0][0] else 0
        except Exception as e:
            return 0

    def show_undo_confirmation(self):
        with ui.dialog() as dialog, ui.card().style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}'):
            ui.label('Confirm Action').classes('text-lg font-bold mb-4').style(f'color: {ColorPalette.MAIN_TEXT}')
            ui.label('Are you sure you want to undo all changes?').style(f'color: {ColorPalette.MAIN_TEXT}')
            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('Yes', on_click=lambda: self.perform_undo(dialog)).style(f'background-color: {ColorPalette.WARNING}; color: white')
                ui.button('No', on_click=dialog.close).style(f'background-color: {ColorPalette.BUTTON_SECONDARY_BG}; color: {ColorPalette.BUTTON_SECONDARY_TEXT}')
        dialog.open()

    def perform_undo(self, dialog):
        self.clear_inputs()
        dialog.close()
        ui.notify('Changes undone')

    def delete_sale(self):
        if not hasattr(self, 'current_sale_id') or not self.current_sale_id:
            ui.notify('No sale selected to delete', color='red')
            return
        
        try:
            # Get the sale total and customer ID before deletion
            sale_data = []
            connection.contogetrows(
                f"SELECT customer_id, total_amount FROM sales WHERE id = {self.current_sale_id}",
                sale_data
            )

            if sale_data:
                customer_id = sale_data[0][0]
                total_amount = float(sale_data[0][1])

                # Delete sale items and sale
                connection.deleterow("DELETE FROM sale_items WHERE sales_id = ?", [self.current_sale_id])
                connection.deleterow("DELETE FROM sales WHERE id = ?", [self.current_sale_id])

                # Reduce customer balance
                if customer_id:
                    connection.insertingtodatabase(
                        "UPDATE customers SET balance = balance - ? WHERE id = ?",
                        (total_amount, customer_id)
                    )

            ui.notify(f'Sale {self.current_sale_id} deleted successfully')
            self.refresh_sales_table()
            self.clear_inputs()

        except Exception as e:
            ui.notify(f'Error deleting sale: {str(e)}', color='red')

    async def refresh_sales_table(self):
        """Refresh sales table"""
        try:
            raw_sales_data = []
            connection.contogetrows(
                "SELECT s.id, s.sale_date, c.customer_name, s.total_amount, s.invoice_number, s.payment_status FROM sales s INNER JOIN customers c ON c.id = s.customer_id ORDER BY s.id DESC",
                raw_sales_data
            )

            sales_data = []
            for row in raw_sales_data:
                sales_data.append({
                    'id': row[0],
                    'sale_date': str(row[1]),
                    'customer_name': str(row[2]),
                    'total_amount': float(row[3]),
                    'invoice_number': str(row[4]),
                    'payment_status': str(row[5])
                })

            self.sales_aggrid.options['rowData'] = sales_data
            self.sales_aggrid.update()
            self.update_totals()

            ui.notify('Sales table refreshed successfully')

        except Exception as e:
            ui.notify(f'Error refreshing sales table: {str(e)}')

    async def save_sale(self):
        try:
            if not self.rows:
                ui.notify('No items to save!')
                return

            sale_date = str(self.date_input.value)
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            customer_name = self.customer_input.value or 'Cash Client'
            customer_id = connection.getid('select id from customers where customer_name = ?', [customer_name])

            payment_method = self.payment_method.value
            payment_status = 'completed' if payment_method == 'Cash' else 'pending'

            subtotal = sum(row['subtotal'] for row in self.rows)
            tax_percent = float(self.tax_percent_input.value or 0)
            tax_amount = float(self.tax_amount_input.value or 0)
            calculated_tax_amount = subtotal * (tax_percent / 100)
            if tax_amount > 0:
                calculated_tax_amount = tax_amount
            total_after_tax = subtotal + calculated_tax_amount
            discount_percent = float(self.discount_percent_input.value or 0)
            discount_amount = float(self.discount_amount_input.value or 0)
            total_after_discount_percent = total_after_tax * (1 - discount_percent / 100)
            final_total = total_after_discount_percent - discount_amount

            if hasattr(self, 'current_sale_id') and self.current_sale_id:
                sale_sql = """
                    UPDATE sales
                    SET sale_date = ?, customer_id = ?, subtotal = ?, discount_amount = ?,
                        total_amount = ?, created_at = ?, payment_status = ?
                    WHERE id = ?
                """
                sale_values = (sale_date, customer_id, subtotal, discount_amount, final_total, created_at, payment_status, self.current_sale_id)
                connection.insertingtodatabase(sale_sql, sale_values)

                connection.insertingtodatabase("DELETE FROM sale_items WHERE sales_id = ?", [self.current_sale_id])

                for row in self.rows:
                    product_id = connection.getid('select id from products where product_name = ?', [row['product']])
                    sale_item_sql = """
                        INSERT INTO sale_items (sales_id, barcode, product_id, quantity, unit_price, total_price, discount_amount)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """
                    sale_item_values = (
                        self.current_sale_id, row['barcode'], product_id,
                        row['quantity'], row['price'], row['subtotal'], row['discount']
                    )
                    connection.insertingtodatabase(sale_item_sql, sale_item_values)

                ui.notify(f'Sale updated successfully! ID: {self.current_sale_id}')
            else:
                invoice_number = self.generate_invoice_number()

                sale_sql = """
                    INSERT INTO sales (sale_date, customer_id, subtotal, discount_amount, total_amount, invoice_number, created_at, payment_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                sale_values = (sale_date, customer_id, subtotal, discount_amount, final_total, invoice_number, created_at, payment_status)
                connection.insertingtodatabase(sale_sql, sale_values)

                last_sale_id = connection.getid("SELECT MAX(id) FROM sales", [])

                for row in self.rows:
                    product_id = connection.getid('select id from products where product_name = ?', [row['product']])
                    sale_item_sql = """
                        INSERT INTO sale_items (sales_id, barcode, product_id, quantity, unit_price, total_price, discount_amount)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """
                    sale_item_values = (
                        last_sale_id, row['barcode'], product_id,
                        row['quantity'], row['price'], row['subtotal'], row['discount']
                    )
                    connection.insertingtodatabase(sale_item_sql, sale_item_values)

                ui.notify(f'Sale saved successfully! Invoice: {invoice_number}')

                if customer_id and payment_method == 'On Account':
                    # Update customer balance based on currency
                    if self.currency_id == 1:  # L.L.
                        connection.update_customerbalance(
                            "UPDATE customers SET balance_ll = balance_ll + ? WHERE id = ?",
                            (final_total, customer_id)
                        )
                    elif self.currency_id == 2:  # USD
                        connection.update_customerbalance(
                            "UPDATE customers SET balance_usd = balance_usd + ? WHERE id = ?",
                            (final_total, customer_id)
                        )
                    elif self.currency_id == 3:  # EUR
                        connection.update_customerbalance(
                            "UPDATE customers SET balance_eur = balance_eur + ? WHERE id = ?",
                            (final_total, customer_id)
                        )
                    else:
                        # Fallback to old balance column
                        connection.update_customerbalance(
                            "UPDATE customers SET balance = balance + ? WHERE id = ?",
                            (final_total, customer_id)
                        )
                elif payment_method == 'Cash':
                    user = session_storage.get('user')
                    notes = f"New sale {last_sale_id}"
                    connection.update_cash_drawer_balance(final_total, 'In', user['user_id'], notes)

            await self.refresh_sales_table()
        except Exception as e:
            ui.notify(f'Error saving sale: {str(e)}')

    def print_sale_invoice(self):
        if not hasattr(self, 'current_sale_id') or not self.current_sale_id:
            ui.notify('No sale selected to print', color='red')
            return
        try:
            # Get invoice data and generate PDF
            ui.notify('Printing invoice...')
        except Exception as e:
            ui.notify(f'Error printing invoice: {e}', color='red')

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
        row = e.args['data']
        self.customer_input.value = row['customer_name']
        self.phone_input.value = row['phone']
        dialog.close()

    def handle_product_grid_click(self, e, dialog):
        row = e.args['data']
        def update_inputs():
            self.product_input.value = row['product_name']
            self.barcode_input.value = row['barcode']
            self.price_input.value = row['price']
        dialog.close()
        ui.timer(0.01, update_inputs, once=True)

    def create_ui(self):
        uiAggridTheme.addingtheme()
        with ui.element('div').classes('flex w-full h-screen'):
            with ui.element('div').classes(f'w-12 p-1 flex flex-col gap-1').style(f'background-color: {ColorPalette.SECONDARY}'):
                ui.button('', icon='add', on_click=self.clear_inputs).classes('w-6 h-6 mb-2').style(f'background-color: {ColorPalette.BUTTON_PRIMARY_BG}; color: {ColorPalette.BUTTON_PRIMARY_TEXT}').tooltip('Add new sale')
                ui.button('', icon='save', on_click=self.save_sale).classes('w-6 h-6 mb-2').style(f'background-color: {ColorPalette.SUCCESS}; color: white').tooltip('Save sale')
                ui.button('', icon='undo', on_click=self.show_undo_confirmation).classes('w-6 h-6 mb-2').style(f'background-color: {ColorPalette.ACCENT}; color: {ColorPalette.MAIN_TEXT}').tooltip('Undo changes')
                ui.button('', icon='delete', on_click=self.delete_sale).classes('w-6 h-6 mb-2').style(f'background-color: {ColorPalette.ERROR}; color: white').tooltip('Delete sale')
                ui.button('', icon='refresh', on_click=self.refresh_sales_table).classes('w-6 h-6 mb-2').style(f'background-color: {ColorPalette.BUTTON_SECONDARY_BG}; color: {ColorPalette.BUTTON_SECONDARY_TEXT}').tooltip('Refresh table')
                ui.button('', icon='print', on_click=self.print_sale_invoice).classes('w-6 h-6 mb-2').style(f'background-color: {ColorPalette.BUTTON_PRIMARY_BG}; color: {ColorPalette.BUTTON_PRIMARY_TEXT}').tooltip('Print invoice')

            with ui.element('div').classes('flex-1 p-1 flex flex-col').style(f'background-color: {ColorPalette.MAIN_BG}'):
                ui.label('Sales History').classes('text-sm font-bold mb-1').style(f'color: {ColorPalette.MAIN_TEXT}')

                with ui.splitter(horizontal=True, value=30).classes('w-full flex-grow') as main_splitter:
                    with main_splitter.before:
                        sales_columns = [
                            {'headerName': 'ID', 'field': 'id', 'width': 40, 'filter': True, 'headerClass': 'blue-header'},
                            {'headerName': 'Date', 'field': 'sale_date', 'width': 70, 'filter': True, 'headerClass': 'blue-header'},
                            {'headerName': 'Customer', 'field': 'customer_name', 'width': 100, 'filter': True, 'headerClass': 'blue-header'},
                            {'headerName': 'Total', 'field': 'total_amount', 'width': 60,  'filter': True, 'headerClass': 'blue-header'},
                            {'headerName': 'Invoice', 'field': 'invoice_number', 'width': 80, 'filter': True, 'headerClass': 'blue-header'},
                            {'headerName': 'Status', 'field': 'payment_status', 'width': 60, 'filter': True, 'headerClass': 'blue-header'}
                        ]

                        raw_sales_data = []
                        connection.contogetrows(
                            "SELECT s.id, s.sale_date, c.customer_name, s.total_amount, s.invoice_number, s.payment_status FROM sales s INNER JOIN customers c ON c.id = s.customer_id ORDER BY s.id DESC",
                            raw_sales_data
                        )

                        sales_data = []
                        for row in raw_sales_data:
                            sales_data.append({
                                'id': row[0],
                                'sale_date': str(row[1]),
                                'customer_name': str(row[2]),
                                'total_amount': float(row[3]),
                                'invoice_number': str(row[4]),
                                'payment_status': str(row[5])
                            })

                        self.sales_aggrid = ui.aggrid({
                            'columnDefs': sales_columns,
                            'rowData': sales_data,
                            'defaultColDef': {'flex': 1, 'minWidth': 30, 'sortable': True, 'resizable': True},
                            'domLayout': 'autoHeight'
                        }).classes('w-full ag-theme-quartz-custom')

                        self.sales_aggrid.on('cellClicked', self.handle_sales_grid_click)

                    with main_splitter.after:
                        with ui.column().classes('w-full gap-2'):
                            # Date and Customer Row
                            with ui.row().classes('w-full gap-2'):
                                self.date_input = ui.date(value=dt.today()).classes('flex-1').style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}; border: 1px solid {ColorPalette.BORDER_LIGHT}')
                                with ui.row().classes('gap-1 flex-1'):
                                    self.customer_input = ui.input('Customer').classes('flex-1').style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}; border: 1px solid {ColorPalette.BORDER_LIGHT}')
                                    ui.button('', icon='search', on_click=self.open_customer_dialog).classes('w-8').style(f'background-color: {ColorPalette.BUTTON_SECONDARY_BG}; color: {ColorPalette.BUTTON_SECONDARY_TEXT}')
                                self.phone_input = ui.input('Phone').classes('flex-1').style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}; border: 1px solid {ColorPalette.BORDER_LIGHT}')

                            # Barcode and Product Row
                            with ui.row().classes('w-full gap-2'):
                                self.barcode_input = ui.input('Barcode').classes('flex-1').style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}; border: 1px solid {ColorPalette.BORDER_LIGHT}').on('keydown.enter', self.update_product_dropdown)
                                with ui.row().classes('gap-1 flex-1'):
                                    self.product_input = ui.input('Product').classes('flex-1').style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}; border: 1px solid {ColorPalette.BORDER_LIGHT}')
                                    ui.button('', icon='search', on_click=self.open_product_dialog).classes('w-8').style(f'background-color: {ColorPalette.BUTTON_SECONDARY_BG}; color: {ColorPalette.BUTTON_SECONDARY_TEXT}')
                                self.quantity_input = ui.number('Qty', value=1, min=1).classes('w-20').style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}; border: 1px solid {ColorPalette.BORDER_LIGHT}')

                            # Price and Discount Row
                            with ui.row().classes('w-full gap-2'):
                                self.price_input = ui.number('Price', format='%.2f').classes('flex-1').style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}; border: 1px solid {ColorPalette.BORDER_LIGHT}')
                                self.discount_input = ui.number('Discount %', min=0, max=100).classes('flex-1').style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}; border: 1px solid {ColorPalette.BORDER_LIGHT}')
                                ui.button('Add', on_click=self.add_product).classes('w-20').style(f'background-color: {ColorPalette.SUCCESS}; color: white')

                            # Products Grid
                            self.aggrid = ui.aggrid({
                                'columnDefs': self.columns,
                                'rowData': self.rows,
                                'domLayout': 'autoHeight'
                            }).classes('w-full ag-theme-quartz-custom')

                            self.aggrid.on('cellClicked', self.open_edit_dialog)

                            # Summary Row
                            with ui.row().classes('w-full justify-between items-center mt-2'):
                                self.summary_label = ui.label('0 items').classes('text-sm').style(f'color: {ColorPalette.MAIN_TEXT}')
                                self.quantity_total_label = ui.label('Total Qty: 0').classes('text-sm').style(f'color: {ColorPalette.MAIN_TEXT}')
                                self.total_label = ui.label('Total: $0.00').classes('text-lg font-bold').style(f'color: {ColorPalette.MAIN_TEXT}')

                            # Tax and Discount Row
                            with ui.row().classes('w-full gap-2'):
                                self.tax_percent_input = ui.number('Tax %', min=0).classes('flex-1').style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}; border: 1px solid {ColorPalette.BORDER_LIGHT}').on('value', self.update_totals)
                                self.tax_amount_input = ui.number('Tax Amount', min=0).classes('flex-1').style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}; border: 1px solid {ColorPalette.BORDER_LIGHT}').on('value', self.update_totals)
                                self.discount_percent_input = ui.number('Discount %', min=0, max=100).classes('flex-1').style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}; border: 1px solid {ColorPalette.BORDER_LIGHT}').on('value', self.update_totals)
                                self.discount_amount_input = ui.number('Discount Amount', min=0).classes('flex-1').style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}; border: 1px solid {ColorPalette.BORDER_LIGHT}').on('value', self.update_totals)

                            # Payment Row
                            with ui.row().classes('w-full gap-2'):
                                self.payment_method = ui.select(['Cash', 'On Account'], value='Cash').classes('flex-1').style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}; border: 1px solid {ColorPalette.BORDER_LIGHT}')
                                self.currency_select = ui.select({row[0]: f"{row[1]} ({row[2]})" for row in self.currency_rows}, value=self.currency_id).classes('flex-1').style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}; border: 1px solid {ColorPalette.BORDER_LIGHT}').on('value', lambda e: setattr(self, 'currency_id', e.value))

                # Customer Dialog
                self.customer_dialog = ui.dialog()
                with self.customer_dialog, ui.card().classes('w-full max-w-6xl').style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}'):
                    ui.label('Select Customer').classes('text-lg font-bold mb-4').style(f'color: {ColorPalette.MAIN_TEXT}')

                    search_input = ui.input('Search').classes('text-xs mb-4').style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}; border: 1px solid {ColorPalette.BORDER_LIGHT}').on('keydown.enter', lambda e: self.filter_customer_rows(e.sender.value))

                    headers = []
                    connection.contogetheaders("SELECT id, customer_name, phone, balance_ll, balance_usd, balance_eur FROM customers", headers)

                    # Custom labels for better display
                    column_labels = {
                        'id': 'ID',
                        'customer_name': 'Customer Name',
                        'phone': 'Phone',
                        'balance_ll': 'Balance LL',
                        'balance_usd': 'Balance USD',
                        'balance_eur': 'Balance EUR'
                    }
                    columns = [{'name': header, 'label': column_labels.get(header, header.title()), 'field': header, 'sortable': True} for header in headers]

                    data = []
                    connection.contogetrows("SELECT id, customer_name, phone, balance_ll, balance_usd, balance_eur FROM customers", data)
                    rows = []
                    for row in data:
                        row_dict = {}
                        for i, header in enumerate(headers):
                            row_dict[header] = row[i]
                        rows.append(row_dict)

                    table = ui.table(columns=columns, rows=rows, pagination=5).classes('w-full')
                    ui.input('Search').bind_value(table, 'filter').classes('text-xs')

                    def on_row_click(row_data):
                        selected_row = row_data.args[1]
                        self.customer_input.value = selected_row['customer_name']
                        self.phone_input.value = selected_row['phone']
                        self.customer_dialog.close()

                    table.on('rowClick', on_row_click)

    def handle_sales_grid_click(self, e):
        row = e.args['data']
        self.current_sale_id = row['id']
        # Load sale details
        sale_data = []
        connection.contogetrows(f"SELECT * FROM sales WHERE id = {self.current_sale_id}", sale_data)
        if sale_data:
            sale = sale_data[0]
            self.date_input.value = dt.fromisoformat(str(sale[1]))  # sale_date
            customer_id = sale[2]  # customer_id
            if customer_id:
                customer_data = []
                connection.contogetrows(f"SELECT customer_name, phone FROM customers WHERE id = {customer_id}", customer_data)
                if customer_data:
                    self.customer_input.value = customer_data[0][0]
                    self.phone_input.value = customer_data[0][1]

            # Load sale items
            sale_items = []
            connection.contogetrows(f"SELECT si.barcode, p.product_name, si.quantity, si.unit_price, si.discount_amount, si.total_price FROM sale_items si JOIN products p ON si.product_id = p.id WHERE si.sales_id = {self.current_sale_id}", sale_items)
            self.rows = []
            for item in sale_items:
                self.rows.append({
                    'barcode': item[0],
                    'product': item[1],
                    'quantity': item[2],
                    'price': item[3],
                    'discount': item[4],
                    'subtotal': item[5]
                })
            self.aggrid.options['rowData'] = self.rows
            self.aggrid.update()
            self.update_totals()
            ui.notify(f'Sale {self.current_sale_id} loaded for editing')
