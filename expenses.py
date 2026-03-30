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

def expenses_content(standalone=False):
    """Content method for expenses that can be used in tabs"""
    if standalone:
        with ModernPageLayout("Expense Management", standalone=standalone):
            ExpensesUI(standalone=False)
    else:
        ExpensesUI(standalone=False)

@ui.page('/expenses')
def expenses_page_route():
    with ModernPageLayout("Expense Management", standalone=True):
        ExpensesUI(standalone=True)

class ExpensesUI:
    def __init__(self, standalone=True):
        self.standalone = standalone
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
        self.aggrid = None
        self.expenses_aggrid = None
        self.total_label = None
        self.auxiliary_select = None
        self.date_input = None
        self.type_input = None
        self.amount_input = None
        self.description_input = None
        self.payment_method = None
        self.invoice_input = None
        self.notes_input = None

        # Initialize UI
        self.create_ui()

    def generate_invoice_number(self):
        """Generate a unique invoice number"""
        try:
            data = []
            connection.contogetrows("SELECT MAX(CAST(SUBSTRING(invoice_number, 4, LEN(invoice_number)-3) AS INT)) FROM expenses WHERE invoice_number LIKE 'EXP-%'", data)
            last_number = data[0][0] if data and data[0][0] else 0
            new_number = last_number + 1
            return f"EXP-{new_number:06d}"
        except Exception as e:
            return f"EXP-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def add_expense(self):
        try:
            amount = float(self.amount_input.value or 0)
            if amount <= 0:
                ui.notify('Please enter a valid amount', color='warning')
                return

            expense_data = {
                'expense_date': self.date_input.value,
                'expense_type': self.type_input.value,
                'description': self.description_input.value,
                'amount': amount,
                'payment_method': self.payment_method.value,
                'payment_status': 'Pending',
                'invoice_number': self.invoice_input.value or self.generate_invoice_number(),
                'auxiliary_id': self.auxiliary_select.value
            }

            self.rows.append(expense_data)
            self.total_amount = sum(row['amount'] for row in self.rows)
            self.total_label.set_text(f"${self.total_amount:,.2f}")

            self.aggrid.options['rowData'] = self.rows
            self.aggrid.update()

            # Clear input fields
            self.amount_input.value = 0.0
            self.description_input.value = ''
            self.invoice_input.value = ''
            self.payment_method.value = 'Cash'

            ui.notify('Expense added to current entry', color='positive')
        except Exception as ex:
            ui.notify(f'Error adding expense: {str(ex)}', color='negative')

    def clear_inputs(self):
        self.rows.clear()
        self.total_amount = 0
        self.total_label.set_text("$0.00")
        self.aggrid.options['rowData'] = self.rows
        self.aggrid.update()
        self.amount_input.value = 0.0
        self.description_input.value = ''
        self.invoice_input.value = ''
        self.payment_method.value = 'Cash'
        self.current_expense_id = None
        self.new_mode = True
        ui.notify('New expense entry ready', color='info')

    def save_expense(self):
        if not self.rows:
            ui.notify('No expense items to save', color='warning')
            return

        try:
            if self.current_expense_id and not self.new_mode:
                # Delete existing expense items
                connection.insertingtodatabase("DELETE FROM expense_items WHERE expense_id = ?", (self.current_expense_id,))
                # Update expense header
                connection.insertingtodatabase("UPDATE expenses SET updated_at = GETDATE() WHERE id = ?", (self.current_expense_id,))
                expense_id = self.current_expense_id
            else:
                # Create new expense header
                expense_id = self.insert_expense_header()

            # Save all expense items
            for row in self.rows:
                self.insert_expense_item(expense_id, row)

            connection.connection.commit()
            ui.notify(f'Expense {"updated" if not self.new_mode else "saved"} successfully!', color='positive')
            self.clear_inputs()
            self.refresh_expenses_table()
        except Exception as ex:
            ui.notify(f'Error saving expense: {str(ex)}', color='negative')
            connection.connection.rollback()

    def insert_expense_header(self):
        sql = """
        INSERT INTO expenses (expense_date, total_amount, status, notes, created_at)
        VALUES (?, ?, 'Draft', ?, GETDATE())
        SELECT SCOPE_IDENTITY() as id
        """
        total = sum(row['amount'] for row in self.rows)
        notes = self.notes_input.value if self.notes_input else ''
        data = []
        connection.contogetrows(sql, data, (self.date_input.value, total, notes))
        return data[0][0] if data else None

    def insert_expense_item(self, expense_id, row):
        sql = """
        INSERT INTO expense_items (expense_id, expense_type, description, amount, payment_method, payment_status, invoice_number, auxiliary_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        connection.insertingtodatabase(sql, (
            expense_id,
            row['expense_type'],
            row['description'],
            row['amount'],
            row['payment_method'],
            row['payment_status'],
            row['invoice_number'],
            row['auxiliary_id']
        ))

    def populate_expense_types(self):
        try:
            data = []
            connection.contogetrows("SELECT expense_type_name FROM expense_types ORDER BY expense_type_name", data)
            options = [row[0] for row in data if row[0]]
            if options and self.type_input:
                self.type_input.options = options
                if not self.type_input.value:
                    self.type_input.value = options[0] if options else ''
                self.type_input.update()
        except Exception as e:
            print(f"Error populating expense types: {e}")

    def populate_auxiliary_options(self):
        try:
            data = []
            connection.contogetrows("SELECT id, account_name FROM auxiliary_accounts ORDER BY account_name", data)
            options = {str(row[0]): row[1] for row in data}
            if options and self.auxiliary_select:
                self.auxiliary_select.options = options
                self.auxiliary_select.update()
        except Exception as e:
            print(f"Error populating auxiliary accounts: {e}")

    def open_edit_dialog(self, row):
        with ui.dialog() as dialog, ModernCard().classes('w-96 p-6'):
            ui.label('Edit Expense Item').classes('text-xl font-bold mb-4')
            
            amount_input = ui.number('Amount', value=row['amount'], format='%.2f').classes('w-full mt-2')
            desc_input = ui.input('Description', value=row['description']).classes('w-full mt-2')
            
            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('Cancel', on_click=dialog.close).props('outline')
                ui.button('Save', on_click=lambda: self.update_expense_item(row, amount_input.value, desc_input.value, dialog)).props('color=primary')
        
        dialog.open()

    def update_expense_item(self, row, new_amount, new_description, dialog):
        row['amount'] = new_amount
        row['description'] = new_description
        
        # Update totals
        self.total_amount = sum(r['amount'] for r in self.rows)
        self.total_label.set_text(f"${self.total_amount:,.2f}")
        
        # Refresh table
        self.aggrid.options['rowData'] = self.rows
        self.aggrid.update()
        
        dialog.close()
        ui.notify('Expense item updated', color='positive')

    def refresh_expenses_table(self):
        try:
            data = []
            sql = "SELECT id, expense_date, total_amount, status FROM expenses ORDER BY id DESC"
            connection.contogetrows(sql, data)
            
            rows = []
            for row in data:
                rows.append({
                    'id': row[0],
                    'expense_date': str(row[1]) if row[1] else '',
                    'total_amount': float(row[2]) if row[2] else 0,
                    'status': row[3]
                })
            
            if self.expenses_aggrid:
                self.expenses_aggrid.options['rowData'] = rows
                self.expenses_aggrid.update()
        except Exception as e:
            print(f"Error refreshing expenses table: {e}")

    def create_ui(self):
        # Wrap content in ModernPageLayout only if standalone, otherwise just render the content
        if self.standalone:
            layout_container = ModernPageLayout("Expense Management", standalone=True)
            layout_container.__enter__()
        
        try:
            with ui.row().classes('w-full gap-6 items-start p-4'):
                # Left Column: Expenses History
                with ui.column().classes('w-[380px] gap-4'):
                    with ModernCard(glass=True).classes('w-full p-6'):
                        ui.label('Expenses History').classes('text-lg font-black mb-4 text-white')
                        
                        expenses_columns = [
                            {'headerName': 'ID', 'field': 'id', 'width': 60},
                            {'headerName': 'Date', 'field': 'expense_date', 'width': 100},
                            {'headerName': 'Total', 'field': 'total_amount', 'width': 100, 'valueFormatter': "'$' + x.toLocaleString()"},
                            {'headerName': 'Status', 'field': 'status', 'width': 80},
                        ]

                        self.expenses_aggrid = ui.aggrid({
                            'columnDefs': expenses_columns,
                            'rowData': [],
                            'defaultColDef': MDS.get_ag_grid_default_def(),
                            'rowSelection': 'single',
                        }).classes('w-full h-[600px] ag-theme-quartz-dark')
                        
                        async def handle_expenses_aggrid_click():
                            try:
                                selected_row = await self.expenses_aggrid.get_selected_row()
                                if selected_row and isinstance(selected_row, dict) and 'id' in selected_row:
                                    expense_id = selected_row['id']
                                    self.current_expense_id = expense_id
                                    
                                    # Load expense items
                                    expense_items = []
                                    sql = """
                                    SELECT expense_date, expense_type, description, amount, payment_method, 
                                           payment_status, invoice_number, auxiliary_id 
                                    FROM expense_items 
                                    WHERE expense_id = ?
                                    """
                                    connection.contogetrows(sql, expense_items, (expense_id,))

                                    if expense_items:
                                        self.rows.clear()
                                        for item in expense_items:
                                            self.rows.append({
                                                'expense_date': str(item[0]) if item[0] else '',
                                                'expense_type': item[1],
                                                'description': item[2],
                                                'amount': float(item[3]),
                                                'payment_method': item[4],
                                                'payment_status': item[5],
                                                'invoice_number': item[6],
                                                'auxiliary_id': item[7]
                                            })
                                        
                                        self.aggrid.options['rowData'] = self.rows
                                        self.aggrid.update()
                                        
                                        self.total_amount = sum(row['amount'] for row in self.rows)
                                        self.total_label.set_text(f"${self.total_amount:,.2f}")
                                        self.new_mode = False
                                        ui.notify(f'Loaded expense ID: {expense_id}', color='positive')
                            except Exception as ex:
                                ui.notify(f'Error loading expense: {str(ex)}', color='negative')
                        
                        self.expenses_aggrid.on('cellClicked', handle_expenses_aggrid_click)

                # Center Column: Form & Current Items
                with ui.column().classes('flex-1 gap-4'):
                    with ui.row().classes('w-full gap-4'):
                        # Input Form
                        with ModernCard(glass=True).classes('w-[360px] p-6'):
                            ui.label('Category & Detail').classes('text-[10px] font-black uppercase text-purple-400 tracking-wider mb-2')
                            
                            with ui.column().classes('w-full gap-3'):
                                self.auxiliary_select = ui.select(options=[], label='Auxiliary Account').classes('w-full glass-input text-white').props('dark rounded outlined dense')
                                self.auxiliary_select.on('focus', self.populate_auxiliary_options)

                                self.date_input = ui.input('Date').classes('w-full glass-input text-white').props('dark rounded outlined dense type=date')
                                self.date_input.value = str(dt.today())

                                self.type_input = ui.select(options=[], label='Expense Type').classes('w-full glass-input text-white').props('dark rounded outlined dense').on('focus', self.populate_expense_types)
                                
                                self.amount_input = ui.number('Amount', value=0.0, format='%.2f').classes('w-full glass-input text-white').props('dark rounded outlined dense')
                                
                                self.description_input = ui.input('Description').classes('w-full glass-input text-white').props('dark rounded outlined dense')
                                
                                with ui.column().classes('w-full gap-0 mt-1'):
                                    ui.label('Payment Method').classes('text-[9px] font-bold text-gray-500 uppercase tracking-widest ml-1')
                                    self.payment_method = ui.radio(options=['Cash', 'Card', 'Bank'], value='Cash').props('inline dark dense').classes('scale-90 origin-left')

                                self.invoice_input = ui.input('Invoice #').classes('w-full glass-input text-white').props('dark rounded outlined dense')
                                
                                ModernButton('Add to Entry', icon='add', on_click=self.add_expense, variant='primary').classes('w-full h-10 mt-2')

                        # Current Entry Table
                        with ModernCard(glass=True).classes('flex-1 p-6'):
                            with ui.row().classes('w-full justify-between items-center mb-4'):
                                ui.label('Current Entry Items').classes('text-lg font-black text-white')
                                with ui.column().classes('items-end'):
                                    ui.label('Total').classes('text-[10px] font-black uppercase text-purple-400 tracking-wider')
                                    self.total_label = ui.label('$0.00').classes('text-2xl font-black text-white')

                            self.aggrid = ui.aggrid({
                                'columnDefs': self.columns,
                                'rowData': self.rows,
                                'defaultColDef': MDS.get_ag_grid_default_def(),
                                'rowSelection': 'single',
                            }).classes('w-full h-96 ag-theme-quartz-dark shadow-inner')
                            
                            async def handle_aggrid_click():
                                try:
                                    selected_row = await self.aggrid.get_selected_row()
                                    if selected_row:
                                        self.open_edit_dialog(selected_row)
                                except Exception as ex:
                                    ui.notify(f'Error: {str(ex)}', color='negative')
                            self.aggrid.on('cellClicked', handle_aggrid_click)

                    # Internal Notes
                    with ModernCard(glass=True).classes('w-full p-4'):
                        self.notes_input = ui.textarea('Internal Notes / Documentation').classes('w-full glass-input text-white').props('dark rounded outlined dense')

                # Right Column: Action Bar
                with ui.column().classes('w-80px items-center'):
                    from modern_ui_components import ModernActionBar
                    ModernActionBar(
                        on_new=self.clear_inputs,
                        on_save=self.save_expense,
                        on_undo=lambda: ui.notify('Undo not implemented for expenses', color='warning'),
                        on_refresh=self.refresh_expenses_table,
                        on_chatgpt=lambda: ui.open('https://chatgpt.com', new_tab=True),
                        button_class='h-16',
                        classes=' '
                    ).style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

            ui.timer(0.1, self.refresh_expenses_table, once=True)
            ui.timer(0.2, self.populate_expense_types, once=True)
            ui.timer(0.2, self.populate_auxiliary_options, once=True)
            
        finally:
            if self.standalone:
                layout_container.__exit__(None, None, None)