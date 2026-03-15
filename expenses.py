from nicegui import ui
from pathlib import Path
from datetime import date as dt
from connection import connection
from datetime import datetime
from decimal import Decimal
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput, ModernStats
from modern_design_system import ModernDesignSystem as MDS

@ui.page('/expenses')
def expenses_page():
    with ModernPageLayout("Expense Management"):
        ExpensesUI()

class ExpensesUI:

    def __init__(self):

        # --- Global Variables ---
        self.columns = [
            {'headerName': 'Date', 'field': 'expense_date', 'width': 80, 'headerClass': 'blue-header'},
            {'headerName': 'Type', 'field': 'expense_type', 'width': 100, 'headerClass': 'blue-header'},
            {'headerName': 'Description', 'field': 'description', 'width': 150, 'headerClass': 'blue-header'},
            {'headerName': 'Amount', 'field': 'amount', 'width': 80,  'headerClass': 'blue-header'},
            {'headerName': 'Payment', 'field': 'payment_method', 'width': 80,  'headerClass': 'blue-header'},
            {'headerName': 'Status', 'field': 'payment_status', 'width': 80,  'headerClass': 'blue-header'},
            {'headerName': 'Invoice', 'field': 'invoice_number', 'width': 100,  'headerClass': 'blue-header'},
            {'headerName': 'Auxiliary', 'field': 'auxiliary_id', 'width': 80, 'headerClass': 'blue-header'}
        ]
        self.rows = []
        self.total_amount = 0
        self.current_expense_id = None
        self.new_mode = True

        # Initialize UI
        self.create_ui()

    def generate_invoice_number(self):
        try:
            existing_invoices = connection.contogetrows(
                "SELECT invoice_number FROM expenses WHERE invoice_number IS NOT NULL", []
            )
            existing_set = {row[0] for row in existing_invoices}
            max_num = 0
            for invoice in existing_set:
                if invoice.startswith('EXP-'):
                    try:
                        num = int(invoice.split('-')[1])
                        max_num = max(max_num, num)
                    except (ValueError, IndexError):
                        continue
            next_num = max_num + 1
            while f"EXP-{next_num:06d}" in existing_set:
                next_num += 1
            return f"EXP-{next_num:06d}"
        except Exception as e:
            import time
            return f"EXP-{int(time.time())}"

    def add_expense(self, e=None):
        try:
            expense_date = str(self.date_input.value)
            expense_type = self.type_input.value
            description = self.description_input.value
            amount = float(self.amount_input.value) if self.amount_input.value else 0
            payment_method = self.payment_method.value
            invoice_number = self.invoice_input.value
            notes = self.notes_input.value
            
            if not expense_type or amount <= 0:
                ui.notify('Please fill in expense type and amount with valid values')
                return
            
            self.rows.append({
                'expense_date': expense_date,
                'expense_type': expense_type,
                'description': description,
                'amount': amount,
                'payment_method': payment_method,
                'payment_status': 'completed',
                'invoice_number': invoice_number,
                'notes': notes,
                'auxiliary_id': self.label_to_aux_id.get(self.auxiliary_select.value, None)
            })
            
            self.total_amount += amount
            self.total_label.text = f"Total: ${self.total_amount:.2f}"
            self.summary_label.text = f'{len(self.rows)} expense(s)'
            
            # Update the grid with the new data
            self.aggrid.options['rowData'] = self.rows
            self.aggrid.update()
            
            # Clear only the input fields, not the rows
            self.date_input.value = str(dt.today())
            self.type_input.value = ''
            self.description_input.value = ''
            self.amount_input.value = 0.0
            self.payment_method.value = 'Cash'
            self.invoice_input.value = ''
            self.notes_input.value = ''
            
        except ValueError as e:
            ui.notify(f'Invalid input: {str(e)}')
    
    def clear_inputs(self):
        self.date_input.value = str(dt.today())
        self.type_input.value = ''
        self.description_input.value = ''
        self.amount_input.value = 0.0
        self.payment_method.value = 'Cash'
        self.invoice_input.value = ''
        self.notes_input.value = ''
        self.auxiliary_select.value = None
        
        self.rows.clear()
        self.aggrid.options['rowData'] = self.rows
        self.aggrid.update()
        
        self.total_amount = 0
        self.total_label.text = "Total: $0.00"
        
        self.current_expense_id = None
        self.new_mode = True

    async def on_row_click_edit_cells(self, e):
        try:
            selected_row = await self.aggrid.get_selected_row()
            
            if selected_row and isinstance(selected_row, dict) and 'expense_type' in selected_row:
                ui.notify(f"Selected: {selected_row.get('expense_type', 'Unknown')} - Amount: ${selected_row.get('amount', 0):.2f}")
                self.open_edit_dialog(selected_row)
            else:
                ui.notify("Please select a valid row to edit")
                
        except Exception as ex:
            ui.notify(f"Error opening edit dialog: {str(ex)}")

    def open_edit_dialog(self, row_data):
        dialog = ui.dialog()
        
        with dialog, ui.card().classes('w-96 p-6'):
            ui.label('Edit Expense').classes('text-xl font-bold mb-4')
            
            with ui.column().classes('w-full gap-3'):
                date_input = ui.input('Date', value=row_data['expense_date']).classes('w-full')
                type_input = ui.input('Type', value=row_data['expense_type']).classes('w-full')
                description_input = ui.input('Description', value=row_data['description']).classes('w-full')
                amount_input = ui.number('Amount', value=row_data['amount'], min=0, step=0.01).classes('w-full')
                payment_input = ui.input('Payment Method', value=row_data['payment_method']).classes('w-full')
                invoice_input = ui.input('Invoice', value=row_data['invoice_number']).classes('w-full')
                
                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button('Cancel', on_click=dialog.close)
                    ui.button('Delete', on_click=lambda: self.delete_row(row_data, dialog)).props('color=negative')
                    ui.button('Save', on_click=lambda: self.save_edited_row(
                        row_data, 
                        date_input.value,
                        type_input.value,
                        description_input.value,
                        amount_input.value,
                        payment_input.value,
                        invoice_input.value,
                        dialog
                    )).props('color=primary')
        
        dialog.open()

    def save_edited_row(self, original_row, new_date, new_type, new_description, new_amount, new_payment, new_invoice, dialog):
        try:
            row_index = next(i for i, row in enumerate(self.rows) 
                           if row['expense_date'] == original_row['expense_date'] and 
                              row['expense_type'] == original_row['expense_type'] and
                              row['amount'] == original_row['amount'])
            
            old_amount = self.rows[row_index]['amount']
            
            self.rows[row_index]['expense_date'] = new_date
            self.rows[row_index]['expense_type'] = new_type
            self.rows[row_index]['description'] = new_description
            self.rows[row_index]['amount'] = float(new_amount)
            self.rows[row_index]['payment_method'] = new_payment
            self.rows[row_index]['invoice_number'] = new_invoice
            
            self.total_amount = self.total_amount - old_amount + float(new_amount)
            self.total_label.text = f"Total: ${self.total_amount:.2f}"
            
            self.aggrid.options['rowData'] = self.rows
            self.aggrid.update()
            
            dialog.close()
            ui.notify('Expense updated successfully')
            
        except Exception as e:
            ui.notify(f'Error updating expense: {str(e)}')

    def delete_row(self, row_data, dialog):
        try:
            row_index = next(i for i, row in enumerate(self.rows) 
                           if row['expense_date'] == row_data['expense_date'] and 
                              row['expense_type'] == row_data['expense_type'] and
                              row['amount'] == row_data['amount'])
            
            self.total_amount -= self.rows[row_index]['amount']
            self.total_label.text = f"Total: ${self.total_amount:.2f}"
            
            del self.rows[row_index]
            self.aggrid.options['rowData'] = self.rows
            self.aggrid.update()
            
            dialog.close()
            ui.notify('Expense removed successfully')
            
        except Exception as e:
            ui.notify(f'Error removing expense: {str(e)}')

    def get_max_expense_id(self):
        try:
            max_id_result = []
            connection.contogetrows("SELECT MAX(id) FROM expenses", max_id_result)
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

    def delete_expense(self):
        try:
            expense_id = None
            
            if hasattr(self, 'current_expense_id') and self.current_expense_id:
                expense_id = self.current_expense_id
            
            if not expense_id:
                ui.notify('No expense data available to delete')
                return
            
            dialog = ui.dialog()
            
            with dialog, ui.card().classes('w-96 p-6'):
                ui.label('Confirm Delete').classes('text-xl font-bold mb-4 text-red-600')
                ui.label(f'Are you sure you want to delete expense ID: {expense_id}?').classes('mb-2')
                ui.label('This will permanently remove the expense from the database.').classes('text-sm text-gray-600 mb-4')
                
                with ui.row().classes('w-full justify-end gap-3 mt-6'):
                    ui.button('No', on_click=dialog.close).props('flat')
                    ui.button('Yes, Delete', on_click=lambda: self.perform_delete_expense(expense_id, dialog)).props('color=negative')
            
            dialog.open()
            
        except Exception as e:
            ui.notify(f'Error preparing delete: {str(e)}')

    def perform_delete_expense(self, expense_id, dialog):
        try:
            # Delete the expense
            connection.deleterow("DELETE FROM expenses WHERE id = ?", [expense_id])
            
            ui.notify(f'Expense {expense_id} deleted successfully')
            dialog.close()
            
            self.expenses_aggrid.update()
            self.clear_inputs()
            self.refresh_expenses_table()
            
        except Exception as e:
            ui.notify(f'Error deleting expense: {str(e)}')
            dialog.close()

    def perform_undo(self, dialog):
        self.rows.clear()
        self.aggrid.options['rowData'] = self.rows
        self.aggrid.update()
        
        self.total_amount = 0
        self.total_label.text = "Total: $0.00"
        
        self.clear_inputs()
        dialog.close()
        self.expenses_aggrid.classes(remove='dimmed')
        ui.notify('Undo completed successfully')

    def refresh_expenses_table(self):
        try:
            raw_expenses_data = []
            connection.contogetrows(
                "SELECT id, expense_date, expense_type, description, amount, payment_method, payment_status, invoice_number, auxiliary_id FROM expenses ORDER BY id DESC",
                raw_expenses_data
            )

            expenses_data = []
            for row in raw_expenses_data:
                expenses_data.append({
                    'id': row[0],
                    'expense_date': str(row[1]),
                    'expense_type': str(row[2]),
                    'description': str(row[3]),
                    'amount': float(row[4]),
                    'payment_method': str(row[5]),
                    'payment_status': str(row[6]),
                    'invoice_number': str(row[7]),
                    'auxiliary_id': str(row[8]) if row[8] else ''
                })

            self.expenses_aggrid.options['rowData'] = expenses_data
            self.expenses_aggrid.update()
            self.expenses_aggrid.classes(remove='dimmed')

            ui.notify('Expenses table refreshed successfully')

        except Exception as e:
            ui.notify(f'Error refreshing expenses table: {str(e)}')

    def save_expense(self):
        try:
            if not self.rows:
                ui.notify('No expenses to save!')
                return

            for expense in self.rows:
                expense_date = expense['expense_date']
                expense_type = expense['expense_type']
                description = expense['description']
                amount = expense['amount']
                payment_method = expense['payment_method']
                payment_status = expense['payment_status']
                invoice_number = expense['invoice_number'] or self.generate_invoice_number()
                notes = expense.get('notes', '')
                created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # Check if auxiliary_id is selected
                aux_id = expense.get('auxiliary_id')
                if not aux_id:
                    # Get ledger id for expenses (6261)
                    ledger_data = []
                    connection.contogetrows("SELECT Id FROM Ledger WHERE AccountNumber = ?", ledger_data, ('6261',))
                    if ledger_data:
                        ledger_id = ledger_data[0][0]

                        # Get next subnumber for auxiliary
                        sub_data = []
                        connection.contogetrows("SELECT COUNT(*) FROM Auxiliary WHERE LedgerId = ?", sub_data, (ledger_id,))
                        next_sub = sub_data[0][0] + 1
                        account_number = f"6261.{next_sub:06d}"

                        # Create auxiliary
                        aux_sql = "INSERT INTO Auxiliary (LedgerId, AccountNumber, Name, Status) VALUES (?, ?, ?, 1)"
                        connection.insertingtodatabase(aux_sql, (ledger_id, account_number, invoice_number))

                        # Set aux_id to the code
                        aux_id = '6261'

                # Insert expense with auxiliary_id
                expense_sql = """
                    INSERT INTO expenses (expense_date, expense_type, description, amount, payment_method, payment_status, invoice_number, notes, created_by, created_at, auxiliary_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                expense_values = (
                    expense_date,
                    expense_type,
                    description,
                    amount,
                    payment_method,
                    payment_status,
                    invoice_number,
                    notes,
                    'System',
                    created_at,
                    aux_id
                )
                connection.insertingtodatabase(expense_sql, expense_values)

            ui.notify(f'Expense saved successfully! Invoice: {invoice_number}')

            self.refresh_expenses_table()
            self.expenses_aggrid.classes(remove='dimmed')

        except Exception as e:
            ui.notify(f'Error saving expense: {str(e)}')

    def load_max_expense(self):
        try:
            max_id = self.get_max_expense_id()
            if max_id > 0:
                expense_data = []
                connection.contogetrows(
                    f"SELECT id, expense_date, expense_type, description, amount, payment_method, payment_status, invoice_number, auxiliary_id FROM expenses WHERE id = {max_id}",
                    expense_data
                )

                if expense_data:
                    row_data = {
                        'id': expense_data[0][0],
                        'expense_date': expense_data[0][1],
                        'expense_type': expense_data[0][2],
                        'description': expense_data[0][3],
                        'amount': expense_data[0][4],
                        'payment_method': expense_data[0][5],
                        'payment_status': expense_data[0][6],
                        'invoice_number': expense_data[0][7],
                        'auxiliary_id': expense_data[0][8]
                    }

                    self.rows.clear()
                    self.rows.append({
                        'expense_date': str(row_data['expense_date']),
                        'expense_type': row_data['expense_type'],
                        'description': row_data['description'],
                        'amount': float(row_data['amount']),
                        'payment_method': row_data['payment_method'],
                        'payment_status': row_data['payment_status'],
                        'invoice_number': row_data['invoice_number'],
                        'auxiliary_id': row_data['auxiliary_id']
                    })

                    self.aggrid.options['rowData'] = self.rows
                    self.aggrid.update()

                    self.total_amount = sum(row['amount'] for row in self.rows)
                    self.total_label.text = f"Total: ${self.total_amount:.2f}"

                    ui.notify(f'✅ Automatically loaded expense ID: {max_id} - Invoice: {row_data["invoice_number"]}')
                else:
                    ui.notify('No expenses found in database')
            else:
                ui.notify('No expenses found in database')

        except Exception as e:
            ui.notify(f'Error loading max expense: {str(e)}')

    def populate_expense_types(self):
        try:
            expense_types_data = []
            connection.contogetrows("SELECT id, expense_type_name FROM expense_types", expense_types_data)
            # Create a simple list of option strings for NiceGUI select
            options = [row[1] for row in expense_types_data if row[1]]
            self.type_input.options = options
            self.type_input.update()
        except Exception as e:
            ui.notify(f'Error loading expense types: {str(e)}')

    def populate_auxiliary_options(self):
        try:
            auxiliary_data = []
            connection.contogetrows("SELECT id, auxiliary_id, account_name FROM auxiliary WHERE auxiliary_id LIKE '62%'", auxiliary_data)
            self.label_to_aux_id = {}
            for row in auxiliary_data:
                label = f"{row[1]} - {row[2]}"
                self.label_to_aux_id[label] = row[1]  # auxiliary_id code
            self.auxiliary_select.options = list(self.label_to_aux_id.keys())
            self.auxiliary_select.update()
        except Exception as e:
            ui.notify(f'Error loading auxiliary options: {str(e)}')

    def create_ui(self):
        # Action Bar
        with ui.row().classes('w-full justify-between items-center mb-6 p-4 rounded-2xl bg-white/5 glass border border-white/10'):
            with ui.row().classes('gap-3'):
                ModernButton('New Expense', icon='add', on_click=self.clear_inputs, variant='primary')
                ModernButton('Save All', icon='save', on_click=self.save_expense, variant='success')
                ModernButton('Undo', icon='undo', on_click=self.show_undo_confirmation, variant='secondary')
                ModernButton('Delete', icon='delete', on_click=self.delete_expense, variant='error')
            
            ModernButton('Refresh', icon='refresh', on_click=self.refresh_expenses_table, variant='outline').classes('text-white border-white/20')

        with ui.column().classes('w-full gap-6'):
            # Row 1: History
            with ModernCard(glass=True).classes('w-full p-6'):
                ui.label('Expenses History').classes('text-xl font-black mb-4 text-white')
                
                expenses_columns = [
                    {'headerName': 'ID', 'field': 'id', 'width': 70, 'filter': True},
                    {'headerName': 'Date', 'field': 'expense_date', 'width': 120, 'filter': True},
                    {'headerName': 'Type', 'field': 'expense_type', 'width': 130, 'filter': True},
                    {'headerName': 'Description', 'field': 'description', 'width': 200, 'filter': True},
                    {'headerName': 'Amount', 'field': 'amount', 'width': 100,  'filter': True, 'valueFormatter': "'$' + x.toLocaleString()"},
                    {'headerName': 'Payment', 'field': 'payment_method', 'width': 120, 'filter': True},
                    {'headerName': 'Invoice', 'field': 'invoice_number', 'width': 130, 'filter': True},
                    {'headerName': 'Auxiliary', 'field': 'auxiliary_id', 'width': 130, 'filter': True}
                ]

                self.expenses_aggrid = ui.aggrid({
                    'columnDefs': expenses_columns,
                    'rowData': [],
                    'defaultColDef': MDS.get_ag_grid_default_def(),
                    'rowSelection': 'single',
                }).classes('w-full h-64 ag-theme-quartz-dark mt-2')
                
                async def handle_expenses_aggrid_click():
                    try:
                        selected_row = await self.expenses_aggrid.get_selected_row()
                        if selected_row and isinstance(selected_row, dict) and 'id' in selected_row:
                            expense_id = selected_row['id']
                            self.current_expense_id = expense_id
                            
                            expense_data = []
                            connection.contogetrows(
                                f"SELECT expense_date, expense_type, description, amount, payment_method, payment_status, invoice_number, auxiliary_id FROM expenses WHERE id = {expense_id}",
                                expense_data
                            )

                            if expense_data:
                                self.rows.clear()
                                self.rows.append({
                                    'expense_date': str(expense_data[0][0]),
                                    'expense_type': expense_data[0][1],
                                    'description': expense_data[0][2],
                                    'amount': float(expense_data[0][3]),
                                    'payment_method': expense_data[0][4],
                                    'payment_status': expense_data[0][5],
                                    'invoice_number': expense_data[0][6],
                                    'auxiliary_id': expense_data[0][7]
                                })
                            
                                self.aggrid.options['rowData'] = self.rows
                                self.aggrid.update()
                                
                                self.total_amount = sum(row['amount'] for row in self.rows)
                                self.total_label.set_text(f"${self.total_amount:,.2f}")
                                ui.notify(f'Loaded expense ID: {expense_id}', color='positive')
                    except Exception as ex:
                        ui.notify(f'Error loading expense: {str(ex)}', color='negative')
                
                self.expenses_aggrid.on('cellClicked', handle_expenses_aggrid_click)

            # Row 2: Form and Current Items
            with ui.row().classes('w-full gap-6'):
                # Input Form
                with ModernCard(glass=True).classes('w-1/3 p-6'):
                    ui.label('Add/Edit Expense').classes('text-lg font-black mb-6 text-white')
                    
                    with ui.column().classes('w-full gap-4'):
                        self.auxiliary_select = ModernInput('Auxiliary', icon='account_balance').classes('w-full')
                        # Convert to select
                        self.auxiliary_select = ui.select(options=[], label='Auxiliary').classes('w-full glass-input text-white').props('dark rounded outlined')
                        self.auxiliary_select.on('focus', self.populate_auxiliary_options)

                        self.date_input = ui.input('Date').classes('w-full glass-input text-white').props('dark rounded outlined type=date')
                        self.date_input.value = str(dt.today())

                        self.type_input = ui.select(options=[], label='Expense Type').classes('w-full glass-input text-white').props('dark rounded outlined')
                        
                        self.description_input = ui.input('Description').classes('w-full glass-input text-white').props('dark rounded outlined')
                        
                        self.amount_input = ui.number('Amount', value=0.0, format='%.2f').classes('w-full glass-input text-white').props('dark rounded outlined')

                        with ui.column().classes('w-full gap-2 mt-2'):
                            ui.label('Payment Method').classes('text-xs font-bold text-gray-400 uppercase tracking-wider')
                            self.payment_method = ui.radio(options=['Cash', 'Card', 'Bank Transfer'], value='Cash').props('inline dark')

                        self.invoice_input = ui.input('Invoice # (Optional)').classes('w-full glass-input text-white').props('dark rounded outlined')
                        self.notes_input = ui.textarea('Internal Notes').classes('w-full glass-input text-white').props('dark rounded outlined')
                        
                        ModernButton('Add to List', icon='playlist_add', on_click=self.add_expense, variant='primary').classes('w-full mt-4')

                # Current Items Table
                with ModernCard(glass=True).classes('flex-1 p-6'):
                    with ui.row().classes('w-full justify-between items-center mb-4'):
                        ui.label('Expense Items').classes('text-xl font-black text-white')
                        with ui.column().classes('items-end'):
                            ui.label('Total Amount').classes('text-[10px] font-black uppercase text-purple-400 tracking-wider')
                            self.total_label = ui.label('$0.00').classes('text-3xl font-black text-white').style('font-family: "Outfit", sans-serif;')

                    self.aggrid = ui.aggrid({
                        'columnDefs': self.columns,
                        'rowData': self.rows,
                        'defaultColDef': MDS.get_ag_grid_default_def(),
                        'rowSelection': 'single',
                    }).classes('w-full h-96 ag-theme-quartz-dark')
                    
                    async def handle_aggrid_click():
                        try:
                            selected_row = await self.aggrid.get_selected_row()
                            if selected_row:
                                self.open_edit_dialog(selected_row)
                        except Exception as ex:
                            ui.notify(f'Error: {str(ex)}', color='negative')
                    
                    self.aggrid.on('cellClicked', handle_aggrid_click)

        # Initialize
        ui.timer(0.1, self.refresh_expenses_table, once=True)
        ui.timer(0.2, self.populate_expense_types, once=True)
        ui.timer(0.3, self.load_max_expense, once=True)

    def clear_inputs(self):
        self.rows.clear()
        self.aggrid.options['rowData'] = self.rows
        self.aggrid.update()
        self.total_amount = 0
        self.total_label.set_text("$0.00")
        self.current_expense_id = None
        self.description_input.value = ''
        self.amount_input.value = 0.0
        self.invoice_input.value = ''
        self.notes_input.value = ''
        ui.notify('Ready for new entry', color='info')

@ui.page('/expenses')
def expenses_page_route():
    expenses_page()
