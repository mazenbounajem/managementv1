from nicegui import ui
from connection import connection
from datetime import datetime
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage

class CustomerReceipt:
    def __init__(self):
        self.input_refs = {}
        self.initial_values = {}
        self.table = None
        self.selected_customer = None
        self.selected_invoices = []
        self.customer_input = None  # Initialize to avoid AttributeError
        self.max_id = 0  # Store the maximum ID
        
        self.max_customer_receipt_id = self.get_max_customer_receipt_id()
        self.setup_ui()
          # Get max ID on load
        self.get_max_customer_receipt_id
    def get_max_customer_receipt_id(self):
        try:
            max_id_result = []
            connection.contogetrows("SELECT MAX(id) FROM customer_receipt", max_id_result)
            return max_id_result[0][0] if max_id_result and max_id_result[0][0] else 0
        except Exception as e:
            return 0
    
    def load_max_customer_receipt(self):
        try:
            max_id_result = []
            connection.contogetrows("SELECT MAX(id) FROM customer_receipt", max_id_result)
            max_id = max_id_result[0][0] if max_id_result and max_id_result[0][0] else 0
            if max_id > 0:
                receipt_data = []
                connection.contogetrows(
                    f"SELECT cr.id, cr.manual_reference, cr.payment_date, c.customer_name, cr.amount, cr.payment_method, cr.status FROM customer_receipt cr INNER JOIN customers c ON c.id = cr.customer_id WHERE cr.id = {max_id}",
                    receipt_data
                )
                
                if receipt_data:
                    row_data = {
                        'id': receipt_data[0][0],
                        'manual_reference': receipt_data[0][1],
                        'payment_date': receipt_data[0][2],
                        'customer_name': receipt_data[0][3],
                        'amount': receipt_data[0][4],
                        'payment_method': receipt_data[0][5],
                        'status': receipt_data[0][6]
                    }
                    
                    # Update UI fields with the loaded receipt data
                    self.customer_input.value = row_data['customer_name']
                    self.ManualReference_input.value = row_data['manual_reference']
                    self.input_refs['total_amount'].set_value(f'{row_data["amount"]:.2f}')
                    self.input_refs['payment_method'].set_value(row_data['payment_method'])
                    
                    ui.notify(f'✅ Automatically loaded receipt ID: {max_id} - Amount: ${row_data["amount"]:.2f} - Status: {row_data["status"]}')
                else:
                    ui.notify('No receipts found in database')
            else:
                ui.notify('No receipts found in database')
                
        except Exception as e:
            ui.notify(f'Error loading max customer receipt: {str(e)}')

    def setup_ui(self):

        # Main content area with splitter layout
        with ui.element('div').classes('flex w-full h-screen'):
            # Left drawer for action buttons - rebuilt to match category.py pattern
            with ui.column().classes('w-48 p-4 bg-gray-100 flex-shrink-0'):
                ui.label('Actions').classes('text-lg font-bold mb-4')
                ui.button('New', icon='add', on_click=self.clear_input_fields).classes('bg-blue-500 text-white w-full mb-2')
                ui.button('Process Receipt', icon='payment', on_click=self.process_receipt).classes('bg-green-500 text-white w-full mb-2')
                ui.button('Undo', icon='undo', on_click=self.undo_changes).classes('bg-yellow-500 text-white w-full mb-2')
                ui.button('Delete', icon='delete', on_click=self.delete_receipt).classes('bg-red-500 text-white w-full mb-2')
                ui.button('Refresh', icon='refresh', on_click=self.refresh_table).classes('bg-purple-500 text-white w-full mb-2')
            
            # Main content area with splitter
            with ui.column().classes('flex-1 p-4 overflow-y-auto'):
                # Splitter for grid and form sections
                with ui.splitter(horizontal=True, value=40).classes('w-full h-full') as main_splitter:
                    with main_splitter.separator:
                        ui.icon('drag_handle').classes('text-gray-400 text-sm')
                    
                    # Top section - Pending Invoices Grid
                    with main_splitter.before:
                        
                        
                        # Search functionality
                        search_input = ui.input('Search Invoices').classes('w-full mb-2')
                        
                        # Column definitions for AG Grid
                        column_defs = [
                            {'headerName': 'ID', 'field': 'id', 'sortable': True, 'filter': True, 'width': 80},
                            {'headerName': 'Reference', 'field': 'manual_reference', 'sortable': True, 'filter': True, 'width': 150},
                            {'headerName': 'Payment Date', 'field': 'payment_date', 'sortable': True, 'filter': True, 'width': 150},
                            {'headerName': 'Customer', 'field': 'customer_name', 'sortable': True, 'filter': True, 'width': 200},
                            {'headerName': 'Amount', 'field': 'amount', 'sortable': True, 'filter': True, 'width': 120},
                            {'headerName': 'Method', 'field': 'payment_method', 'sortable': True, 'filter': True, 'width': 100},
                            {'headerName': 'Status', 'field': 'status', 'sortable': True, 'filter': True, 'width': 120}
                        ]
                        
                        # Create AG Grid table with scroll functionality
                        self.table = ui.aggrid({
                            'columnDefs': column_defs,
                            'rowData': [],
                            'defaultColDef': {'flex': 1, 'minWidth': 100, 'sortable': True, 'filter': True},
                            'rowSelection': 'single',
                            'domLayout': 'normal',
                            'pagination': True,
                            'paginationPageSize': 5
                        }).classes('w-full ag-theme-quartz-custom').style('height: 200px; overflow-y: auto;')
                        
                        # Fetch initial data immediately
                        self.refresh_table()
                        self.table.classes(remove='dimmed')
                    
                    # Bottom section - Receipt Details
                    with main_splitter.after:
                        ui.label('Receipt Details').classes('text-xl font-bold mb-2')
                        
                        # Input fields for receipt data
                        with ui.row().classes('w-full mb-4'):
                            self.ManualReference_input=ui.input('manual reference', placeholder='ManualReference').classes('w-20 h-7 text-xs')
                            self.input_refs['date'] = ui.input('Date', value=str(datetime.now().date())).classes('w-1/3')
                            
                            self.customer_input = ui.input('Customer', placeholder='Customer').classes('w-28 h-7 text-xs')
                            self.customer_input.on('click', lambda: self.customer_dialog.open())
                            self.balance_input=ui.input('balance', placeholder='balance').classes('w-20 h-7 text-xs')
                            ui.button('Select Invoice', icon='receipt', on_click=self.open_invoice_dialog).classes('w-1/4 mr-2 bg-green-500 text-white')
                        
                        # Create customer dialog
                        self.customer_dialog = ui.dialog()
                        with self.customer_dialog, ui.card().classes('w-full'):
                            headers = []
                            connection.contogetheaders("SELECT id, customer_name, phone,balance FROM customers", headers)
                            columns = [{'name': header, 'label': header.title(), 'field': header, 'sortable': True} for header in headers]
                            
                            data = []
                            connection.contogetrows("SELECT id, customer_name, phone,balance FROM customers", data)
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
                                self.balance_input.value = selected_row['balance']
                                self.selected_customer = selected_row
                                self.customer_dialog.close()
                                
                            table.on('rowClick', on_row_click)    
                            
                        # Create invoice dialog (but don't open it yet)
                        self.invoice_dialog = ui.dialog()
                        with self.invoice_dialog, ui.card().classes('w-full max-w-6xl'):
                            self.invoice_dialog_label = ui.label('').classes('text-xl font-bold mb-4')
                            
                            # Create AG Grid with checkboxes for invoice selection
                            column_defs = [
                                {'headerName': '', 'field': 'selected', 'checkboxSelection': True, 'width': 50},
                                {'headerName': 'Invoice #', 'field': 'invoice_number', 'width': 120},
                                {'headerName': 'Amount', 'field': 'total_amount', 'width': 100},
                                {'headerName': 'Date', 'field': 'sale_date', 'width': 120},
                                {'headerName': 'Status', 'field': 'payment_status', 'width': 100}
                            ]
                            
                            self.invoice_table = ui.aggrid({
                                'columnDefs': column_defs,
                                'rowData': [],
                                'rowSelection': 'multiple',
                                'rowMultiSelectWithClick': True
                            }).classes('w-full').style('height: 400px')
                            
                            self.total_label = ui.label('Total: $0.00').classes('text-lg font-bold mt-4')
                            
                            async def update_total():
                                try:
                                    selected_rows = await self.invoice_table.get_selected_rows()
                                    self.selected_invoices = selected_rows
                                    total = sum(float(invoice['total_amount']) for invoice in selected_rows)
                                    self.total_label.set_text(f'Total: ${total:.2f}')
                                except Exception as e:
                                    ui.notify(f'Error calculating total: {str(e)}')
                            
                            self.invoice_table.on('selectionChanged', update_total)
                            
                            def confirm_selection():
                                if self.selected_invoices:
                                    total = sum(float(invoice['total_amount']) for invoice in self.selected_invoices)
                                    self.input_refs['total_amount'].set_value(f'{total:.2f}')
                                    self.invoice_dialog.close()
                                    ui.notify(f'Selected {len(self.selected_invoices)} invoices, Total: ${total:.2f}')
                                else:
                                    ui.notify('Please select at least one invoice', color='warning')
                            
                            with ui.row().classes('w-full justify-end mt-4'):
                                ui.button('OK', on_click=confirm_selection, icon='check').props('color=primary')
                                ui.button('Cancel', on_click=self.invoice_dialog.close).props('flat')

                        # Row under the table for invoice selection and total amount
                        with ui.row().classes('w-full mb-4'):
                            
                            self.input_refs['total_amount'] = ui.input('Total Amount', value='0.00').classes('w-1/4 mr-2')
                            self.input_refs['payment_method'] = ui.select(
                                options=['Cash', 'Card', 'Visa', 'Account', 'Wish', 'OMT'], 
                                value='Cash',
                                label='Payment Method'
                            ).classes('w-1/4')
                        
                        # Add row selection functionality for AG Grid after customer input is defined
                        self.table.on('cellClicked', self.on_row_click)
        
        # Load max customer receipt after UI setup
        self.load_max_customer_receipt()
    
    def clear_input_fields(self):
        # Clear customer input with error handling
        try:
            if self.customer_input:
                self.customer_input.value = ''
            if hasattr(self, 'balance_input') and self.balance_input:
                self.balance_input.value = ''
        except AttributeError:
            ui.notify('UI elements not fully initialized yet', color='warning')
            return
        
        # Clear other input fields
        if 'date' in self.input_refs:
            self.input_refs['date'].set_value(str(datetime.now().date()))
        if 'total_amount' in self.input_refs:
            self.input_refs['total_amount'].set_value('0.00')
        if 'payment_method' in self.input_refs:
            self.input_refs['payment_method'].set_value('Cash')
        self.selected_customer = None
        self.selected_invoices = []
        # Dim the grid when creating new record
        if self.table:
            self.table.classes(add='dimmed')
    
    def clear_input_fields_without_dimming(self):
        # Clear customer input with error handling
        try:
            if self.customer_input:
                self.customer_input.value = ''
            if hasattr(self, 'balance_input') and self.balance_input:
                self.balance_input.value = ''
        except AttributeError:
            ui.notify('UI elements not fully initialized yet', color='warning')
            return
        
        # Clear other input fields
        if 'date' in self.input_refs:
            self.input_refs['date'].set_value(str(datetime.now().date()))
        if 'total_amount' in self.input_refs:
            self.input_refs['total_amount'].set_value('0.00')
        if 'payment_method' in self.input_refs:
            self.input_refs['payment_method'].set_value('Cash')
        self.selected_customer = None
        self.selected_invoices = []
        # Do NOT dim the grid when refreshing
    
   
    def open_invoice_dialog(self):
        if not self.selected_customer:
            ui.notify(f'Please select a customer first')
            return
        
        # Update the dialog label with the customer name
        self.invoice_dialog_label.set_text(f'Select Invoices for {self.selected_customer["customer_name"]}')
        
        # Fetch pending invoices for the selected customer
        invoices_data = []
        sql = f"""
        SELECT s.id, s.invoice_number, s.total_amount, s.sale_date, s.payment_status
        FROM sales s 
        WHERE s.customer_id = {self.selected_customer['id']} AND s.payment_status = 'pending'
        """
        connection.contogetrows(sql, invoices_data)
        
        # Convert pyodbc.Row objects to dictionaries to avoid JSON serialization issues
        invoices = []
        for row in invoices_data:
            invoice_dict = {
                'id': row[0],
                'invoice_number': row[1],
                'total_amount': row[2],
                'sale_date': row[3],
                'payment_status': row[4]
            }
            invoices.append(invoice_dict)
        
        if not invoices:
            ui.notify('No pending invoices found for this customer', color='warning')
            return
        
        # Update the invoice table with the fetched data
        self.invoice_table.options['rowData'] = invoices
        self.invoice_table.update()
        
        # Reset selection and total
        self.selected_invoices = []
        self.total_label.set_text('Total: $0.00')
        
        # Open the dialog
        self.invoice_dialog.open()
    
    def process_receipt(self):
        # Get values from input fields with error handling
        customer_name = self.customer_input.value if self.customer_input else None
        amount = self.input_refs['total_amount'].value if 'total_amount' in self.input_refs else None
        payment_method = self.input_refs['payment_method'].value if 'payment_method' in self.input_refs else None
        
        # Check if all required data is entered
        if not customer_name or not amount or not self.selected_invoices or not self.selected_customer:
            ui.notify('Please select a customer and at least one invoice', color='red')
            return
        
        try:
            # Insert receipt record into customer_receipt table
            payment_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            customer_id = self.selected_customer['id']
            
            insert_receipt_sql = """
            INSERT INTO customer_receipt (manual_reference, payment_date, customer_id, amount, payment_method, status, notes, created_at)
            VALUES (?, ?, ?, ?, ?, 'completed', 'Receipt processed for selected invoices', ?)
            """

            # Generate a reference number
            reference = f"REC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            values=(self.ManualReference_input.value,payment_date,customer_id,float(amount),payment_method,payment_date)
            connection.insertingtodatabase(insert_receipt_sql, values=values)

            # Get the last inserted receipt ID for sales_payment table
            last_receipt_id = connection.getid("SELECT MAX(id) FROM customer_receipt", [])

            # Insert into sales_payment table
            sales_payment_sql = """
            INSERT INTO sales_payment (sales_id, customer_id, invoice_number, total_amount, sale_date, payment_status, debit, credit, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            # For customer receipts, debit = total_amount, credit = 0
            debit = float(amount)
            credit = 0.0
            payment_status = 'completed'

            # Insert payment record for each selected invoice
            for invoice in self.selected_invoices:
                sales_payment_values = (
                    invoice['id'],  # sales_id
                    customer_id,
                    invoice['invoice_number'],
                    float(amount),  # Use the receipt amount
                    payment_date,
                    payment_status,
                    debit,
                    credit,
                    f"Customer receipt payment for invoice {invoice['invoice_number']}"
                )
                connection.insertingtodatabase(sales_payment_sql, sales_payment_values)
            # Update sales status to completed for selected invoices
            for invoice in self.selected_invoices:
                update_sales_sql = """
                UPDATE sales 
                SET payment_status = 'completed', payment_method = ?
                WHERE invoice_number = ?
                """
                connection.insertingtodatabase(update_sales_sql, (payment_method, invoice['invoice_number']))
            
            # Subtract from customer balance (since this is a payment received)
            update_customer_sql = """
            UPDATE customers 
            SET balance = balance - ? 
            WHERE id = ?
            """
            connection.insertingtodatabase(update_customer_sql, (float(amount), customer_id))
            
            ui.notify(f'Receipt of ${float(amount):.2f} processed successfully for {customer_name}.', color='green')
            
            # Reset the form after successful receipt
            self.clear_input_fields()
            self.refresh_table()
            self.table.classes(remove='dimmed')
                
        except Exception as e:
            ui.notify(f'Error processing receipt: {str(e)}', color='red')
    
    def undo_changes(self):
        # Restore customer input if available in initial values with error handling
        try:
            if 'customer_name' in self.initial_values and self.customer_input:
                self.customer_input.value = self.initial_values['customer_name']
            if 'total_amount' in self.input_refs and 'total_amount' in self.initial_values:
                self.input_refs['total_amount'].set_value(self.initial_values['total_amount'])
            if 'payment_method' in self.input_refs and 'payment_method' in self.initial_values:
                self.input_refs['payment_method'].set_value(self.initial_values['payment_method'])
        except AttributeError:
            ui.notify('UI elements not fully initialized yet', color='warning')
            return
        
        # Remove dimming when undoing changes
        if self.table:
            self.table.classes(remove='dimmed')
        ui.notify('Changes undone', color='blue')
    
    async def delete_receipt(self):
        """Delete the selected receipt and revert all related changes"""
        try:
            # Get the currently selected row
            selected_row = await self.table.get_selected_row()
            if not selected_row:
                ui.notify('Please select a receipt to delete', color='warning')
                return
            
            receipt_id = selected_row['id']
            customer_id = selected_row['customer_id']
            amount = selected_row['amount']
            
            # Confirm deletion
            if not ui.run_javascript('confirm("Are you sure you want to delete this receipt? This will revert all related invoice payments.")'):
                return
            
            # Start transaction - revert all changes
            try:
                # 1. Delete the receipt record
                delete_receipt_sql = "DELETE FROM customer_receipt WHERE id = ?"
                connection.insertingtodatabase(delete_receipt_sql, (receipt_id,))
                
                # 2. Revert invoice statuses back to 'pending'
                revert_invoices_sql = """
                UPDATE sales 
                SET payment_status = 'pending', payment_method = NULL 
                WHERE invoice_number IN (
                    SELECT invoice_number 
                    FROM sales 
                    WHERE payment_status = 'completed' 
                    AND customer_id = ?
                    AND payment_method = ?
                )
                """
                connection.insertingtodatabase(revert_invoices_sql, (customer_id, selected_row['payment_method']))
                
                # 3. Add back to customer balance (reverse the payment)
                update_customer_sql = """
                UPDATE customers 
                SET balance = balance + ? 
                WHERE id = ?
                """
                connection.insertingtodatabase(update_customer_sql, (float(amount), customer_id))
                
                ui.notify(f'Receipt #{receipt_id} deleted successfully. All changes have been reverted.', color='green')
                
                # Refresh the table to show updated data
                self.refresh_table()
                
            except Exception as e:
                ui.notify(f'Error deleting receipt: {str(e)}', color='red')
                
        except Exception as e:
            ui.notify(f'Error: {str(e)}', color='red')
    
    def refresh_table(self):
        # Remove dimming first
        if self.table:
            self.table.classes(remove='dimmed')
        
        # Query to fetch customer receipt records with customer name
        sql = """
        SELECT 
            cr.id,
            cr.manual_reference,
            cr.payment_date,
            cr.customer_id,
            cr.amount,
            cr.payment_method,
            cr.status,
            cr.notes,
            cr.created_at,
            c.customer_name as customer_name
        FROM customer_receipt cr
        INNER JOIN customers c ON cr.customer_id = c.id
        ORDER BY cr.created_at DESC
        """
        receipt_data = []
        connection.contogetrows(sql, receipt_data)
        
        # Convert pyodbc.Row objects to dictionaries to avoid JSON serialization issues
        receipts = []
        for row in receipt_data:
            receipt_dict = {
                'id': row[0],
                'manual_reference': row[1],
                'payment_date': row[2],
                'customer_id': row[3],
                'amount': row[4],
                'payment_method': row[5],
                'status': row[6],
                'notes': row[7],
                'created_at': row[8],
                'customer_name': row[9]
            }
            receipts.append(receipt_dict)

        # Update AG Grid with new data
        if self.table:
            self.table.options['rowData'] = receipts
            self.table.update()
        
        # Clear input fields but don't dim the table (since this is a refresh)
        self.clear_input_fields_without_dimming()

    async def on_row_click(self):
        try:
            selected_row = await self.table.get_selected_row()
            if selected_row:
                # Update customer input if customer name is available
                if 'customer_name' in selected_row:
                    self.customer_input.value = selected_row['customer_name']
                
                # Update other input fields with row data
                if 'manual_reference' in selected_row and hasattr(self, 'ManualReference_input'):
                    self.ManualReference_input.value = selected_row['manual_reference']
                if 'payment_date' in selected_row and 'date' in self.input_refs:
                    self.input_refs['date'].set_value(selected_row['payment_date'])
                if 'amount' in selected_row and 'total_amount' in self.input_refs:
                    self.input_refs['total_amount'].set_value(str(selected_row['amount']))
                if 'payment_method' in selected_row and 'payment_method' in self.input_refs:
                    self.input_refs['payment_method'].set_value(selected_row['payment_method'])
                
                # Store initial values for undo functionality
                self.initial_values.update({
                    'customer_name': self.customer_input.value,
                    'total_amount': self.input_refs['total_amount'].value,
                    'payment_method': self.input_refs['payment_method'].value
                })
                
                # Remove dimming when selecting a row
                if self.table:
                    self.table.classes(remove='dimmed')
        except Exception as e:
            ui.notify(f'Error selecting row: {str(e)}')

# Register the page route
@ui.page('/customerreceipt')
def customer_receipt_page_route():
    uiAggridTheme.addingtheme()

    # Check if user is logged in
    user = session_storage.get('user')
    if not user:
        ui.notify('Please login to access this page', color='red')
        ui.run_javascript('window.location.href = "/login"')
        return

    # Get user permissions
    permissions = connection.get_user_permissions(user['role_id'])
    allowed_pages = {page for page, can_access in permissions.items() if can_access}

    # Create enhanced navigation instance
    navigation = EnhancedNavigation(permissions, user)
    navigation.create_navigation_drawer()  # Create drawer first
    navigation.create_navigation_header()  # Then create header with toggle button

    CustomerReceipt()
