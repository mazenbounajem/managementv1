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
        self.auxiliary_input = None
        self.selected_auxiliary_id = None
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

            if not self.selected_auxiliary_id:
                ui.notify('Please select an Auxiliary Account.', color='warning')
                return

            if not self.type_input.value:
                ui.notify('Please select an Expense Type.', color='warning')
                return

            expense_data = {
                'expense_date': self.date_input.value,
                'expense_type': self.type_input.value,
                'description': self.description_input.value,
                'amount': amount,
                'payment_method': self.payment_method.value,
                'payment_status': 'Pending',
                'invoice_number': self.invoice_input.value or self.generate_invoice_number(),
                'auxiliary_id': self.selected_auxiliary_id
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
        if self.expenses_aggrid:
            self.expenses_aggrid.classes(add='dimmed')
        if hasattr(self, 'action_bar'):
            self.action_bar.enter_new_mode()
        ui.notify('New expense entry ready', color='info')

    def save_expense(self):
        if not self.rows:
            ui.notify('No expense items to save', color='warning')
            return

        try:
            for row in self.rows:
                # Insert each item into the expenses table directly
                sql = """
                INSERT INTO expenses (expense_date, expense_type, description, amount, payment_method, payment_status, invoice_number, notes, auxiliary_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
                """
                notes = self.notes_input.value if self.notes_input else ''
                connection.insertingtodatabase(sql, (
                    row['expense_date'],
                    row['expense_type'],
                    row['description'],
                    row['amount'],
                    row['payment_method'],
                    row['payment_status'], # Use status from grid
                    row['invoice_number'],
                    notes,
                    row['auxiliary_id']
                ))

            ui.notify('All expenses saved successfully!', color='positive')
            self.clear_inputs()
            self.refresh_expenses_table() # Refresh the history table at the top
        except Exception as ex:
            ui.notify(f'Error saving expense: {str(ex)}', color='negative')



    def populate_expense_types(self):
        try:
            data = []
            connection.contogetrows("SELECT expense_type_name FROM expense_types ORDER BY expense_type_name", data)
            options = [row[0] for row in data if row[0]]
            if self.type_input:
                self.type_input.options = options
                if not self.type_input.value and options:
                    self.type_input.value = options[0]
                self.type_input.update()
        except Exception as e:
            print(f"Error populating expense types: {e}")

    def open_auxiliary_dialog(self):
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-4xl glass p-8 border border-white/10').style('background: rgba(15, 15, 25, 0.9); backdrop-filter: blur(20px); border-radius: 2rem;'):
            ui.label('Select Auxiliary Account').classes('text-2xl font-black mb-6 text-white').style('font-family: "Outfit", sans-serif;')
            
            with ui.row().classes('w-full items-center gap-3 bg-white/5 px-4 py-2 rounded-xl border border-white/10 mb-6 shadow-inner'):
                ui.icon('search', size='1.25rem').classes('text-[#08CB00]')
                search_input = ui.input(placeholder='Search by account name or number...').props('borderless dense').classes('flex-1 text-white font-bold text-sm').on('input', lambda e: self.filter_auxiliary_rows(e.value))
            
            data = []
            connection.contogetrows(
                "SELECT id, auxiliary_id, account_name, number FROM auxiliary WHERE auxiliary_id LIKE '62%' ORDER BY account_name",
                data
            )
            
            self.auxiliary_rows = []
            for row in data:
                self.auxiliary_rows.append({
                    'id': row[0],
                    'auxiliary_id': str(row[1]) if row[1] else '',
                    'account_name': row[2],
                    'number': row[3]
                })
            
            columns = [
                {'headerName': 'ID', 'field': 'id', 'width': 70},
                {'headerName': 'Aux Code', 'field': 'auxiliary_id', 'width': 100},
                {'headerName': 'Account Number', 'field': 'number', 'width': 150},
                {'headerName': 'Account Name', 'field': 'account_name', 'flex': 1}
            ]
            
            self.auxiliary_grid = ui.aggrid({
                'columnDefs': columns,
                'rowData': self.auxiliary_rows,
                'rowSelection': 'single',
                'domLayout': 'normal',
                'defaultColDef': MDS.get_ag_grid_default_def()
            }).classes('w-full h-80 ag-theme-quartz-dark shadow-inner').style('background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px;')
            
            def handle_click(e):
                try:
                    row = e.args['data']
                    self.selected_auxiliary_id = row['id']
                    self.auxiliary_input.value = f"{row['number']} - {row['account_name']}"
                    dialog.close()
                    ui.notify(f"Auxiliary Account Selected: {row['account_name']}", color='info')
                except Exception as ex:
                    ui.notify(f"Selection error: {ex}", color='negative')
            
            self.auxiliary_grid.on('cellClicked', handle_click)
            
            with ui.row().classes('w-full justify-end mt-6'):
                ui.button('Dismiss', on_click=dialog.close).props('flat text-color=white').classes('px-6 rounded-xl hover:bg-white/5 font-black text-xs uppercase tracking-widest')
        dialog.open()

    def filter_auxiliary_rows(self, search_text):
        if not hasattr(self, 'auxiliary_rows'):
            return
        if not search_text:
            filtered_rows = self.auxiliary_rows
        else:
            search_text = search_text.lower()
            filtered_rows = [row for row in self.auxiliary_rows if any(search_text in str(value).lower() for value in row.values())]
        if hasattr(self, 'auxiliary_grid'):
            self.auxiliary_grid.options['rowData'] = filtered_rows
            self.auxiliary_grid.update()

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
            # Query the actual expenses table (individual entries)
            sql = "SELECT id, expense_date, expense_type, amount, payment_status, invoice_number, auxiliary_id FROM expenses ORDER BY id DESC"
            connection.contogetrows(sql, data)
            
            rows = []
            for row in data:
                rows.append({
                    'id': row[0],
                    'expense_date': str(row[1]) if row[1] else '',
                    'expense_type': row[2],
                    'amount': float(row[3]) if row[3] else 0,
                    'payment_status': row[4],
                    'invoice_number': row[5],
                    'auxiliary_id': row[6]
                })
            
            if hasattr(self, 'history_aggrid') and self.history_aggrid:
                self.history_aggrid.options['rowData'] = rows
                self.history_aggrid.update()
        except Exception as e:
            print(f"Error refreshing history: {e}")

    def load_history_entry(self, e):
        """Loads a record from history into the entry form for review or re-editing"""
        try:
            row = e.args.get('data', {})
            if not row:
                return
            
            expense_id = row['id']
            # Fetch the full record to be sure we have everything
            data = []
            sql = "SELECT expense_date, expense_type, description, amount, payment_method, payment_status, invoice_number, notes, auxiliary_id FROM expenses WHERE id = ?"
            connection.contogetrows(sql, data, (expense_id,))
            
            if data:
                res = data[0]
                self.date_input.value = str(res[0]) if res[0] else str(dt.today())
                self.type_input.value = res[1] or ''
                self.description_input.value = res[2] or ''
                self.amount_input.value = float(res[3]) if res[3] else 0.0
                self.payment_method.value = res[4] or 'Cash'
                self.invoice_input.value = res[6] or ''
                self.notes_input.value = res[7] or ''
                self.selected_auxiliary_id = res[8]
                
                # Fetch auxiliary name/number for display
                if self.selected_auxiliary_id:
                    aux_data = []
                    connection.contogetrows("SELECT number, account_name FROM auxiliary WHERE id = ?", aux_data, (self.selected_auxiliary_id,))
                    if aux_data:
                        self.auxiliary_input.value = f"{aux_data[0][0]} - {aux_data[0][1]}"
                    else:
                        self.auxiliary_input.value = "Click to Select"
                else:
                    self.auxiliary_input.value = "Click to Select"
                    
                ui.notify(f"Loaded entry ID: {expense_id}", color='info')
        except Exception as ex:
            ui.notify(f"Error loading history: {ex}", color='negative')

    def create_ui(self):
        # Wrap content in ModernPageLayout only if standalone, otherwise just render the content
        if self.standalone:
            layout_container = ModernPageLayout("Expense Management", standalone=True)
            layout_container.__enter__()
        
        try:
            with ui.row().classes('w-full gap-6 items-start p-4'):
                # Center Column: History (Top) and Entry (Bottom)
                with ui.column().classes('flex-1 gap-4'):
                    with ui.splitter(horizontal=True, value=30).classes('w-full h-[700px]') as splitter:
                        with splitter.before:
                            with ModernCard(glass=True).classes('w-full h-full p-6'):
                                with ui.row().classes('w-full justify-between items-center mb-4'):
                                    with ui.row().classes('items-center'):
                                        ui.label('Expenses History').classes('text-lg font-black text-white')
                                        with ui.row().classes('items-center bg-white/10 rounded-full px-3 py-1 shadow-sm border border-gray-300 dark:border-gray-600 ml-4'):
                                            ui.icon('search', color='gray').classes('text-lg')
                                            self.search_input = ui.input(placeholder='Search expenses...').props('borderless dense').classes('ml-2 w-64 text-sm outline-none text-white')
                                    ui.button(icon='refresh', on_click=self.refresh_expenses_table).props('flat round text-color=white')
                                
                                history_columns = [
                                    {'headerName': 'ID', 'field': 'id', 'width': 60},
                                    {'headerName': 'Date', 'field': 'expense_date', 'width': 100},
                                    {'headerName': 'Type', 'field': 'expense_type', 'width': 120},
                                    {'headerName': 'Amount', 'field': 'amount', 'width': 100, 'valueFormatter': "'$' + x.toLocaleString()"},
                                    {'headerName': 'Auxiliary', 'field': 'auxiliary_id', 'width': 100},
                                    {'headerName': 'Invoice #', 'field': 'invoice_number', 'width': 120},
                                ]

                                self.history_aggrid = ui.aggrid({
                                    'columnDefs': history_columns,
                                    'rowData': [],
                                    'defaultColDef': MDS.get_ag_grid_default_def(),
                                    'rowSelection': 'single',
                                }).classes('w-full h-48 ag-theme-quartz-dark')
                                
                                self.search_input.on('update:model-value', lambda e: (
                                    self.history_aggrid.options.update({'quickFilterText': e.sender.value}),
                                    self.history_aggrid.update()
                                ))
                                
                                self.history_aggrid.on('cellClicked', self.load_history_entry)

                        with splitter.after:
                            with ui.column().classes('w-full gap-4 pt-4'):
                                with ui.row().classes('w-full gap-4'):
                                    # Input Form
                                    with ModernCard(glass=True).classes('w-[360px] p-6'):
                                        ui.label('Category & Detail').classes('text-[10px] font-black uppercase text-green-400 tracking-wider mb-2')
                                        
                                        with ui.column().classes('w-full gap-3'):
                                            self.auxiliary_input = ui.input('Auxiliary Account (Click to Select)').classes('w-full glass-input text-white cursor-pointer').props('dark rounded outlined dense readonly').on('click', self.open_auxiliary_dialog)

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
                                                ui.label('Total').classes('text-[10px] font-black uppercase text-green-400 tracking-wider')
                                                self.total_label = ui.label('$0.00').classes('text-2xl font-black text-white')

                                        self.aggrid = ui.aggrid({
                                            'columnDefs': self.columns,
                                            'rowData': self.rows,
                                            'defaultColDef': MDS.get_ag_grid_default_def(),
                                            'rowSelection': 'single',
                                        }).classes('w-full h-64 ag-theme-quartz-dark shadow-inner')
                                        
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
                    self.action_bar = ModernActionBar(
                        on_new=self.clear_inputs,
                        on_save=self.save_expense,
                        on_undo=lambda: self.action_bar.reset_state(),
                        on_refresh=self.refresh_expenses_table,
                        on_chatgpt=lambda: ui.open('https://chatgpt.com', new_tab=True),
                        target_table=self.history_aggrid,
                        button_class='h-16',
                        classes=' '
                    )
                    self.action_bar.style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

            ui.timer(0.1, self.refresh_expenses_table, once=True)
            ui.timer(0.2, self.populate_expense_types, once=True)
            
        finally:
            if self.standalone:
                layout_container.__exit__(None, None, None)