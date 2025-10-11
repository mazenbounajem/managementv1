from nicegui import ui
from connection import connection
from datetime import datetime
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation

class SupplierPayment:
    def __init__(self):
        self.input_refs = {}
        self.initial_values = {}
        self.table = None
        self.selected_supplier = None
        self.selected_invoices = []
        self.supplier_input = None  # Initialize to avoid AttributeError
        self.max_id = 0  # Store the maximum ID
        
        self.max_supplier_payment_id = self.get_max_supplier_payment_id()
        self.setup_ui()
          # Get max ID on load
        self.get_max_supplier_payment_id
    def get_max_supplier_payment_id(self):
        try:
            max_id_result = []
            connection.contogetrows("SELECT MAX(id) FROM supplier_payment", max_id_result)
            return max_id_result[0][0] if max_id_result and max_id_result[0][0] else 0
        except Exception as e:
            return 0
    
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
                    self.supplier_input.value = row_data['supplier_name']
                    self.input_refs['total_amount'].set_value(f'{row_data["amount"]:.2f}')
                    self.input_refs['payment_method'].set_value(row_data['payment_method'])
                    
                    ui.notify(f'✅ Automatically loaded payment ID: {max_id} - Amount: ${row_data["amount"]:.2f} - Status: {row_data["status"]}')
                else:
                    ui.notify('No payments found in database')
            else:
                ui.notify('No payments found in database')
                
        except Exception as e:
            ui.notify(f'Error loading max supplier payment: {str(e)}')

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
                        
                        
                        # Search functionality
                        search_input = ui.input('Search Invoices').classes('w-full mb-2')
                        
                        # Column definitions for AG Grid
                        column_defs = [
                            {'headerName': 'ID', 'field': 'id', 'sortable': True, 'filter': True, 'width': 80},
                            {'headerName': 'Reference', 'field': 'manual_reference', 'sortable': True, 'filter': True, 'width': 150},
                            {'headerName': 'Payment Date', 'field': 'payment_date', 'sortable': True, 'filter': True, 'width': 150},
                            {'headerName': 'Supplier', 'field': 'supplier_name', 'sortable': True, 'filter': True, 'width': 200},
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
                    
                    # Bottom section - Payment Details
                    with main_splitter.after:
                        ui.label('Payment Details').classes('text-xl font-bold mb-2')
                        
                        # Input fields for payment data
                        with ui.row().classes('w-full mb-4'):
                            self.ManualReference_input=ui.input('manual reference', placeholder='ManualReference').classes('w-20 h-7 text-xs')
                            self.input_refs['date'] = ui.input('Date', value=str(datetime.now().date())).classes('w-1/3')
                            
                            self.supplier_input = ui.input('Supplier', placeholder='Supplier').classes('w-28 h-7 text-xs')
                            self.supplier_input.on('click', lambda: self.supplier_dialog.open())
                            self.balance_input=ui.input('balance', placeholder='balance').classes('w-20 h-7 text-xs')
                            ui.button('Select Invoice', icon='receipt', on_click=self.open_invoice_dialog).classes('w-1/4 mr-2 bg-green-500 text-white')
                        
                        # Create supplier dialog
                        self.supplier_dialog = ui.dialog()
                        with self.supplier_dialog, ui.card().classes('w-750'):
                            headers = []
                            connection.contogetheaders("SELECT id, name, phone,balance FROM suppliers", headers)
                            columns = [{'name': header, 'label': header.title(), 'field': header, 'sortable': True} for header in headers]
                            
                            data = []
                            connection.contogetrows("SELECT id, name, phone,balance FROM suppliers", data)
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
                                self.supplier_input.value = selected_row['name']
                                self.balance_input.value = selected_row['balance']
                                self.selected_supplier = selected_row
                                self.supplier_dialog.close()
                                
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
                                {'headerName': 'Date', 'field': 'purchase_date', 'width': 120},
                                {'headerName': 'Status', 'field': 'payment_status', 'width': 100}
                            ]
                            
                            self.invoice_table = ui.aggrid({
                                'columnDefs': column_defs,
                                'rowData': [],
                                'rowSelection': 'multiple',
                                'rowMultiSelectWithClick': True,
                                'getRowId': 'function(params) { return params.data.id; }'
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
                        
                        # Add row selection functionality for AG Grid after supplier input is defined
                        self.table.on('cellClicked', self.on_row_click)
        
        # Load max supplier payment after UI setup
        self.load_max_supplier_payment()
    
    def clear_input_fields(self):
        # Clear supplier input with error handling
        try:
            if self.supplier_input:
                self.supplier_input.value = ''
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
        self.selected_supplier = None
        self.selected_invoices = []
        # Dim the grid when creating new record
        if self.table:
            self.table.classes(add='dimmed')
    
   
    def open_invoice_dialog(self):
        if not self.selected_supplier:
            ui.notify(f'Please select a supplier first')
            return
        
        # Update the dialog label with the supplier name
        self.invoice_dialog_label.set_text(f'Select Invoices for {self.selected_supplier["name"]}')
        
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
        
        if not invoices:
            ui.notify('No pending invoices found for this supplier', color='warning')
            return
        
        # Update the invoice table with the fetched data
        self.invoice_table.options['rowData'] = invoices
        self.invoice_table.update()
        
        # Reset selection and total
        self.selected_invoices = []
        self.total_label.set_text('Total: $0.00')
        
        # Open the dialog
        self.invoice_dialog.open()
    
    def process_payment(self):
        # Get values from input fields with error handling
        supplier_name = self.supplier_input.value if self.supplier_input else None
        amount = self.input_refs['total_amount'].value if 'total_amount' in self.input_refs else None
        payment_method = self.input_refs['payment_method'].value if 'payment_method' in self.input_refs else None
        
        # Check if all required data is entered
        if not supplier_name or not amount or not self.selected_invoices or not self.selected_supplier:
            ui.notify('Please select a supplier and at least one invoice', color='red')
            return
        
        try:
            # Insert payment record into supplier_payment table and get the payment id
            supplier_id = self.selected_supplier['id']
            payment_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            manual_reference = f"PAY-{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # Get notes from selected invoices
            invoice_notes = []
            for invoice in self.selected_invoices:
                check_notes_sql = "SELECT notes FROM purchases WHERE invoice_number = ?"
                notes_result = []
                connection.contogetrows_with_params(check_notes_sql, notes_result, (invoice['invoice_number'],))
                if notes_result and notes_result[0][0]:
                    invoice_notes.append(f"Invoice {invoice['invoice_number']}: {notes_result[0][0]}")
            combined_notes = 'Payment processed for selected invoices. ' + '; '.join(invoice_notes) if invoice_notes else 'Payment processed for selected invoices'

            insert_payment_sql = """
            INSERT INTO supplier_payment (manual_reference, payment_date, supplier_id, amount, payment_method, status, notes, created_at)
            VALUES (?, ?, ?, ?, ?, 'completed', ?, ?)
            """
            connection.insertingtodatabase(insert_payment_sql, (manual_reference, payment_date, supplier_id, float(amount), payment_method, combined_notes, payment_date))

            # Get the payment id using MAX(id) after insert
            payment_id_result = []
            connection.contogetrows("SELECT MAX(id) FROM supplier_payment", payment_id_result)
            payment_id = payment_id_result[0][0] if payment_id_result and payment_id_result[0][0] else None

            if not payment_id:
                raise Exception("Failed to retrieve payment id")

            # Insert records into purchase_payment table for each selected invoice
            for invoice in self.selected_invoices:
                # Get notes for purchase_payment
                check_notes_sql = "SELECT notes FROM purchases WHERE invoice_number = ?"
                notes_result = []
                connection.contogetrows_with_params(check_notes_sql, notes_result, (invoice['invoice_number'],))
                notes_pp = notes_result[0][0] if notes_result and notes_result[0][0] else 'Payment processed'

                insert_purchase_payment_sql = """
                INSERT INTO purchase_payment (purchase_id, purchase_invoice_number, total_amount, purchase_date, created_date, supplier_id, status, amount_paid, payment_method, debit, credit, notes)
                VALUES (?, ?, ?, ?, ?, ?, 'completed', ?, ?, ?, ?, ?)
                """
                connection.insertingtodatabase(insert_purchase_payment_sql, (
                    invoice['id'],
                    invoice['invoice_number'],
                    invoice['total_amount'],
                    invoice['purchase_date'],
                    payment_date,
                    supplier_id,
                    invoice['total_amount'],  # amount_paid
                    payment_method,
                    0,  # debit
                    float(invoice['total_amount']),  # credit
                    notes_pp
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

                connection.insertingtodatabase(update_purchase_sql, (payment_method, notes, invoice['invoice_number']))
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
        # Restore supplier input if available in initial values with error handling
        try:
            if 'supplier_name' in self.initial_values and self.supplier_input:
                self.supplier_input.value = self.initial_values['supplier_name']
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
    
    def delete_payment(self):
        """Delete payment functionality - placeholder for future implementation"""
        ui.notify('Delete functionality not yet implemented', color='warning')
    
    def refresh_table(self):
        self.table.classes(remove='dimmed')
        # Query to fetch supplier payment records with supplier name
        sql = """
        SELECT 
            sp.id,
            sp.manual_reference,
            sp.payment_date,
            sp.supplier_id,
            sp.amount,
            sp.payment_method,
            sp.status,
            sp.notes,
            sp.created_at,
            s.name as supplier_name
        FROM supplier_payment sp
        INNER JOIN suppliers s ON sp.supplier_id = s.id
        ORDER BY sp.created_at DESC
        """
        payment_data = []
        connection.contogetrows(sql, payment_data)
        
        # Convert pyodbc.Row objects to dictionaries to avoid JSON serialization issues
        payments = []
        for row in payment_data:
            payment_dict = {
                'id': row[0],
                'manual_reference': row[1],
                'payment_date': row[2],
                'supplier_id': row[3],
                'amount': row[4],
                'payment_method': row[5],
                'status': row[6],
                'notes': row[7],
                'created_at': row[8],
                'supplier_name': row[9]
            }
            payments.append(payment_dict)

        # Update AG Grid with new data
        if self.table:
            self.table.options['rowData'] = payments
            self.table.update()
        
        # Remove dimming and clear input fields
        if self.table:
            self.table.classes(remove='dimmed')
        self.clear_input_fields()

    async def on_row_click(self):
        try:
            selected_row = await self.table.get_selected_row()
            if selected_row:
                # Update supplier input if supplier name is available
                if 'supplier_name' in selected_row:
                    self.supplier_input.value = selected_row['supplier_name']
                
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
                    'supplier_name': self.supplier_input.value,
                    'total_amount': self.input_refs['total_amount'].value,
                    'payment_method': self.input_refs['payment_method'].value
                })
                
                # Remove dimming when selecting a row
                if self.table:
                    self.table.classes(remove='dimmed')
        except Exception as e:
            ui.notify(f'Error selecting row: {str(e)}')

# Register the page route
@ui.page('/supplierpayment')
def supplier_payment_page_route():
    SupplierPayment()
