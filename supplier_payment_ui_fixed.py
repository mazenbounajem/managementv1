from nicegui import ui
from connection import connection
from datetime import datetime
from uiaggridtheme import uiAggridTheme

class SupplierPayment:
    def __init__(self):
        self.input_refs = {}
        self.initial_values = {}
        self.table = None
        self.selected_supplier = None
        self.selected_invoices = []
        
        
        self.setup_ui()
        self.load_max_supplier_payment()
         
    
    def setup_ui(self):
        uiAggridTheme.addingtheme()
        with ui.header().classes('items-center justify-between'):
            ui.label('Supplier Payment Management').classes('text-2xl font-bold')
            ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).props('flat color=white')

        # Main content area with splitter layout
        with ui.element('div').classes('flex w-full h-screen'):
            # Left drawer for action buttons - rebuilt to match category.py pattern
            with ui.column().classes('w-48 p-4 bg-gray-100 flex-shrink-0'):
                ui.label('Actions').classes('text-lg font-bold mb-4')
                ui.button('New', icon='add', on_click=self.clear_input_fields).classes('bg-blue-500 text-white w-full mb-2')
                ui.button('Process Payment', icon='payment', on_click=self.process_payment).classes('bg-green-500 text-white w-full mb-2')
                ui.button('Undo', icon='undo', on_click=self.undo_changes).classes('bg-yellow-500 text-white w-full mb-2')
                ui.button('Delete', icon='delete', on_click=self.delete_payment).classes('bg-red-500 text-white w-full mb-2')
                ui.button('Refresh', icon='refresh', on_click=self.refresh_table).classes('bg-purple-500 text-white w-full mb-2')
            
            # Main content area with splitter
            with ui.column().classes('flex-1 p-4 overflow-y-auto'):
                # Splitter for grid and form sections
                with ui.splitter(horizontal=True, value=40).classes('w-full h-full') as main_splitter:
                    with main_splitter.separator:
                        ui.icon('drag_handle').classes('text-gray-400 text-sm')
                    
                    # Top section - Pending Invoices Grid
                    with main_splitter.before:
                        ui.label('Pending Invoices').classes('text-xl font-bold mb-2')
                        
                        # Search functionality
                        search_input = ui.input('Search Invoices').classes('w-full mb-2')
                        
                        # Column definitions for AG Grid
                        column_defs = [
                            {'headerName': 'ID', 'field': 'id', 'sortable': True, 'filter': True, 'width': 100},
                            {'headerName': 'Invoice ID', 'field': 'invoice_number', 'sortable': True, 'filter': True, 'width': 150},
                            {'headerName': 'Supplier', 'field': 'supplier_name', 'sortable': True, 'filter': True, 'width': 200},
                            {'headerName': 'Amount', 'field': 'amount', 'sortable': True, 'filter': True, 'width': 120},
                            {'headerName': 'Purchase Date', 'field': 'purchase_date', 'sortable': True, 'filter': True, 'width': 150},
                            {'headerName': 'Creation Date', 'field': 'creation_date', 'sortable': True, 'filter': True, 'width': 150},
                            {'headerName': 'Status', 'field': 'status', 'sortable': True, 'filter': True, 'width': 120}
                        ]
                        
                        # Fetch initial data
                        pending_invoices = []
                        self.refresh_table()
                        
                        # Create AG Grid table with scroll functionality
                        self.table = ui.aggrid({
                            'columnDefs': column_defs,
                            'rowData': pending_invoices,
                            'defaultColDef': {'flex': 1, 'minWidth': 100, 'sortable': True, 'filter': True},
                            'rowSelection': 'single',
                            'domLayout': 'normal',
                            'pagination': True,
                            'paginationPageSize': 5
                        }).classes('w-full ag-theme-quartz-custom').style('height: 200px; overflow-y: auto;')
                        
                        # Add row selection functionality for AG Grid
                        async def on_row_click():
                            try:
                                selected_row = await self.table.get_selected_row()
                                if selected_row:
                                    if 'supplier_name' in self.input_refs and 'supplier_name' in selected_row:
                                        self.input_refs['supplier_name'].set_value(selected_row['supplier_name'])
                                    if 'total_amount' in self.input_refs and 'amount' in selected_row:
                                        self.input_refs['total_amount'].set_value(selected_row['amount'])
                                    if 'date' in self.input_refs and 'purchase_date' in selected_row:
                                        self.input_refs['date'].set_value(str(selected_row['purchase_date']))
                                    
                                    # Set selected invoices for payment processing
                                    self.selected_invoices = [selected_row]
                                    
                                    # Store initial values for undo functionality
                                    self.initial_values.update({
                                        'supplier_name': self.input_refs['supplier_name'].value,
                                        'total_amount': self.input_refs['total_amount'].value,
                                        'payment_method': self.input_refs['payment_method'].value,
                                        'date': self.input_refs['date'].value
                                    })
                            except Exception as e:
                                ui.notify(f'Error selecting row: {str(e)}')
                        
                        self.table.on('cellClicked', on_row_click)
                    
                    # Bottom section - Payment Details
                    with main_splitter.after:
                        ui.label('Payment Details').classes('text-xl font-bold mb-2')
                        
                        # Input fields for payment data
                        with ui.row().classes('w-full mb-4'):
                            self.input_refs['date'] = ui.input('Date', value=str(datetime.now().date())).classes('w-1/3')
                            
                            self.input_refs['supplier_name'] = ui.input('Supplier', placeholder='Supplier').classes('w-28 h-7 text-xs')
                            self.input_refs['supplier_name'].on('click', lambda: self.supplier_dialog.open())
                            self.balance_input = ui.input('balance', placeholder='balance').classes('w-20 h-7 text-xs')
                            ui.button('Select Invoice', icon='receipt', on_click=self.open_invoice_dialog).classes('w-1/4 mr-2 bg-green-500 text-white')
                        self.supplier_dialog = ui.dialog()
                        with self.supplier_dialog, ui.card().classes('w-750'):
                            headers = []
                            connection.contogetheaders("SELECT id, name, phone, balance FROM suppliers", headers)
                            columns = [{'name': header, 'label': header.title(), 'field': header, 'sortable': True} for header in headers]
                            
                            data = []
                            connection.contogetrows("SELECT id, name, phone, balance FROM suppliers", data)
                            rows = []
                            for row in data:
                                row_dict = {}
                                for i, header in enumerate(headers):
                                    row_dict[header] = row[i]
                                rows.append(row_dict)
                            
                            table = ui.table(columns=columns, rows=rows, pagination=5, row_key='id').classes('w-full')
                            ui.input('Search').bind_value(table, 'filter').classes('text-xs')
                            
                            def on_row_click(row_data):
                                selected_row = row_data.args[1]
                                self.input_refs['supplier_name'].set_value(selected_row['name'])
                                self.balance_input.value = selected_row['balance']
                                self.selected_supplier = selected_row
                                self.supplier_dialog.close()
                                
                            table.on('rowClick', on_row_click)    
                            

                        # Row under the table for invoice selection and total amount
                        with ui.row().classes('w-full mb-4'):
                            
                            self.input_refs['total_amount'] = ui.input('Total Amount', value='0.00').classes('w-1/4 mr-2')
                            self.input_refs['payment_method'] = ui.select(
                                options=['Cash', 'Card', 'Visa', 'Account', 'Wish', 'OMT'], 
                                value='Cash',
                                label='Payment Method'
                            ).classes('w-1/4')
    
    def load_max_supplier_payment(self):
        try:
            max_id_result = []
            connection.contogetrows("SELECT MAX(id) FROM supplier_payment", max_id_result)
            max_id = max_id_result[0][0] if max_id_result and max_id_result[0][0] else 0
            if max_id > 0:
                payment_data = []
                connection.contogetrows(
                    f"SELECT sp.id, sp.manual_reference, sp.payment_date, s.name, sp.amount, sp.payment_method, sp.status FROM supplier_payment sp INNER JOIN suppliers s ON s.id = sp.supplier_id WHERE sp.id = {max_id}",
                    payment_data
                )
                
                if payment_data:
                    row_data = {
                        'id': payment_data[0][0],
                        'manual_reference': payment_data[0][1],
                        'payment_date': payment_data[0][2],
                        'supplier_name': payment_data[0][3],
                        'amount': payment_data[0][4],
                        'payment_method': payment_data[0][5],
                        'status': payment_data[0][6]
                    }
                    
                    # Update UI fields with the loaded payment data
                    self.input_refs['supplier_name'].set_value(row_data['supplier_name'])
                    self.input_refs['total_amount'].set_value(f'{row_data["amount"]:.2f}')
                    self.input_refs['payment_method'].set_value(row_data['payment_method'])
                    
                    ui.notify(f'✅ Automatically loaded payment ID: {max_id} - Amount: ${row_data["amount"]:.2f} - Status: {row_data["status"]}')
                else:
                    ui.notify('No payments found in database')
            else:
                ui.notify('No payments found in database')
                
        except Exception as e:
            ui.notify(f'Error loading max supplier payment: {str(e)}')

    def clear_input_fields(self):
        if 'supplier_name' in self.input_refs:
            self.input_refs['supplier_name'].set_value('')
        if 'date' in self.input_refs:
            self.input_refs['date'].set_value(str(datetime.now().date()))
        if 'total_amount' in self.input_refs:
            self.input_refs['total_amount'].set_value('0.00')
        if 'payment_method' in self.input_refs:
            self.input_refs['payment_method'].set_value('Cash')
        self.selected_supplier = None
        self.selected_invoices = []
        # Dim the grid when creating new record
        if self.table:
            self.table.classes('dimmed')
    
   
    def open_invoice_dialog(self):
        if not self.selected_supplier:
            ui.notify(f'Please select a supplier first')
            return
            
        with ui.dialog() as invoice_dialog, ui.card().classes('w-full max-w-6xl'):
            print(self.selected_supplier["name"])
            ui.label(f'Select Invoices for {self.selected_supplier["name"]}').classes('text-xl font-bold mb-4')
            
            # Fetch pending invoices for the selected supplier
            invoices_data = []
            sql = f"""
            SELECT p.id, p.invoice_number, p.total_amount, p.purchase_date, p.payment_status
            FROM purchases p 
            WHERE p.supplier_id = {self.selected_supplier['id']} AND p.payment_status = 'pending'
            """
            connection.contogetrows(sql, invoices_data)
            
            # Convert pyodbc.Row objects to dictionaries to avoid JSON serialization issues
            invoices = []
            for row in invoices_data:
                invoice_dict = {
                    'id': row[0],
                    'invoice_number': row[1],
                    'total_amount': row[2],
                    'purchase_date': row[3],
                    'payment_status': row[4]
                }
                invoices.append(invoice_dict)
            print(invoices)
            if not invoices:
                ui.label('No pending invoices found for this supplier').classes('text-gray-500 mb-4')
                ui.button('Close', on_click=invoice_dialog.close).props('color=primary')
                return
            
            # Create AG Grid with checkboxes for invoice selection
            column_defs = [
                {'headerName': '', 'field': 'selected', 'checkboxSelection': True, 'width': 50},
                {'headerName': 'Invoice #', 'field': 'invoice_number', 'width': 120},
                {'headerName': 'Amount', 'field': 'total_amount', 'width': 100},
                {'headerName': 'Date', 'field': 'purchase_date', 'width': 120},
                {'headerName': 'Status', 'field': 'payment_status', 'width': 100}
            ]
            
            invoice_table = ui.aggrid({
                'columnDefs': column_defs,
                'rowData': invoices,
                'rowSelection': 'multiple',
                'rowMultiSelectWithClick': True,
                'getRowId': 'function(params) { return params.data.id; }'
            }).classes('w-full').style('height: 400px')
            
            total_label = ui.label('Total: $0.00').classes('text-lg font-bold mt-4')
            
            async def update_total():
                try:
                    selected_rows = await invoice_table.get_selected_rows()
                    self.selected_invoices = selected_rows
                    total = sum(float(invoice['total_amount']) for invoice in selected_rows)
                    total_label.set_text(f'Total: ${total:.2f}')
                except Exception as e:
                    ui.notify(f'Error calculating total: {str(e)}')
            
            invoice_table.on('selectionChanged', update_total)
            
            def confirm_selection():
                if self.selected_invoices:
                    total = sum(float(invoice['total_amount']) for invoice in self.selected_invoices)
                    self.input_refs['total_amount'].set_value(f'{total:.2f}')
                    invoice_dialog.close()
                    ui.notify(f'Selected {len(self.selected_invoices)} invoices, Total: ${total:.2f}')
                else:
                    ui.notify('Please select at least one invoice', color='warning')
            
            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('OK', on_click=confirm_selection, icon='check').props('color=primary')
                ui.button('Cancel', on_click=invoice_dialog.close).props('flat')
    
    def process_payment(self):
        # Get values from input fields
        supplier_name = self.input_refs['supplier_name'].value
        amount = self.input_refs['total_amount'].value
        payment_method = self.input_refs['payment_method'].value

        # Check if all required data is entered
        if not supplier_name or not amount or not self.selected_invoices:
            ui.notify('Please select a supplier and at least one invoice', color='red')
            return

        try:
            # Insert payment record into supplier_payment table and get the payment id
            supplier_id = self.selected_supplier['id']
            payment_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            manual_reference = f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}"

            insert_payment_sql = """
            INSERT INTO supplier_payment (manual_reference, payment_date, supplier_id, amount, payment_method, status, notes, created_at)
            VALUES (?, ?, ?, ?, ?, 'completed', 'Payment processed for selected invoices', ?)
            """
            connection.insertingtodatabase(insert_payment_sql, (manual_reference, payment_date, supplier_id, float(amount), payment_method, payment_date))

            # Get the payment id using MAX(id) after insert
            payment_id_result = []
            connection.contogetrows("SELECT MAX(id) FROM supplier_payment", payment_id_result)
            payment_id = payment_id_result[0][0] if payment_id_result and payment_id_result[0][0] else None

            if not payment_id:
                raise Exception("Failed to retrieve payment id")

            # Insert records into purchase_payment table for each selected invoice
            for invoice in self.selected_invoices:
                insert_purchase_payment_sql = """
                INSERT INTO purchase_payment (purchase_id, purchase_invoice_number, total_amount, purchase_date, created_date, supplier_id, status, amount_paid, payment_method)
                VALUES (?, ?, ?, ?, ?, ?, 'completed', ?, ?)
                """
                connection.insertingtodatabase(insert_purchase_payment_sql, (
                    invoice['id'],
                    invoice['invoice_number'],
                    invoice['total_amount'],
                    invoice['purchase_date'],
                    payment_date,
                    supplier_id,
                    invoice['total_amount'],  # amount_paid
                    payment_method
                ))

            # Update purchase status to completed and notes with payment id for selected invoices
            for invoice in self.selected_invoices:
                update_purchase_sql = """
                UPDATE purchases
                SET payment_status = 'completed', payment_method = ?, notes = ?
                WHERE invoice_number = ?
                """
                notes = f"Payment ID: {payment_id}"
                # Debug: Check current notes before update
                check_sql = "SELECT notes FROM purchases WHERE invoice_number = ?"
                current_notes_result = []
                connection.contogetrows_with_params(check_sql, current_notes_result, (invoice['invoice_number'],))
                current_notes = current_notes_result[0][0] if current_notes_result else "No record found"

                # Fix: Use execute_update to ensure update is committed properly
                rows_affected = connection.db_manager.execute_update(update_purchase_sql, (payment_method, notes, invoice['invoice_number']))
                if rows_affected == 0:
                    ui.notify(f"Warning: No rows updated for invoice {invoice['invoice_number']} (current notes: {current_notes})", color='orange')
                else:
                    ui.notify(f"✅ Updated invoice {invoice['invoice_number']} with payment ID {payment_id}", color='green')

            # Deduct from supplier balance
            update_supplier_sql = """
            UPDATE suppliers
            SET balance = balance - ?
            WHERE id = ?
            """
            connection.insertingtodatabase(update_supplier_sql, (float(amount), supplier_id))

            ui.notify(f'Payment of ${float(amount):.2f} processed successfully for {supplier_name}. Payment ID: {payment_id}', color='green')

            # Reset the form after successful payment
            self.clear_input_fields()
            self.refresh_table()

        except Exception as e:
            ui.notify(f'Error processing payment: {str(e)}', color='red')
    
    def undo_changes(self):
        if 'supplier_name' in self.input_refs and 'supplier_name' in self.initial_values:
            self.input_refs['supplier_name'].set_value(self.initial_values['supplier_name'])
        if 'total_amount' in self.input_refs and 'total_amount' in self.initial_values:
            self.input_refs['total_amount'].set_value(self.initial_values['total_amount'])
        if 'payment_method' in self.input_refs and 'payment_method' in self.initial_values:
            self.input_refs['payment_method'].set_value(self.initial_values['payment_method'])
        if 'date' in self.input_refs and 'date' in self.initial_values:
            self.input_refs['date'].set_value(self.initial_values['date'])
        # Remove dimming when undoing changes
        if self.table:
            self.table.classes(remove='dimmed')
        ui.notify('Changes undone', color='blue')
    
    def delete_payment(self):
        """Delete payment functionality - placeholder for future implementation"""
        ui.notify('Delete functionality not yet implemented', color='warning')
    
    
    
    def refresh_table(self):
        # Query to fetch pending invoices (purchases with payment_status = 'pending')
        sql = """
        SELECT p.id, p.invoice_number, s.name, p.total_amount, p.purchase_date, p.creation_date, p.payment_status
        FROM purchases p
        INNER JOIN suppliers s ON p.supplier_id = s.id
        WHERE p.payment_status = 'pending'
        """
        if self.selected_supplier:
            sql += f" AND p.supplier_id = {self.selected_supplier['id']}"
        pending_invoices_data = []
        connection.contogetrows(sql, pending_invoices_data)

        # Convert pyodbc.Row objects to dictionaries to avoid JSON serialization issues
        pending_invoices = []
        for row in pending_invoices_data:
            invoice_dict = {
                'id': row[0],
                'invoice_number': row[1],
                'supplier_name': row[2],
                'amount': row[3],
                'purchase_date': row[4],
                'creation_date': row[5],
                'status': row[6]
            }
            pending_invoices.append(invoice_dict)

        # Update AG Grid with new data
        if self.table:
            self.table.options['rowData'] = pending_invoices
            self.table.update()

        # Remove dimming and clear input fields
        if self.table:
            self.table.classes(remove='dimmed')
        self.clear_input_fields()

# Register the page route
@ui.page('/supplierpayment')
def supplier_payment_page_route():
    SupplierPayment()
