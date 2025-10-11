from nicegui import ui
from datetime import date as dt
from connection import connection
from datetime import datetime
from loading_indicator import loading_indicator
import asyncio
class SalesUI:
    
    def __init__(self):
        self.invoicenumber=''
        with ui.header().classes('items-center justify-between'):
            ui.label('Sales Management').classes('text-2xl font-bold')
            ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).props('flat color=white')
            # --- Mock Data ---
            
            # Get max ID from searchtable (sales table) on initialization
            self.max_sale_id = self.get_max_sale_id()
       
       

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

    def generate_invoice_number(self):
        """Generate the next unique invoice number based on the last used number."""
        try:
            # Get all existing invoice numbers to ensure uniqueness
            existing_invoices = connection.contogetrows(
                "SELECT invoice_number FROM sales WHERE invoice_number IS NOT NULL", 
                []
            )
            
            # Create a set of existing invoice numbers for quick lookup
            existing_set = {row[0] for row in existing_invoices}
            
            # Find the highest numeric invoice number
            max_num = 0
            for invoice in existing_set:
                if invoice.startswith('INV-'):
                    try:
                        num = int(invoice.split('-')[1])
                        max_num = max(max_num, num)
                    except (ValueError, IndexError):
                        continue
            
            # Start from the next available number
            next_num = max_num + 1
            
            # Ensure the generated number is unique
            while f"INV-{next_num:06d}" in existing_set:
                next_num += 1
            
            return f"INV-{next_num:06d}"
            
        except Exception as e:
            # Fallback to timestamp-based invoice number
            import time
            return f"INV-{int(time.time())}"

    def add_product(self,e=None):
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
            
            
            # clear the inputs 
            self.clear_inputs_inputs()
            # Update table
            self.table.update()
            self.table.run_method('scrollTo', len(self.table.rows)-1)
            
            
            
            
        except ValueError as e:
            ui.notify(f'Invalid input: {str(e)}')
    def clear_inputs_inputs(self):
        self.barcode_input.value = ''
        self.product_input.value = ''
        self.quantity_input.value = 1
        self.discount_input.value = 0
        self.price_input.value = 0.0
        
    
    def clear_inputs(self):
        """Clear all input fields and set default customer."""
        # Set customer to Cash Client by default
        self.customer_input.value = 'Cash Client'
        self.phone_input.value = ''
        
        # Clear product input fields
        self.barcode_input.value = ''
        self.product_input.value = ''
        self.quantity_input.value = 1
        self.discount_input.value = 0
        self.price_input.value = 0.0
        
        # Clear the table (remove all rows)
        self.rows.clear()
        self.table.update()
        
        # Reset totals
        self.total_amount = 0
        self.subtotal_label.text = "Subtotal: $0.00"
        self.total_label.text = "Total: $0.00"
        
        # Reset discount inputs
        self.discount_percent_input.value = 0
        self.discount_amount_input.value = 0
        
        # Reset current sale ID and make search table editable
        self.current_sale_id = None
        self.searchtable.props(remove='readonly')

    def update_product_dropdown(self, e):
        """Update product dropdown based on barcode."""
        try:
            barcode = self.barcode_input.value
            if barcode:
                # Query database for product with matching barcode
                product_data = []
                connection.contogetrows(
                    f"SELECT barcode, product_name, price FROM products WHERE barcode = '{barcode}'", 
                    product_data
                )
                
                if product_data:
                    product = product_data[0]
                    self.product_input.value = product[1]  # product_name
                    self.price_input.value = float(product[2])  # price
                    ui.notify(f"Product loaded: {product[1]}")
                else:
                    ui.notify("Product not found for this barcode")
        except Exception as e:
            ui.notify(f'Error updating product: {str(e)}')

    def on_row_click_edit_cells(self, e):
        """Handle row click events - open edit dialog for selected row."""
        try:
            # Get the row data from the event
            row_index = e.args[0] if len(e.args) > 0 else None
            row_data = e.args[1] if len(e.args) > 1 else None
            
            # Validate we have row data
            if row_data and isinstance(row_data, dict):
                ui.notify(f"Selected: {row_data.get('product', 'Unknown')} - Qty: {row_data.get('quantity', 0)}")
                self.open_edit_dialog(row_data, row_index)
            elif row_index is not None and 0 <= row_index < len(self.rows):
                # Use row data from our rows list
                row_data = self.rows[row_index]
                ui.notify(f"Selected: {row_data.get('product', 'Unknown')} - Qty: {row_data.get('quantity', 0)}")
                self.open_edit_dialog(row_data, row_index)
            else:
                ui.notify("No row data available for editing")
                
        except Exception as ex:
            ui.notify(f"Error opening edit dialog: {str(ex)}")
            

    def open_edit_dialog(self, row_data, row_index=None):
        """Open a dialog for editing the selected row."""
        dialog = ui.dialog()
        
        with dialog, ui.card().classes('w-96 p-6'):
            ui.label('Edit Product').classes('text-xl font-bold mb-4')
            
            # Form fields for editing
            with ui.column().classes('w-full gap-3'):
                # Display read-only fields
                ui.label(f"Barcode: {row_data['barcode']}").classes('font-medium')
                ui.label(f"Product: {row_data['product']}").classes('font-medium')
                
                # Editable fields
                quantity_input = ui.number('Quantity', value=row_data['quantity'], min=1)
                discount_input = ui.number('Discount %', value=row_data['discount'], min=0, max=100)
                price_input = ui.number('Price', value=row_data['price'], min=0, step=0.01)
                
                # Buttons
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
        """Save the edited row data and update the table."""
        try:
            # Find the index of the row to update
            row_index = next(i for i, row in enumerate(self.rows) 
                           if row['barcode'] == original_row['barcode'] and 
                              row['product'] == original_row['product'])
            
            # Calculate old subtotal for total adjustment
            old_subtotal = self.rows[row_index]['subtotal']
            
            # Update the row data
            self.rows[row_index]['quantity'] = int(new_quantity)
            self.rows[row_index]['discount'] = float(new_discount)
            self.rows[row_index]['price'] = float(new_price)
            self.rows[row_index]['subtotal'] = self.calculate_subtotal(
                int(new_quantity), 
                float(new_price), 
                float(new_discount)
            )
            
            # Update total amount
            self.total_amount = self.total_amount - old_subtotal + self.rows[row_index]['subtotal']
            self.total_label.text = f"Total: ${self.total_amount:.2f}"
            
            # Update the table display
            self.table.update()
            
            # Close the dialog
            dialog.close()
            
            ui.notify('Product updated successfully')
            
        except Exception as e:
            ui.notify(f'Error updating product: {str(e)}')

    def delete_row(self, row_data, dialog):
        """Delete the selected row from the table."""
        try:
            # Find and remove the row
            row_index = next(i for i, row in enumerate(self.rows) 
                           if row['barcode'] == row_data['barcode'] and 
                              row['product'] == row_data['product'])
            
            # Subtract from total
            self.total_amount -= self.rows[row_index]['subtotal']
            self.total_label.text = f"Total: ${self.total_amount:.2f}"
            
            # Remove the row
            del self.rows[row_index]
            
            # Update the table display
            self.table.update()
            
            # Close the dialog
            dialog.close()
            
            ui.notify('Product removed successfully')
            
        except Exception as e:
            ui.notify(f'Error removing product: {str(e)}')

    def update_totals(self):
        """Update subtotal and total displays."""
        subtotal = sum(row['subtotal'] for row in self.rows)
        self.subtotal_label.text = f"Subtotal: ${subtotal:.2f}"
        
        # Calculate final total with discounts
        discount_percent = float(self.discount_percent_input.value or 0)
        discount_amount = float(self.discount_amount_input.value or 0)
        
        total_after_percent = subtotal * (1 - discount_percent / 100)
        final_total = total_after_percent - discount_amount
        
        self.total_label.text = f"Total: ${max(0, round(final_total, 2)):.2f}"

    def get_max_sale_id(self):
        """Get the maximum sale ID from the searchtable (sales table)."""
        try:
            # Get max sale ID from database
            max_id_result = []
            connection.contogetrows("SELECT MAX(id) FROM sales", max_id_result)
            
            if max_id_result and max_id_result[0][0]:
                max_id = max_id_result[0][0]
                return max_id
            else:
                return 0
                
        except Exception as e:
            print(f"Error getting max sale ID: {e}")
            return 0

    def display_max_sale_id(self):
        """Display the maximum sale ID from the search table."""
        try:
            # Get max sale ID from database
            max_id_result = []
            connection.contogetrows("SELECT MAX(id) FROM sales", max_id_result)
            
            if max_id_result and max_id_result[0][0]:
                max_id = max_id_result[0][0]
                self.max_id_label.text = f"Max Sale ID: {max_id}"
            else:
                self.max_id_label.text = "Max Sale ID: 0"
                
        except Exception as e:
            self.max_id_label.text = "Max Sale ID: Error"
            print(f"Error getting max sale ID: {e}")

    def show_undo_confirmation(self):
        """Show confirmation dialog for undo action."""
        dialog = ui.dialog()
        
        with dialog, ui.card().classes('w-96 p-6'):
            ui.label('Confirm Undo').classes('text-xl font-bold mb-4')
            ui.label('Are you sure you want to undo all changes?').classes('mb-4')
            
            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('Cancel', on_click=dialog.close)
                ui.button('OK', on_click=lambda: self.perform_undo(dialog)).props('color=primary')
        
        dialog.open()

    def show_delete_confirmation(self):
        """Show confirmation dialog for delete action."""
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

    def perform_delete(self, dialog):
        """Perform the delete action."""
        if hasattr(self, 'current_sale_id') and self.current_sale_id:
            self.delete_sale(self.current_sale_id)
        else:
            ui.notify('No sale selected for deletion')
        dialog.close()

    def perform_undo(self, dialog):
        """Perform the undo action and clear UI cards."""
        # Clear the table rows
        self.rows.clear()
        self.table.update()
        
        # Reset totals
        self.total_amount = 0
        self.total_label.text = "Total: $0.00"
        self.subtotal_label.text = "Subtotal: $0.00"
        
        # Clear input fields
        self.clear_inputs()
        
        # Close the dialog
        dialog.close()
        
        ui.notify('Undo completed successfully')

    def refresh_sales_table(self):
        """Refresh the sales table with latest data."""
        try:
            # Fetch updated sales data
            raw_sales_data = []
            connection.contogetrows(
                "SELECT s.id, s.sale_date, c.customer_name, s.total_amount, s.invoice_number, s.payment_status FROM sales s INNER JOIN customers c ON c.id = s.customer_id", 
                raw_sales_data
            )
            
            # Convert pyodbc.Row objects to dictionaries
            sales_data = []
            for row in raw_sales_data:
                sales_data.append({
                    'id': row[0],
                    'sale_date': row[1],
                    'customer_name': row[2],
                    'total_amount': row[3],
                    'invoice_number': row[4],
                    'payment_status': row[5]
                })
            
            # Update the search table
            self.searchtable.rows = sales_data
            self.searchtable.update()
            
        except Exception as e:
            ui.notify(f'Error refreshing sales table: {str(e)}')

    def delete_sale(self, sale_id):
        """Delete a sale and its associated items by sale ID."""
        try:
            if not sale_id:
                ui.notify('No sale selected for deletion')
                return
            
            # Delete sale items first (foreign key constraint)
            connection.deleterow("DELETE FROM sale_items WHERE sales_id = ?", [sale_id])
            
            # Delete the sale
            connection.deleterow("DELETE FROM sales WHERE id = ?", [sale_id])
            
            ui.notify(f'Sale {sale_id} deleted successfully')
            
            # Refresh the sales table
            self.refresh_sales_table()
            
            # Clear the current form
            self.clear_inputs()
            
        except Exception as e:
            ui.notify(f'Error deleting sale: {str(e)}')

    def save_sale(self):
        """Save the current sale to the database."""
        try:
            if not self.rows:
                ui.notify('No items to save!')
                return

            # Get ledger id for sales (7011)
            ledger_data = []
            connection.contogetrows("SELECT Id FROM Ledger WHERE AccountNumber='7011'", ledger_data)
            if not ledger_data:
                ui.notify('Sales ledger not found', color='red')
                return
            ledger_id = ledger_data[0][0]

            # Get current date and timestamp
            sale_date = str(self.date_input.value)
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Get customer info
            customer_name = self.customer_input.value or 'Cash Client'
            customer_id = connection.getid('select id from customers where customer_name = ?', [customer_name])

            # Calculate totals
            subtotal = sum(row['subtotal'] for row in self.rows)
            discount_percent = float(self.discount_percent_input.value or 0)
            discount_amount = float(self.discount_amount_input.value or 0)
            total_after_percent = subtotal * (1 - discount_percent / 100)
            final_total = total_after_percent - discount_amount

            if hasattr(self, 'current_sale_id') and self.current_sale_id:
                # Update existing sale
                sale_sql = """
                    UPDATE sales
                    SET sale_date = ?, customer_id = ?, subtotal = ?, discount_amount = ?,
                        total_amount = ?, created_at = ?
                    WHERE id = ?
                """
                sale_values = (sale_date, customer_id, subtotal, discount_amount, final_total, created_at, self.current_sale_id)
                connection.insertingtodatabase(sale_sql, sale_values)

                # Delete existing sale items for this sale
                delete_items_sql = "DELETE FROM sale_items WHERE sales_id = ?"
                connection.insertingtodatabase(delete_items_sql, [self.current_sale_id])

                # Insert updated sale items
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

            else:
                # Create new sale
                invoice_number = self.generate_invoice_number()

                sale_sql = """
                    INSERT INTO sales (sale_date, customer_id, subtotal, discount_amount, total_amount, invoice_number, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                sale_values = (sale_date, customer_id, subtotal, discount_amount, final_total, invoice_number, created_at)
                connection.insertingtodatabase(sale_sql, sale_values)

                # Get the last inserted sale ID
                last_sale_id = connection.getid("SELECT MAX(id) FROM sales", [])

                # Get next subnumber for auxiliary
                sub_data = []
                connection.contogetrows("SELECT COUNT(*) FROM Auxiliary WHERE LedgerId=?", sub_data, (ledger_id,))
                next_sub = sub_data[0][0] + 1
                account_number = f"7011.{next_sub:06d}"

                # Create auxiliary
                aux_sql = "INSERT INTO Auxiliary (LedgerId, AccountNumber, Name, Status) VALUES (?, ?, ?, 1)"
                connection.insertingtodatabase(aux_sql, (ledger_id, account_number, invoice_number))

                # Get auxiliary id
                aux_id_data = []
                connection.contogetrows("SELECT @@IDENTITY", aux_id_data)
                aux_id = aux_id_data[0][0]

                # Update sale with auxiliary_id
                connection.insertingtodatabase("UPDATE sales SET auxiliary_id=? WHERE id=?", (aux_id, last_sale_id))

                # Insert sale items
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

            # Refresh the sales table
            self.refresh_sales_table()

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
                    
                    # Set the current sale ID for updates
                    self.current_sale_id = max_id
                    
                    # Make search table read-only when loading existing sale
                    self.searchtable.props('readonly')
                    
                    # Fetch related sale items using the max sale_id
                    sale_items_data = []
                    connection.contogetrows(
                        f"SELECT p.barcode, p.product_name, si.quantity, ISNULL(si.discount_amount, 0), si.unit_price, si.total_price FROM sale_items si INNER JOIN products p ON p.id = si.product_id WHERE si.sales_id = {max_id}",
                        sale_items_data
                    )
                    
                    # Clear and populate self.table with sale items
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
                    self.table.update()
                    
                    # Update totals
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
            print(f"Error loading max sale: {e}")

    def create_ui(self):
        """Create the main UI layout."""
        with ui.element('div').classes('flex w-full h-screen'):
            # === LEFT SIDE BUTTONS ===
            with ui.element('div').classes('w-1/12 bg-gray-100 p-2 flex flex-col gap-2'):
                ui.button('🆕 New', on_click=self.clear_inputs)
                ui.button('💾 Save', on_click=self.save_sale)
                ui.button('↩️ Undo', on_click=self.show_undo_confirmation)
                ui.button('🗑️ Delete', on_click=self.show_delete_confirmation)
                ui.button('🖨️ Print')
                ui.button('🔄 Refresh', on_click=self.refresh_sales_table)

            # === RIGHT SIDE CONTENT ===
            with ui.element('div').classes('w-11/12 p-4 flex flex-col gap-4 overflow-y-auto'):
                # --- CARD 0: Sales Search ---
                with ui.card().classes('w-full').style('margin: 2px 0; padding: 4px;'):
                    with ui.expansion('Sales Info', icon='table', value=True).style('font-size: 8px;'):
                        # Define essential columns for better card fit
                        columns = [
                            {'name': 'id', 'label': 'ID', 'field': 'id', 'sortable': True, 'classes': 'w-12'},
                            {'name': 'sale_date', 'label': 'Date', 'field': 'sale_date', 'sortable': True, 'classes': 'w-20'},
                            {'name': 'customer_name', 'label': 'Customer', 'field': 'customer_name', 'sortable': True, 'classes': 'w-32'},
                            {'name': 'total_amount', 'label': 'Total', 'field': 'total_amount', 'sortable': True, 'classes': 'w-20'},
                            {'name': 'invoice_number', 'label': 'Invoice', 'field': 'invoice_number', 'sortable': True, 'classes': 'w-24'},
                            {'name': 'payment_status', 'label': 'Status', 'field': 'payment_status', 'sortable': True, 'classes': 'w-20'}
                        ]

                        # Fetch rows for the table with essential columns only
                        raw_sales_data = []
                        connection.contogetrows(
                            "SELECT s.id, s.sale_date, c.customer_name, s.total_amount, s.invoice_number, s.payment_status FROM sales s INNER JOIN customers c ON c.id = s.customer_id", 
                            raw_sales_data
                        )
                        
                        # Convert pyodbc.Row objects to dictionaries
                        sales_data = []
                        for row in raw_sales_data:
                            sales_data.append({
                                'id': row[0],
                                'sale_date': row[1],
                                'customer_name': row[2],
                                'total_amount': row[3],
                                'invoice_number': row[4],
                                'payment_status': row[5]
                            })

                        # Create self.searchtable with sales data - limited to 4 rows with scroll
                        self.searchtable = ui.table(
                            columns=columns, 
                            rows=sales_data, 
                            pagination={'rowsPerPage': 4, 'page': 1}
                        ).classes('w-full h-48').style('font-size: 8px; line-height: 1;')
                        self.searchtable.props('dense virtual-scroll')
                        
                        # Add search functionality
                        ui.input('Search Sales', placeholder='Search by customer, invoice, etc...').bind_value(self.searchtable, 'filter')
                        
                        # Handle row click event to populate self.table
                        def handle_sales_row_click(e):
                            try:
                                row_data = e.args[1]
                                sale_id = row_data['id']
                                customer_name = row_data['customer_name']
                                
                                ui.notify(f'Loading items for sale ID: {sale_id}')
                                
                                # Update customer name input with the customer from clicked row
                                self.customer_input.value = customer_name
                                
                                # Set the current sale ID for updates
                                self.current_sale_id = sale_id
                                
                                # Make search table read-only when loading existing sale
                                self.searchtable.props('readonly')
                                
                                # Fetch related sale items using the sale_id
                                sale_items_data = []
                                connection.contogetrows(
                                    f"SELECT p.barcode, p.product_name, si.quantity, ISNULL(si.discount_amount, 0), si.unit_price, si.total_price FROM sale_items si INNER JOIN products p ON p.id = si.product_id WHERE si.sales_id = {sale_id}",
                                    sale_items_data
                                )
                                
                                # Clear and populate self.table with sale items
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
                                self.table.update()
                                
                                # Update totals
                                self.total_amount = sum(row['subtotal'] for row in self.rows)
                                self.total_label.text = f"Total: ${self.total_amount:.2f}"
                                self.invoicenumber=row_data["invoice_number"]
                                
                                ui.notify(f'✅ Loaded {len(self.rows)} items for invoice {row_data["invoice_number"]}')
                                
                            except Exception as ex:
                                ui.notify(f'❌ Error loading sale items: {str(ex)}')
                                print(f"Error details: {ex}")
                        
                        # Bind the row click event to self.searchtable
                        self.searchtable.on('rowClick', handle_sales_row_click)
                        
                        # Automatically load the sale with max ID after UI is created
                        ui.timer(0.1, self.load_max_sale, once=True)

                # --- CARD 1: Date + Customer Info ---
                with ui.card().classes('w-full').style('margin: 2px 0; padding: 4px;'):
                    with ui.expansion('Order & Customer Info', icon='person', value=True).style('font-size: 8px;'):
                        with ui.row().classes('items-center w-full gap-4'):
                            # DATE PICKER with icon menu
                            with ui.input('Date', value=str(dt.today())) as self.date_input:
                                with ui.menu().props('no-parent-event') as menu:
                                    with ui.date().bind_value(self.date_input):
                                        with ui.row().classes('justify-end'):
                                            ui.button('Close', on_click=menu.close).props('flat')
                                with self.date_input.add_slot('append'):
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
                        with ui.dialog() as dialog, ui.card():
                                headers = []
                                connection.contogetheaders("SELECT barcode, product_name, stock_quantity,price FROM products", headers)
                                columns = [{'name': header, 'label': header.title(), 'field': header, 'sortable': True} for header in headers]
                                
                                # Fetch data from database
                                data = []
                                connection.contogetrows("SELECT barcode, product_name, stock_quantity,price FROM products", data)
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
                                    self.product_input.value = selected_row['product_name']
                                    self.barcode_input.value = selected_row['barcode']
                                    self.price_input.value = selected_row['price']
                                    dialog.close()
                                    
                                table.on('rowClick', on_row_click)
                            
                            # Open dialog when clicking on customer input
                        self.product_input.on('click', dialog.open)
                          
                        self.quantity_input = ui.number('Quantity', value=1, min=1)
                        self.discount_input = ui.number('Discount', value=0, min=0, max=100)
                        self.price_input = ui.number('Price', value=0.0, min=0)
                        ui.button('Add', on_click=self.add_product)

                # --- CARD 3: Product Table ---
                with ui.card().classes('w-full'):
                    with ui.element('div').classes('w-full'):
                        # Table with virtual scroll and styling
                        self.table = ui.table(
                            columns=self.columns, 
                            rows=self.rows, 
                            row_key='barcode'
                        ).classes('w-full').props('dense virtual-scroll')
                        self.table.on('rowClick', self.on_row_click_edit_cells)
                        self.table.props('style="border: 2px solid green"')
                        # Set table header background to red
                        self.table.props('table-class="bg-red"')
                        
                        

        # Add footer with calculations - 10px height
        with ui.footer().style('background-color: #3874c8; height: 70px; padding: 0; margin: 0; overflow: hidden;'):
            with ui.row().classes('w-full justify-between items-center h-full'):
                # Left side - empty for now
                ui.label('')
                
                # Right side - calculations
                with ui.row().classes('items-center gap-2 h-full'):
                    # Subtotal
                    with ui.column().classes('text-right h-full flex items-center'):
                        ui.label('Sub:').classes('text-white text-xs leading-none')
                        self.subtotal_label = ui.label('$0.00').classes('text-white text-xs font-bold leading-none')
                    
                    # Discount %
                    with ui.column().classes('text-right h-full flex items-center'):
                        ui.label('%:').classes('text-white text-xs leading-none')
                        self.discount_percent_input = ui.number(
                            value=0, 
                            min=0, 
                            max=100,
                            on_change=self.update_totals
                        ).classes('w-8 h-6 text-white bg-transparent border border-white rounded px-1 text-xs leading-none').style('font-size: 8px; padding: 0; margin: 0;')
                    
                    # Discount $
                    with ui.column().classes('text-right h-full flex items-center'):
                        ui.label('$:').classes('text-white text-xs leading-none')
                        self.discount_amount_input = ui.number(
                            value=0, 
                            min=0,
                            on_change=self.update_totals
                        ).classes('w-10 h-6 text-white bg-transparent border border-white rounded px-1 text-xs leading-none').style('font-size: 8px; padding: 0; margin: 0;')
                    
                    # Total
                    with ui.column().classes('text-right h-full flex items-center border-l border-white pl-2'):
                        ui.label('T:').classes('text-white text-xs leading-none')
                        self.total_label = ui.label('$0.00').classes('text-white text-xs font-bold leading-none')

# Create and run the application
@ui.page('/sales')
def sales_page_route():
    SalesUI()