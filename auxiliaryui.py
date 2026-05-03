from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from modern_design_system import ModernDesignSystem as MDS
import accounting_helpers

def auxiliary_content(standalone=False):
    """Content method for auxiliary management that can be used in tabs"""
    if standalone:
        with ModernPageLayout("Auxiliary Management"):
            AuxiliaryUI(standalone=False)
    else:
        AuxiliaryUI(standalone=False)

@ui.page('/auxiliary')
def auxiliary_page_route():
    with ModernPageLayout("Auxiliary Management"):
        AuxiliaryUI(standalone=True)

class AuxiliaryUI:
    def __init__(self, standalone=True):
        self.standalone = standalone
        self.input_refs = {}
        self.initial_values = {}
        self.row_data = []
        self.table = None
        self.from_date = None
        self.to_date = None
        self.create_ui()

    def clear_input_fields(self):
        self.input_refs['aux_code'].value = None
        self.input_refs['account_name'].value = ''
        self.input_refs['number'].value = ''
        self.input_refs['status'].value = 1
        self.input_refs['id'].value = ''
        if self.table:
            self.table.classes(add='dimmed')
            self.table.run_method('deselectAll')
        ui.notify('Ready for new entry', color='info')

    def _load_last_row(self):
        """Load first row (last id DESC) into form and undim table"""
        if not self.row_data:
            return
        row = self.row_data[0]
        self.input_refs['id'].value = str(row['id'])
        self.input_refs['aux_code'].value = row['auxiliary_id']
        self.input_refs['account_name'].value = row['account_name'] or ''
        self.input_refs['number'].value = row['number'] or ''
        self.input_refs['status'].value = row['status']
        self.initial_values = {
            'aux_code': row['auxiliary_id'],
            'account_name': row['account_name'] or '',
            'number': row['number'] or '',
            'status': row['status'],
            'id': str(row['id'])
        }
        if self.table:
            self.table.classes(remove='dimmed')

    def save_auxiliary(self):
        aux_code = self.input_refs['aux_code'].value
        account_name = self.input_refs['account_name'].value
        number = self.input_refs['number'].value
        status = self.input_refs['status'].value
        id_value = self.input_refs['id'].value

        if not aux_code or not account_name or not number:
            ui.notify('Code, Name and Number are required', color='warning')
            return

        try:
            if id_value:
                sql = "UPDATE auxiliary SET auxiliary_id=?, account_name=?, number=?, update_date=GETDATE(), status=? WHERE id=?"
                values = (aux_code, account_name, number, status, id_value)
            else:
                sql = "INSERT INTO auxiliary (auxiliary_id, account_name, number, update_date, status) VALUES (?, ?, ?, GETDATE(), ?)"
                values = (aux_code, account_name, number, status)

            connection.insertingtodatabase(sql, values)
            ui.notify('Saved successfully', color='positive')
            if self.table:
                self.table.classes(remove='dimmed')
            self.refresh_table()
        except Exception as e:
            ui.notify(f'Error saving: {str(e)}', color='negative')

    def undo_changes(self):
        fields = ['aux_code', 'account_name', 'number', 'status', 'id']
        for field in fields:
            if field in self.initial_values:
                self.input_refs[field].value = self.initial_values[field]
        if self.table:
            self.table.classes(remove='dimmed')
        ui.notify('Changes reverted', color='info')

    def delete_auxiliary(self):
        id_value = self.input_refs['id'].value
        if not id_value:
            ui.notify('Select a record to delete', color='warning')
            return

        try:
            sql = "DELETE FROM auxiliary WHERE id=?"
            connection.deleterow(sql, id_value)
            ui.notify('Deleted successfully', color='positive')
            if self.table:
                self.table.classes(remove='dimmed')
            self.clear_input_fields()
            self.refresh_table()
        except Exception as e:
            ui.notify(f'Error deleting: {str(e)}', color='negative')

    def refresh_table(self):
        try:
            data = []
            sql = """
                SELECT a.id, a.auxiliary_id, l.Name_en as ledger_name, 
                       a.account_name, a.number, a.update_date, a.status 
                FROM auxiliary a
                LEFT JOIN Ledger l ON a.auxiliary_id = l.AccountNumber
                ORDER BY a.id DESC
            """
            connection.contogetrows(sql, data)

            new_row_data = []
            for row in data:
                # Extract the auxiliary suffix (e.g., '000001' from '4111.000001')
                full_number = str(row[4]) if row[4] else ''
                aux_suffix = full_number.split('.')[-1] if '.' in full_number else full_number

                new_row_data.append({
                    'id': row[0],
                    'auxiliary_id': str(row[1]) if row[1] else '',
                    'ledger_name': str(row[2]) if row[2] else 'Unknown',
                    'account_name': row[3],
                    'number': full_number,
                    'aux_suffix': aux_suffix,
                    'update_date': str(row[5]),
                    'status': row[6]
                })

            if self.table:
                self.table.options['rowData'] = new_row_data
                self.table.update()

            self.row_data = new_row_data
            self.update_code_options()
            # Load last entry into form and undim
            self._load_last_row()
        except Exception as e:
            ui.notify(f'Error refreshing: {str(e)}', color='negative')

    def update_code_options(self):
        try:
            data = []
            connection.contogetrows("SELECT AccountNumber, Name_en FROM Ledger WHERE Status = 1 ORDER BY AccountNumber", data)
            options = {str(row[0]): f"{row[0]} - {row[1]}" for row in data if row[0]}
            self.input_refs['aux_code'].options = options
            self.input_refs['aux_code'].update()
        except Exception as e:
            print(f"Error updating codes from ledger: {e}")

    def get_selected_aux_number(self):
        """Return the auxiliary number (e.g. 4111.000001) of the currently loaded account."""
        number = self.input_refs.get('number', None)
        if number and number.value:
            return number.value
        return None

    def print_statement(self):
        """Open Statement of Account dialog for the selected auxiliary number."""
        from nicegui import ui
        aux_number = self.get_selected_aux_number()
        if not aux_number:
            ui.notify('Select an auxiliary account first', color='warning')
            return
            
        from datetime import date
        today = date.today().strftime('%Y-%m-%d')
        first_of_month = date.today().replace(day=1).strftime('%Y-%m-%d')

        with ui.dialog() as dlg:
            dlg.props('persistent')
            with ModernCard(glass=True).classes('min-w-[400px] p-6'):
                ui.label('Statement of Account').classes('text-xl font-black text-white mb-4')
                
                with ui.column().classes('w-full gap-4'):
                    from_date_input = ui.input('From Date', value=first_of_month).props('type=date dark outlined').classes('w-full text-white')
                    to_date_input = ui.input('To Date', value=today).props('type=date dark outlined').classes('w-full text-white')
                    
                    def _run_report():
                        f = from_date_input.value
                        t = to_date_input.value
                        if not f or not t:
                            ui.notify('Select dates.', color='warning')
                            return
                        if f > t:
                            ui.notify('From date must be before To date.', color='negative')
                            return
                        import auxiliary_reports
                        auxiliary_reports.report_auxiliary_statement(f, t)
                        dlg.close()

                    with ui.row().classes('w-full justify-between mt-4'):
                        ModernButton('Cancel', on_click=dlg.close, variant='danger')
                        ModernButton('View Report', on_click=_run_report, variant='primary').classes('bg-purple-600')
        dlg.open()

    def print_trial_balance(self):
        """Print full Trial Balance PDF."""
        from nicegui import ui
        try:
            from_d = self.from_date.value if self.from_date and self.from_date.value else None
            to_d = self.to_date.value if self.to_date and self.to_date.value else None
            accounting_helpers.print_trial_balance(from_date=from_d, to_date=to_d)
        except Exception as e:
            ui.notify(f'Trial Balance Error: {e}', color='negative')

    def view_transactions(self):
        """Show all accounting transactions for the selected auxiliary number."""
        aux_number = self.get_selected_aux_number()
        if not aux_number:
            from nicegui import ui
            ui.notify('Select an auxiliary account first', color='warning')
            return
        
        from_d = self.from_date.value if self.from_date and self.from_date.value else None
        to_d = self.to_date.value if self.to_date and self.to_date.value else None
        
        accounting_helpers.show_transactions_dialog(account_number=aux_number, from_date=from_d, to_date=to_d)

    def create_ui(self):

        # Wrap content in ModernPageLayout only if standalone, otherwise just render the content
        if self.standalone:
            layout_container = ModernPageLayout("Auxiliary Management", standalone=True)
            layout_container.__enter__()
        
        try:
            with ui.row().classes('w-full gap-6 items-start p-4 animate-fade-in'):
                # Left Column: Form
                with ui.column().classes('w-1/3 gap-6'):
                    with ModernCard(glass=True).classes('w-full p-6'):
                        ui.label('Record Details').classes('text-lg font-black mb-6 text-white')
                        with ui.column().classes('w-full gap-4'):
                            self.input_refs['aux_code'] = ui.select([None], label='Account (Code - Name)').classes('w-full glass-input text-white').props('dark rounded outlined')
                            self.input_refs['number'] = ui.input('Auxiliary Number').classes('w-full glass-input text-white').props('dark rounded outlined')
                            self.input_refs['status'] = ui.select({1: 'Active', 0: 'Inactive'}, label='Status').classes('w-full glass-input text-white').props('dark rounded outlined')
                            self.input_refs['id'] = ui.input('ID (Internal)').classes('w-full glass-input text-white').props('dark rounded outlined readonly')

                    with ModernCard(glass=True).classes('w-full p-6'):
                        ui.label('Name & Identity').classes('text-lg font-black mb-6 text-white')
                        with ui.column().classes('w-full gap-4'):
                            self.input_refs['account_name'] = ui.input('Account Name').classes('w-full glass-input text-white').props('dark rounded outlined')

                    # Removed 'Report Filters' and 'Actions' cards as they are now handled by ModernActionBar and Report Center
                # Middle Column: List
                with ui.column().classes('flex-1 gap-6'):
                    with ModernCard(glass=True).classes('w-full p-6'):
                        with ui.row().classes('w-full justify-between items-center mb-4'):
                            ui.label('Auxiliary List').classes('text-xl font-black text-white ml-2')
                            self.search_input = ui.input(placeholder='Search...').classes('w-64 glass-input text-white text-sm').props('dark rounded outlined dense')
                            self.search_input.on('input', lambda e: self.filter_rows(e.value))

                        column_defs = [
                            {'headerName': 'Ledger Name', 'field': 'ledger_name', 'width': 130},
                            {'headerName': 'Account (Aux Code)', 'field': 'auxiliary_id', 'width': 140},
                            {'headerName': 'Name', 'field': 'account_name', 'width': 220, 'flex': 1},
                            {'headerName': 'Auxiliary', 'field': 'aux_suffix', 'width': 100},
                            {'headerName': 'Full Number', 'field': 'number', 'width': 130},
                            {'headerName': 'Status', 'field': 'status', 'width': 100, 'cellRenderer': 'params => params.value == 1 ? "Active" : "Inactive"'}
                        ]

                        self.table = ui.aggrid({
                            'columnDefs': column_defs,
                            'rowData': [],
                            'defaultColDef': MDS.get_ag_grid_default_def(),
                            'rowSelection': 'single',
                        }).classes('w-full h-[600px] ag-theme-quartz-dark')
                        
                        def on_row_click(e):
                            try:
                                selected_row = e.args.get('data', {})
                                if selected_row:
                                    self.input_refs['id'].value = str(selected_row['id'])
                                    self.input_refs['aux_code'].value = selected_row['auxiliary_id']
                                    self.input_refs['account_name'].value = selected_row['account_name'] or ''
                                    self.input_refs['number'].value = selected_row['number'] or ''
                                    self.input_refs['status'].value = selected_row['status']
                                    self.initial_values = {
                                        'aux_code': selected_row['auxiliary_id'],
                                        'account_name': selected_row['account_name'] or '',
                                        'number': selected_row['number'] or '',
                                        'status': selected_row['status'],
                                        'id': str(selected_row['id'])
                                    }
                                    if self.table:
                                        self.table.classes(remove='dimmed')
                            except Exception as e:
                                ui.notify(f'Error selecting: {str(e)}', color='negative')

                        self.table.on('cellClicked', on_row_click)

                # Right Column: Action Bar
                with ui.column().classes('w-80px items-center'):
                    from modern_ui_components import ModernActionBar
                    ModernActionBar(
                        on_new=self.clear_input_fields,
                        on_save=self.save_auxiliary,
                        on_undo=self.undo_changes,
                        on_delete=self.delete_auxiliary,
                        on_refresh=self.refresh_table,
                        on_chatgpt=lambda: ui.run_javascript('window.open("https://chatgpt.com", "_blank");'),
                        on_print=self.print_statement,
                        on_print_special=lambda: __import__('auxiliary_reports').open_print_special_dialog(),
                        on_view_transaction=self.view_transactions,
                        target_table=self.table,
                        button_class='h-16',
                        classes=' '
                    ).style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

            ui.timer(0.1, self.refresh_table, once=True)
        finally:
            if self.standalone:
                layout_container.__exit__(None, None, None)

    def filter_rows(self, search_text):
        if not search_text:
            self.table.options['rowData'] = self.row_data
        else:
            search_text = search_text.lower()
            filtered = [row for row in self.row_data if any(search_text in str(v).lower() for v in row.values())]
            self.table.options['rowData'] = filtered
        self.table.update()