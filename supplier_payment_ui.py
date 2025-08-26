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
                            {'headerName': 'Invoice ID', 'field': 'invoice_id', 'sortable': True, 'filter': True, 'width': 150},
                            {'headerName': 'Supplier', 'field': 'supplier_name', 'sortable': True, 'filter': True, 'width': 200},
                            {'headerName': 'Amount', 'field': 'amount', 'sortable': True, 'filter': True, 'width': 120},
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
                                    
                                    # Store initial values for undo functionality
                                    self.initial_values.update({
                                        'supplier_name': self.input_refs['supplier_name'].value,
                                        'total_amount': self.input_refs['total_amount'].value,
                                        'payment_method': self.input_refs['payment_method'].value
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
                            
                            self.supplier_input = ui.input('Supplier', placeholder='Supplier').classes('w-28 h-7 text-xs')
                            self.supplier_input.on('click', lambda: self.supplier_dialog.open())
                            self.balance_input=ui.input('balance', placeholder='balance').classes('w-20 h-7 text-xs')
                            ui.button('Select Invoice', icon='receipt', on_click=self.open_invoice_dialog).classes('w-1/4 mr-2 bg-green-500 text-white')
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
                            
                            table = ui.table(columns=columns, rows=rows, pagination=5).classes('w-full')
                            ui.input('Search').bind_value(table, 'filter').classes('text-xs')
                            
                            def on_row_click(row_data):
                                selected_row = row_data.args[1]
                                self.supplier_input.value = selected_row['name']
                                self.balance_input.value = selected_row['balance']
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
        self.supplier_input
        if not self.supplier_input:
            
            ui.notify(f'Please select a supplier first,{self.supplier_input}')
            return
            
        with ui.dialog() as invoice_dialog, ui.card().classes('w-full max-w-6xl'):
            print(self.supplier_input["name"])
            ui.label(f'Select Invoices for {self.supplier_input["name"]}').classes('text-xl font-bold mb-4')
            
            # Fetch pending invoices for the selected supplier
            invoices = []
            sql = """
            SELECT p.id, p.invoice_number, p.total_amount, p.purchase_date, p.payment_status
            FROM purchases p 
            WHERE p.supplier_id = ? AND p.payment_status = 'pending'
            """
            connection.contogetrows(sql, invoices, [self.supplier_input['id']])
            
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
                'rowMultiSelectWithClick': True
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
            # Update purchase status to completed for selected invoices
            for invoice in self.selected_invoices:
                update_purchase_sql = """
                UPDATE purchases 
                SET payment_status = 'completed', payment_method = ?
                WHERE invoice_number = ?
                """
                connection.insertingtodatabase(update_purchase_sql, (payment_method, invoice['invoice_number']))
            
            # Deduct from supplier balance
            supplier_id = self.selected_supplier['id']
            update_supplier_sql = """
            UPDATE suppliers 
            SET balance = balance - ? 
            WHERE id = ?
            """
            connection.insertingtodatabase(update_supplier_sql, (float(amount), supplier_id))
            
            ui.notify(f'Payment of ${float(amount):.2f} processed successfully for {supplier_name}.', color='green')
            
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
        SELECT p.invoice_number as invoice_id, s.name as supplier_name, p.total_amount as amount, p.payment_status as status 
        FROM purchases p 
        INNER JOIN suppliers s ON p.supplier_id = s.id 
        WHERE p.payment_status = 'pending'
        """
        pending_invoices = []
        connection.contogetrows(sql, pending_invoices)

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
