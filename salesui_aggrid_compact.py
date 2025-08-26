from nicegui import ui
from pathlib import Path
from datetime import date as dt
from connection import connection
from datetime import datetime
from decimal import Decimal
from invoice_pdf_cairo import generate_sales_invoice_pdf
from uiaggridtheme import uiAggridTheme
class SalesUI:
    
    def __init__(self):
        self.invoicenumber = ''
        with ui.header().classes('items-center justify-between'):
            ui.label('Sales Management').classes('text-2xl font-bold')
            ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).props('flat color=white')
            self.max_sale_id = self.get_max_sale_id()

        # --- Global Variables ---
        self.columns = [
            {'headerName': 'Barcode', 'field': 'barcode', 'width': 100, 'headerClass': 'green-header'},
            {'headerName': 'Product', 'field': 'product', 'width': 150, 'headerClass': 'green-header'},
            {'headerName': 'Qty', 'field': 'quantity', 'width': 60,  'headerClass': 'green-header'},
            {'headerName': 'Discount', 'field': 'discount', 'width': 80,  'headerClass': 'green-header'},
            {'headerName': 'Price', 'field': 'price', 'width': 80,  'headerClass': 'green-header'},
            {'headerName': 'Subtotal', 'field': 'subtotal', 'width': 100,  'headerClass': 'green-header'}
        ]
        self.rows = []
        self.total_amount = 0
        self.total_quantity = 0
        self.total_items = 0
        self.grid_readonly = False  # Track grid state
        self.new_mode = False  # Track new mode state

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
        self.subtotal_label.text = "Subtotal: $0.00"
        self.total_label.text = "Total: $0.00"
        
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
        dialog = ui.dialog()
        
        with dialog, ui.card().classes('w-full'):
            ui.label('Select Product').classes('text-xl font-bold mb-4')
            
            headers = []
            connection.contogetheaders("SELECT barcode, product_name, stock_quantity, price, cost_price FROM products", headers)
            columns = [{'name': header, 'label': header.title(), 'field': header, 'sortable': True} for header in headers]
            
            # Fetch data from database
            data = []
            connection.contogetrows("SELECT barcode, product_name, stock_quantity, price, cost_price FROM products", data)
            rows = []
            for row in data:
                row_dict = {}
                for i, header in enumerate(headers):
                    row_dict[header] = row[i]
                rows.append(row_dict)
            
            table = ui.table(columns=columns, rows=rows, pagination=5).classes('w-full text-xs')
            ui.input('Search').bind_value(table, 'filter').classes('text-xs')
            
            def on_row_click(row_data):
                selected_row = row_data.args[1]
                self.product_input.value = selected_row['product_name']
                self.barcode_input.value = selected_row['barcode']
                self.price_input.value = selected_row['price']
                self.cost_input.value = selected_row['cost_price']  # Display cost
                self.product_dialog.close()
            
            table.on('rowClick', on_row_click)
        
        dialog.open()

    def show_profit_dialog(self):
        """Calculate and display profit in a dialog using database query."""
        try:
            sale_id = None
            
            # Determine which sale ID to use
            if hasattr(self, 'current_sale_id') and self.current_sale_id:
                sale_id = self.current_sale_id
            elif self.rows:
                # If we have items but no current sale ID, use max sale ID
                sale_id = self.get_max_sale_id()
            
            if not sale_id:
                ui.notify('No sale data available to calculate profit')
                return
            
            # Execute the profit calculation query
            
            profit_data = connection.getprofit(f"select sum(((unit_price-products.cost_price)*(quantity))-discount_amount) as profit from sale_items right join products on products.id=product_id where sale_items.sales_id='{sale_id}'")
            
            
            
            # Calculate profit percentage
            profitpercentage=(Decimal(profit_data[0]) / Decimal(self.total_amount))*100 
            
            
            
            # Display the profit dialog
            profit_dialog = ui.dialog()
            with profit_dialog, ui.card().classes('w-80'):
                ui.label('💰 Profit Analysis').classes('text-xl font-bold mb-4 text-center text-green-600')
                
                with ui.column().classes('w-full gap-3'):
                    ui.label(f'Sale ID: {sale_id}').classes('text-sm text-gray-600')
                    ui.label(f'Profit Data:{profit_data[0]}').classes('text-sm text-gray-600')
                    ui.label(f'profit Percentage: {round(profitpercentage,2)}').classes('text-sm text-gray-600')
                    
                    ui.separator()
                    
                    #ui.label(f'Total Sale Amount: ${total_amount:.2f}').classes('text-lg font-semibold')
                    #ui.label(f'Calculated Profit: ${calculated_profit:.2f}').classes('text-2xl font-bold text-green-600')
                   # ui.label(f'Profit Margin: {profit_percentage:.2f}%').classes('text-lg text-blue-600')
                
                with ui.row().classes('w-full justify-center mt-4'):
                    ui.button('Close', on_click=profit_dialog.close).props('color=primary')
            
            profit_dialog.open()
            
        except Exception as e:
            ui.notify(f'Error calculating profit: {str(e)}')
            print(f'Profit calculation error: {str(e)}')
    def print_invoice(self):
        """Generate and print invoice PDF from current sale data"""
        try:
            if not self.rows:
                ui.notify('No items to print!')
                return
            
            # Generate invoice number if not exists
            invoice_number = self.invoicenumber or self.generate_invoice_number()
            
            # Prepare invoice data
            invoice_data = {
                'invoice_number': invoice_number,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'customer_name': self.customer_input.value or 'Cash Client',
                'customer_phone': self.phone_input.value or '',
                'total_amount': self.total_amount,
                'subtotal': self.total_amount,  # Simplified for now
                'items': self.rows
            }
            
            # Generate PDF
            pdf_buffer = generate_sales_invoice_pdf(self.rows, 
                                                  self.customer_input.value or 'Cash Client',
                                                  invoice_number,
                                                  self.total_amount)
            
            # Save PDF to file
            filename = f"invoice_{invoice_number}.pdf"
            with open(filename, 'wb') as f:
                f.write(pdf_buffer.getvalue())
            
            ui.notify(f'Invoice generated: {filename}')
            
            # Update invoice number if it was generated
            if not self.invoicenumber:
                self.invoicenumber = invoice_number
            
            # Open PDF file (Windows)
            import os
            if os.name == 'nt':  # Windows
                os.startfile(filename)
            else:  # macOS and Linux
                os.system(f'open "{filename}"' if os.name == 'posix' else f'xdg-open "{filename}"')
                
        except Exception as e:
            ui.notify(f'Error generating invoice: {str(e)}')
            print(f'Print invoice error: {str(e)}')
   
    
                            
    def open_edit_dialog(self, row_data):
        dialog = ui.dialog()
        
        with dialog, ui.card().classes('w-96 p-6'):
            ui.label('Edit Product').classes('text-xl font-bold mb-4')
            
            with ui.column().classes('w-full gap-3'):
                ui.label(f"Barcode: {row_data['barcode']}").classes('font-medium')
                ui.label(f"Product: {row_data['product']}").classes('font-medium')
                
                quantity_input = ui.number('Quantity', value=row_data['quantity'], min=1)
                discount_input = ui.number('Discount %', value=row_data['discount'], min=0, max=100)
                price_input = ui.number('Price', value=row_data['price'], min=0, step=0.01)
                
                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button('Cancel', on_click=dialog.close)
                    ui.button('Delete', on_click=lambda: self.delete_row(row_data, dialog)).props('color=negative')
                    ui.button('Save', on_click=lambda: self.save_edited_row(
                        row_data, 
                        quantity_input.value, 
                        discount_input.value, 
                        price_input.value,
                        dialog
                    )).props('color=primary')
        
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
            
            self.total_amount = self.total_amount - old_subtotal + self.rows[row_index]['subtotal']
            self.total_label.text = f"Total: ${self.total_amount:.2f}"
            
            # Update stock quantity for the product
            connection.insertingtodatabase("UPDATE products SET stock_quantity = stock_quantity + ? WHERE id = ?", (old_quantity, product_id))
            connection.insertingtodatabase("UPDATE products SET stock_quantity = stock_quantity - ? WHERE id = ?", (int(new_quantity), product_id))
            
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
            self.total_label.text = f"Total: ${self.total_amount:.2f}"
            
            # Restore stock quantity for the product
            product_id = connection.getid('select id from products where product_name = ?', [row_data['product']])
            connection.insertingtodatabase("UPDATE products SET stock_quantity = stock_quantity + ? WHERE id = ?", (quantity_to_restore, product_id))
            
            del self.rows[row_index]
            self.aggrid.options['rowData'] = self.rows
            self.aggrid.update()
            
            dialog.close()
            ui.notify('Product removed successfully')
            
        except Exception as e:
            ui.notify(f'Error removing product: {str(e)}')

    def update_totals(self):
        subtotal = sum(row['subtotal'] for row in self.rows)
        total_quantity = sum(row['quantity'] for row in self.rows)
        
        # Update summary labels with row count and quantity
        
        self.summary_label.text = f"{len(self.rows)} items"
        self.quantity_total_label.text = f"Total Qty: {total_quantity}"
        
        # Fix subtotal calculation - when no discount, subtotal equals total
        discount_percent = float(self.discount_percent_input.value or 0)
        discount_amount = float(self.discount_amount_input.value or 0)
        
        if discount_percent == 0 and discount_amount == 0:
            # No discount applied, subtotal equals total
            self.subtotal_label.text = f"${subtotal:.2f}"
            final_total = subtotal
        else:
            # Discount applied, calculate properly
            total_after_percent = subtotal * (1 - discount_percent / 100)
            final_total = total_after_percent - discount_amount
            self.subtotal_label.text = f"${subtotal:.2f}"
        
        self.total_label.text = f"${max(0, round(final_total, 2)):.2f}"

    def get_max_sale_id(self):
        try:
            max_id_result = []
            connection.contogetrows("SELECT MAX(id) FROM sales", max_id_result)
            return max_id_result[0][0] if max_id_result and max_id_result[0][0] else 0
        except Exception as e:
            return 0

    def show_undo_confirmation(self):
        
        dialog = ui.dialog()
        
        with dialog, ui.card().classes('w-96 p-6'):
            ui.label('Confirm Undo').classes('text-xl font-bold mb-4')
            ui.label('Are you sure you want to undo all changes?').classes('mb-4')
            
            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('Cancel', on_click=dialog.close)
                ui.button('OK', on_click=lambda: self.perform_undo(dialog)).props('color=primary')
        
        dialog.open()

    def show_delete_confirmation(self):
        dialog = ui.dialog()
        
        with dialog, ui.card().classes('w-96 p-6'):
            ui.label('Confirm Delete').classes('text-xl font-bold mb-4')
            
            if hasattr(self, 'current_sale_id') and self.current_sale_id:
                ui.label(f'Are you sure you want to delete sale ID: {self.current_sale_id}?').classes('mb-4')
                ui.label('This will remove the sale and all its items from the database.').classes('text-sm text-gray-600 mb-4')
                
                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button('Cancel', on_click=dialog.close)
                    ui.button('Delete', on_click=lambda: self.perform_delete(dialog)).props('color=negative')
            else:
                ui.label('No sale selected for deletion.').classes('mb-4')
                ui.label('Please select a sale from the table first.').classes('text-sm text-gray-600 mb-4')
                
                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button('OK', on_click=dialog.close).props('color=primary')
        
        dialog.open()

    def delete_sale(self):
        """Show confirmation dialog before deleting a sale"""
        try:
            sale_id = None
            
            # Determine which sale ID to use
            if hasattr(self, 'current_sale_id') and self.current_sale_id:
                sale_id = self.current_sale_id
            elif self.rows:
                # If we have items but no current sale ID, use max sale ID
                sale_id = self.get_max_sale_id()
            
            if not sale_id:
                ui.notify('No sale data available to delete')
                return
            
            # Create confirmation dialog
            dialog = ui.dialog()
            
            with dialog, ui.card().classes('w-96 p-6'):
                ui.label('Confirm Delete').classes('text-xl font-bold mb-4 text-red-600')
                ui.label(f'Are you sure you want to delete sale ID: {sale_id}?').classes('mb-2')
                ui.label('This will permanently remove the sale and all its items from the database.').classes('text-sm text-gray-600 mb-4')
                
                with ui.row().classes('w-full justify-end gap-3 mt-6'):
                    ui.button('No', on_click=dialog.close).props('flat')
                    ui.button('Yes, Delete', on_click=lambda: self.perform_delete_sale(sale_id, dialog)).props('color=negative')
            
            dialog.open()
            
        except Exception as e:
            ui.notify(f'Error preparing delete: {str(e)}')

    def perform_delete_sale(self, sale_id, dialog):
        """Perform the actual deletion after confirmation"""
        try:
            # Get the sale total and customer ID before deletion
            sale_data = []
            connection.contogetrows(
                f"SELECT customer_id, total_amount FROM sales WHERE id = {sale_id}", 
                sale_data
            )
            
            if sale_data:
                customer_id = sale_data[0][0]
                total_amount = float(sale_data[0][1])
                
                # Delete sale items and sale
                connection.deleterow("DELETE FROM sale_items WHERE sales_id = ?", [sale_id])
                connection.deleterow("DELETE FROM sales WHERE id = ?", [sale_id])
                
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
            self.refresh_sales_table()
            
        except Exception as e:
            ui.notify(f'Error deleting sale: {str(e)}')
            dialog.close()

    def perform_undo(self, dialog):
        
        self.rows.clear()
        self.aggrid.options['rowData'] = self.rows
        self.aggrid.update()
        
        self.total_amount = 0
        self.subtotal_label.text = "Subtotal: $0.00"
        self.total_label.text = "Total: $0.00"
        
        self.clear_inputs()
        dialog.close()
        self.sales_aggrid.classes(remove='dimmed')
        ui.notify('Undo completed successfully')

    def refresh_sales_table(self):
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
            
            # Update the sales_aggrid with fresh data
            self.sales_aggrid.options['rowData'] = sales_data
            self.sales_aggrid.update()
            self.sales_aggrid.classes(remove='dimmed')
            # Update totals after refresh
            self.update_totals()
            
            ui.notify('Sales table refreshed successfully')
            
        except Exception as e:
            ui.notify(f'Error refreshing sales table: {str(e)}')

    def save_sale(self):
        
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
            payment_status = 'completed' if payment_method == 'Cash' else 'pending'
            
            subtotal = sum(row['subtotal'] for row in self.rows)
            discount_percent = float(self.discount_percent_input.value or 0)
            discount_amount = float(self.discount_amount_input.value or 0)
            total_after_percent = subtotal * (1 - discount_percent / 100)
            final_total = total_after_percent - discount_amount
            
            if hasattr(self, 'current_sale_id') and self.current_sale_id:
                sale_sql = """
                    UPDATE sales 
                    SET sale_date = ?, customer_id = ?, subtotal = ?, discount_amount = ?, 
                        total_amount = ?, created_at = ?, payment_status = ?
                    WHERE id = ?
                """
                sale_values = (sale_date, customer_id, subtotal, discount_amount, final_total, created_at, payment_status, self.current_sale_id)
                connection.insertingtodatabase(sale_sql, sale_values)
                
                delete_items_sql = "DELETE FROM sale_items WHERE sales_id = ?"
                connection.insertingtodatabase(delete_items_sql, [self.current_sale_id])
                
                for row in self.rows:
                    product_id = connection.getid('select id from products where product_name = ?', [row['product']])
                    barcode = row['barcode']
                    product_id_from_barcode = connection.getid('select id from products where barcode = ?', [barcode])
                    final_product_id = product_id_from_barcode or product_id
                    
                    sale_item_sql = """
                        INSERT INTO sale_items (sales_id, barcode, product_id, quantity, unit_price, total_price, discount_amount)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """
                    sale_item_values = (
                        self.current_sale_id,
                        row['barcode'],
                        final_product_id,
                        row['quantity'],
                        row['price'],
                        row['subtotal'], 
                        row['discount']
                    )
                    connection.insertingtodatabase(sale_item_sql, sale_item_values)
                
                ui.notify(f'Sale updated successfully! ID: {self.current_sale_id}')

                # Update customer balance only if payment method is "On Account"
                if customer_id and payment_method == 'On Account':
                    connection.insertingtodatabase(
                        "UPDATE customers SET balance = balance + ? WHERE id = ?",
                        (final_total, customer_id)
                    )
                    ui.notify(f'Customer balance updated successfully! New balance: {final_total}')
                elif payment_method == 'Cash':
                    ui.notify('Cash payment - customer balance not updated')
                
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
                    barcode = row['barcode']
                    product_id_from_barcode = connection.getid('select id from products where barcode = ?', [barcode])
                    final_product_id = product_id_from_barcode or product_id
                    
                    sale_item_sql = """
                        INSERT INTO sale_items (sales_id, barcode, product_id, quantity, unit_price, total_price, discount_amount)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """
                    sale_item_values = (
                        last_sale_id,
                        row['barcode'],
                        final_product_id,
                        row['quantity'],
                        row['price'],
                        row['subtotal'], 
                        row['discount']
                    )
                    connection.insertingtodatabase(sale_item_sql, sale_item_values)
                
                ui.notify(f'Sale saved successfully! Invoice: {invoice_number}')

                # Update customer balance only if payment method is "On Account"
                if customer_id and payment_method == 'On Account':
                    connection.update_customerbalance(
                        "UPDATE customers SET balance = balance + ? WHERE id = ?",
                        (final_total, customer_id)
                    )
                    ui.notify(f'Customer balance updated successfully! New balance: {final_total}')
                elif payment_method == 'Cash':
                    ui.notify('Cash payment - customer balance not updated')
            
            self.refresh_sales_table()
            self.sales_aggrid.classes(remove='dimmed')
        except Exception as e:
            ui.notify(f'Error saving sale: {str(e)}')

    def load_max_sale(self):
        """Automatically load the sale with the maximum ID when entering the interface."""
        try:
            max_id = self.get_max_sale_id()
            if max_id > 0:
                # Fetch the sale data for the max ID
                sale_data = []
                connection.contogetrows(
                    f"SELECT s.id, s.sale_date, c.customer_name, s.total_amount, s.invoice_number, s.payment_status FROM sales s INNER JOIN customers c ON c.id = s.customer_id WHERE s.id = {max_id}",
                    sale_data
                )
                
                if sale_data:
                    row_data = {
                        'id': sale_data[0][0],
                        'sale_date': sale_data[0][1],
                        'customer_name': sale_data[0][2],
                        'total_amount': sale_data[0][3],
                        'invoice_number': sale_data[0][4],
                        'payment_status': sale_data[0][5]
                    }
                    
                    # Update customer name input with the customer from the max sale
                    self.customer_input.value = row_data['customer_name']
                    
                    # Set the current sale ID
                    self.current_sale_id = max_id
                    
                    # Fetch related sale items using the max sale_id
                    sale_items_data = []
                    connection.contogetrows(
                        f"SELECT p.barcode, p.product_name, si.quantity, ISNULL(si.discount_amount, 0), si.unit_price, si.total_price FROM sale_items si INNER JOIN products p ON p.id = si.product_id WHERE si.sales_id = {max_id}",
                        sale_items_data
                    )
                    
                    # Clear and populate table with sale items
                    self.rows.clear()
                    for item in sale_items_data:
                        self.rows.append({
                            'barcode': str(item[0]) if item[0] else '',
                            'product': str(item[1]) if item[1] else 'Unknown Product',
                            'quantity': int(item[2]) if item[2] else 0,
                            'discount': float(item[3]) if item[3] else 0.0,
                            'price': float(item[4]) if item[4] else 0.0,
                            'subtotal': float(item[5]) if item[5] else 0.0
                        })
            
                    # Update the table display
                    self.aggrid.options['rowData'] = self.rows
                    self.aggrid.update()
                    
                    self.total_amount = sum(row['subtotal'] for row in self.rows)
                    self.total_label.text = f"Total: ${self.total_amount:.2f}"
                    self.invoicenumber = row_data["invoice_number"]
                    
                    ui.notify(f'✅ Automatically loaded sale ID: {max_id} - Invoice: {row_data["invoice_number"]}')
                else:
                    ui.notify('No sales found in database')
            else:
                    ui.notify('No sales found in database')
                
        except Exception as e:
            ui.notify(f'Error loading max sale: {str(e)}')

    def create_ui(self):
        """Create the main UI layout with working dialogs and compact design."""
        with ui.element('div').classes('flex w-full h-screen'):
            # === LEFT SIDE BUTTONS - ULTRA COMPACT ===
            with ui.element('div').classes('w-1/12 bg-gray-100 p-1 flex flex-col gap-1'):
                ui.button('🆕 New', on_click=self.clear_inputs).classes('text-xs py-1 px-2 w-full')

                ui.button('💾 Save', on_click=self.save_sale).classes('text-xs py-1 px-2 w-full')
                ui.button('↩️ Undo', on_click=self.show_undo_confirmation).classes('text-xs py-1 px-2 w-full')
                ui.button('🗑️ Delete', on_click=self.delete_sale).classes('text-xs py-1 px-2 w-full')
                ui.button('🖨️ Print', on_click=self.print_invoice).classes('text-xs py-1 px-2 w-full')
                ui.button('🔄 Refresh', on_click=self.refresh_sales_table).classes('text-xs py-1 px-2 w-full')
                            # Add custom CSS for AG Grid theme
                 # === RIGHT SIDE CONTENT - ULTRA COMPACT ===
            with ui.element('div').classes('w-11/12 p-1 flex flex-col gap-1 overflow-y-auto'):
                # --- HORIZONTAL SPLITTER: Search Results and Order/Customer Info ---
                with ui.splitter(horizontal=True, value=35).classes('w-full h-full') as main_splitter:
                    with main_splitter.separator:
                        ui.icon('lightbulb').classes('text-green text-sm')
                    with main_splitter.before:
                        # Search results grid with scrollable container - COMPACT
                        with ui.element('div').classes('w-full h-full p-1'):
                            ui.label('Sales History').classes('text-sm font-bold text-gray-700 mb-1')
                            
                            # Define columns for sales search grid - REDUCED WIDTHS
                            sales_columns = [
                                {'headerName': 'ID', 'field': 'id', 'width': 40, 'filter': True, 'headerClass': 'green-header'},
                                {'headerName': 'Date', 'field': 'sale_date', 'width': 70, 'filter': True, 'headerClass': 'green-header'},
                                {'headerName': 'Customer', 'field': 'customer_name', 'width': 100, 'filter': True, 'headerClass': 'green-header'},
                                {'headerName': 'Total', 'field': 'total_amount', 'width': 60,  'filter': True, 'headerClass': 'green-header'},
                                {'headerName': 'Invoice', 'field': 'invoice_number', 'width': 80, 'filter': True, 'headerClass': 'green-header'},
                                {'headerName': 'Status', 'field': 'payment_status', 'width': 60, 'filter': True, 'headerClass': 'green-header'}
                            ]

                            # Fetch sales data
                            raw_sales_data = []
                            connection.contogetrows(
                                "SELECT s.id, s.sale_date, c.customer_name, s.total_amount, s.invoice_number, s.payment_status FROM sales s INNER JOIN customers c ON c.id = s.customer_id ORDER BY s.id DESC", 
                                raw_sales_data
                            )
                            
                            # Convert to AG Grid format
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

                            # Create AG Grid for sales search with 3 ROWS MAX HEIGHT
                            
                            self.sales_aggrid = ui.aggrid({
                                'columnDefs': sales_columns,
                                'rowData': sales_data,
                                'defaultColDef': {'flex': 1, 'minWidth': 30, 'sortable': True, 'filter': True},
                                'rowSelection': 'single',
                                'domLayout': 'normal',
                                
                            }).classes('w-full rounded border border-red-200 ag-theme-quartz-custom').style('overflow-y: auto;height:200px;')
                            
                            # Add click handler for sales grid
                            async def handle_sales_aggrid_click():
                                
                                try:
                                    selected_row = await self.sales_aggrid.get_selected_row()
                                    if selected_row and isinstance(selected_row, dict) and 'id' in selected_row:
                                        sale_id = selected_row['id']
                                        customer_name = selected_row['customer_name']
                                        
                                        ui.notify(f'Loading items for sale ID: {sale_id}')
                                        
                                        # Update customer name input
                                        self.customer_input.value = customer_name
                                        
                                        # Set the current sale ID
                                        self.current_sale_id = sale_id
                                        
                                        # Fetch related sale items
                                        sale_items_data = []
                                        connection.contogetrows(
                                            f"SELECT p.barcode, p.product_name, si.quantity, ISNULL(si.discount_amount, 0), si.unit_price, si.total_price FROM sale_items si INNER JOIN products p ON p.id = si.product_id WHERE si.sales_id = {sale_id}",
                                            sale_items_data
                                        )
                                        
                                        # Clear and populate table
                                        self.rows.clear()
                                        for item in sale_items_data:
                                            self.rows.append({
                                                'barcode': str(item[0]) if item[0] else '',
                                                'product': str(item[1]) if item[1] else 'Unknown Product',
                                                'quantity': int(item[2]) if item[2] else 0,
                                                'discount': float(item[3]) if item[3] else 0.0,
                                                'price': float(item[4]) if item[4] else 0.0,
                                                'subtotal': float(item[5]) if item[5] else 0.0
                                            })
                                    
                                        # Update displays
                                        self.aggrid.options['rowData'] = self.rows
                                        self.aggrid.update()
                                        
                                        self.total_amount = sum(row['subtotal'] for row in self.rows)
                                        self.total_label.text = f"Total: ${self.total_amount:.2f}"
                                        self.invoicenumber = selected_row["invoice_number"]
                                        
                                        # Update totals after loading sale items
                                        self.update_totals()
                                        
                                        ui.notify(f'✅ Loaded {len(self.rows)} items for invoice {selected_row["invoice_number"]}')
                                        
                                except Exception as ex:
                                    ui.notify(f'❌ Error loading sale items: {str(ex)}')
                            
                            self.sales_aggrid.on('cellClicked', handle_sales_aggrid_click)
                            
                            # Auto-load max sale
                            ui.timer(0.1, self.load_max_sale, once=True)
                
                    # --- ULTRA COMPACT ORDER/CUSTOMER INFO & PRODUCT ENTRY ---
                    with main_splitter.after:
                        # Ultra-compact customer info section
                        with ui.element('div').classes('w-full'):
                            # Single row for all customer info - MINIMAL HEIGHT
                            with ui.row().classes('w-full items-center gap-20 mb-1 p-1 bg-blue-100 rounded '):
                                # Date picker - compact
                                self.date_input = ui.input('Date', value=datetime.now().strftime('%Y-%m-%d %H:%M:%S')).classes('w-24 h-7 text-xs')
                                
                                # Customer selection - compact
                                self.customer_input = ui.input('Customer', placeholder='Customer').classes('w-28 h-7 text-xs')
                                self.customer_input.on('click', lambda: self.customer_dialog.open())
                                
                                # Phone - compact
                                self.phone_input = ui.input('Phone', placeholder='Phone').classes('w-20 h-7 text-xs')
                                
                              
                                
                                # Currency - compact
                                ui.input('Currency', value='USD').classes('w-12 h-7 text-xs')
                                  # Payment method - compact
                               
                                
                                self.payment_method = ui.radio(options=['Cash', 'On Account'], value='Cash').props('inline')

                        # Customer dialog - compact version
                        self.customer_dialog = ui.dialog()
                        with self.customer_dialog, ui.card().classes('w-full'):
                            headers = []
                            connection.contogetheaders("SELECT id, customer_name, phone, balance FROM customers", headers)
                            columns = [{'name': header, 'label': header.title(), 'field': header, 'sortable': True} for header in headers]
                            
                            # Fetch data from database
                            data = []
                            connection.contogetrows("SELECT id, customer_name, phone,balance FROM customers", data)
                            rows = []
                            for row in data:
                                row_dict = {}
                                for i, header in enumerate(headers):
                                    row_dict[header] = row[i]
                                rows.append(row_dict)
                            
                            table = ui.table(columns=columns, rows=rows, pagination=5).classes('w-full text-xs')
                            ui.input('Search').bind_value(table, 'filter').classes('text-xs')
                            
                            def on_row_click(row_data):
                                selected_row = row_data.args[1]
                                self.customer_input.value = selected_row['customer_name']
                                self.phone_input.value = selected_row['phone']
                                self.customer_dialog.close()
                                
                            table.on('rowClick', on_row_click)

                        # Product dialog - compact version
                        self.product_dialog = ui.dialog()
                        with self.product_dialog, ui.card().classes('w-full'):
                            headers = []
                            connection.contogetheaders("SELECT barcode, product_name, stock_quantity, price,cost_price FROM products", headers)
                            columns = [{'name': header, 'label': header.title(), 'field': header, 'sortable': True} for header in headers]
                            
                            # Fetch data from database
                            data = []
                            connection.contogetrows("SELECT barcode, product_name, stock_quantity, price,cost_price FROM products", data)
                            rows = []
                            for row in data:
                                row_dict = {}
                                for i, header in enumerate(headers):
                                    row_dict[header] = row[i]
                                rows.append(row_dict)
                            
                            table = ui.table(columns=columns, rows=rows, pagination=10).classes('w-full text-xs')
                            ui.input('Search').bind_value(table, 'filter').classes('text-xs')
                            
                            def on_product_select(row_data):
                                selected_row = row_data.args[1]
                                self.product_input.value = selected_row['product_name']
                                self.barcode_input.value = selected_row['barcode']
                                self.price_input.value = selected_row['price']
                                self.product_dialog.close()
                                
                                # Automatically add the product to the grid
                                self.add_product()
                                
                            table.on('rowClick', on_product_select)

                        # Ultra-compact product entry container
                        with ui.element('div').classes('w-full '):
                            # Input row for new product - IMPROVED SIZE AND PADDING
                            with ui.row().classes('w-full items-center gap-3 p-3 bg-gray-100 rounded-lg shadow-sm'):
                                self.barcode_input = ui.input('Barcode', placeholder='Barcode').classes('w-24 h-10 text-sm').on('change', lambda e: self.update_product_dropdown(e))
                                self.product_input = ui.input('Product', placeholder='Product').classes('w-32 h-10 text-sm').on('click', lambda: self.product_dialog.open())
                                self.quantity_input = ui.number('Qty', value=1, min=1).classes('w-16 h-10 text-sm')
                                self.price_input = ui.number('Price', value=0.0, min=0).classes('w-20 h-10 text-sm')
                                self.discount_input = ui.number('Disc %', value=0, min=0, max=100).classes('w-16 h-10 text-sm')
                                ui.button('Add', on_click=self.add_product).props('size=md').classes('h-10 px-4 text-sm font-medium')
                            uiAggridTheme.addingtheme()
                            # AG Grid container - fixed height above footer
                            with ui.element('div').classes('w-full h-[calc(100vh-480px)] min-h-48 border rounded-lg bg-white shadow-sm mt-4'):
                                # AG Grid for products - FIXED HEIGHT
                                self.aggrid = ui.aggrid({
                                    'columnDefs': self.columns,
                                    'rowData': self.rows,
                                    'defaultColDef': {'flex': 1, 'minWidth': 40, 'sortable': True, 'filter': True},
                                    'rowSelection': 'single',
                                    'domLayout': 'normal',
                                    
                                }).classes('w-full h-full p-2')
                                
                                # Click handler for editing
                                async def handle_aggrid_click():
                                    try:
                                        selected_row = await self.aggrid.get_selected_row()
                                        if selected_row:
                                            self.open_edit_dialog(selected_row)
                                            # Update totals after selection
                                            self.update_totals()
                                    except Exception as ex:
                                        ui.notify(f'Error: {str(ex)}')
                                
                                self.aggrid.on('cellClicked', handle_aggrid_click)

                        # Footer section with summary - MOVED TO BOTTOM
                        with ui.element('div').classes('w-full p-4 bg-gray-100 border-t border-gray-300 fixed bottom-0 left-0 right-0 z-10'):
                            with ui.row().classes('w-full justify-between items-center'):
                                # Left side - Item count and quantity
                                with ui.column().classes('gap-1'):
                                    ui.label('SUMMARY').classes('text-sm font-bold text-gray-700')
                                    
                                    
                                    self.summary_label = ui.label('0 items').classes('text-sm text-gray-600')
                                    self.quantity_total_label = ui.label('Qty: 0').classes('text-sm text-gray-600')
                                
                                # Center - Calculate Profit button and Discount inputs
                                with ui.column().classes('gap-2 items-center'):
                                    # Calculate Profit button
                                    ui.button('Calculate Profit', on_click=self.show_profit_dialog).props('color=primary').classes('h-10 px-4 text-sm font-medium')
                                    
                                    with ui.row().classes('items-center gap-2'):
                                        ui.label('Discount:').classes('text-sm font-medium')
                                        self.discount_percent_input = ui.number(
                                            value=0,
                                            min=0,
                                            max=100,
                                            on_change=self.update_totals
                                        ).classes('w-24 h-12 text-xl px-2 border-2 border-gray-300 rounded')
                                        ui.label('%').classes('text-sm')
                                        
                                        self.discount_amount_input = ui.number(
                                            value=0,
                                            min=0,
                                            on_change=self.update_totals
                                        ).classes('w-32 h-12 text-xl px-2 border-2 border-gray-300 rounded')
                                
                                # Right side - Totals and Profit display
                                with ui.column().classes('gap-1 items-end'):
                                    
                                    self.subtotal_label = ui.label('Subtotal: $0.00').classes('text-2xl font-bold')
                                    self.total_label = ui.label('Total: $0.00').classes('text-3xl font-bold text-blue-600')

@ui.page('/sales')
def sales_page_route():
    SalesUI()
