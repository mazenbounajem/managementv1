from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from modern_design_system import ModernDesignSystem as MDS

def ledger_content(standalone=False):
    """Content method for ledger that can be used in tabs"""
    if standalone:
        with ModernPageLayout("Ledger Management", standalone=standalone):
            LedgerUI(standalone=False)
    else:
        LedgerUI(standalone=False)

@ui.page('/ledger')
def ledger_page_route():
    ledger_content(standalone=True)

class LedgerUI:
    def __init__(self, standalone=True):
        self.standalone = standalone
        self.input_refs = {}
        self.initial_values = {}
        self.row_data = []
        self.table = None
        self.search_input = None
        self.create_ui()

    def clear_input_fields(self):
        self.input_refs['account_number'].value = ''
        self.input_refs['sub_number'].value = ''
        self.input_refs['parent_id'].value = None
        self.input_refs['name_en'].value = ''
        self.input_refs['name_fr'].value = ''
        self.input_refs['name_ar'].value = ''
        self.input_refs['status'].value = 1
        self.input_refs['id'].value = ''
        if self.table:
            self.table.classes('dimmed')
        ui.notify('Ready for new ledger entry', color='info')

    def save_ledger(self):
        account_number = self.input_refs['account_number'].value
        sub_number = self.input_refs['sub_number'].value
        parent_id = self.input_refs['parent_id'].value
        name_en = self.input_refs['name_en'].value
        name_fr = self.input_refs['name_fr'].value
        name_ar = self.input_refs['name_ar'].value
        status = self.input_refs['status'].value
        id_value = self.input_refs['id'].value

        if not account_number or not name_en:
            ui.notify('Account Number and English Name are required', color='warning')
            return

        try:
            if id_value:
                sql = "UPDATE Ledger SET AccountNumber=?, SubNumber=?, ParentId=?, Name_en=?, Name_fr=?, Name_ar=?, UpdateDate=GETDATE(), Status=? WHERE Id=?"
                values = (account_number, sub_number, parent_id, name_en, name_fr, name_ar, status, id_value)
            else:
                sql = "INSERT INTO Ledger (AccountNumber, SubNumber, ParentId, Name_en, Name_fr, Name_ar, UpdateDate, Status) VALUES (?, ?, ?, ?, ?, ?, GETDATE(), ?)"
                values = (account_number, sub_number, parent_id, name_en, name_fr, name_ar, status)

            connection.insertingtodatabase(sql, values)
            ui.notify('Ledger saved successfully', color='positive')
            if self.table:
                self.table.classes(remove='dimmed')
            self.refresh_table()
        except Exception as e:
            ui.notify(f'Error saving ledger: {str(e)}', color='negative')

    def undo_changes(self):
        for field in ['account_number', 'sub_number', 'parent_id', 'name_en', 'name_fr', 'name_ar', 'status', 'id']:
            if field in self.initial_values:
                self.input_refs[field].value = self.initial_values[field]
        if self.table:
            self.table.classes(remove='dimmed')
        ui.notify('Changes reverted', color='info')

    def delete_ledger(self):
        id_value = self.input_refs['id'].value
        if not id_value:
            ui.notify('Please select a ledger to delete', color='warning')
            return

        try:
            # Check if ledger is used in any transactions
            data = []
            connection.contogetrows("SELECT COUNT(*) FROM journal_voucher_lines WHERE account=?", data, (self.input_refs['account_number'].value,))
            if data and data[0][0] > 0:
                ui.notify('Cannot delete: Ledger account is in use by journal vouchers', color='warning')
                return
                
            sql = "DELETE FROM Ledger WHERE Id=?"
            connection.deleterow(sql, id_value)
            ui.notify('Ledger deleted successfully', color='positive')
            if self.table:
                self.table.classes(remove='dimmed')
            self.clear_input_fields()
            self.refresh_table()
        except Exception as e:
            ui.notify(f'Error deleting ledger: {str(e)}', color='negative')

    def refresh_table(self):
        try:
            data = []
            connection.contogetrows("SELECT Id, AccountNumber, SubNumber, ParentId, Name_en, Name_fr, Name_ar, UpdateDate, Status FROM Ledger ORDER BY Id DESC", data)

            new_row_data = []
            for row in data:
                new_row_data.append({
                    'Id': row[0],
                    'AccountNumber': row[1],
                    'SubNumber': row[2],
                    'ParentId': row[3],
                    'Name_en': row[4],
                    'Name_fr': row[5],
                    'Name_ar': row[6],
                    'UpdateDate': str(row[7]),
                    'Status': row[8]
                })

            if self.table:
                self.table.options['rowData'] = new_row_data
                self.table.update()
                self.table.classes(remove='dimmed')

            self.row_data = new_row_data
            self.clear_input_fields()
            self.update_parent_options()
        except Exception as e:
            ui.notify(f'Error refreshing data: {str(e)}', color='negative')

    def update_parent_options(self):
        try:
            ledger_data = []
            connection.contogetrows("SELECT Id, Name_en FROM Ledger WHERE Status = 1 ORDER BY Name_en", ledger_data)
            options = {'': 'None (Root Level)'}
            for row in ledger_data:
                if row[0] != int(self.input_refs['id'].value) if self.input_refs['id'].value else True:
                    options[str(row[0])] = f"{row[1]} (ID: {row[0]})"
            self.input_refs['parent_id'].options = options
            self.input_refs['parent_id'].update()
        except Exception as e:
            print(f"Error updating parent options: {e}")

    def create_ui(self):
        # Wrap content in ModernPageLayout only if standalone, otherwise just render the content
        if self.standalone:
            layout_container = ModernPageLayout("Ledger Management", standalone=True)
            layout_container.__enter__()
        
        try:
            # Action Bar
            with ui.row().classes('w-full justify-between items-center mb-6 p-4 rounded-2xl bg-white/5 glass border border-white/10'):
                with ui.row().classes('gap-3'):
                    ModernButton('New Entry', icon='add', on_click=self.clear_input_fields, variant='primary')
                    ModernButton('Save', icon='save', on_click=self.save_ledger, variant='success')
                    ModernButton('Undo', icon='undo', on_click=self.undo_changes, variant='secondary')
                    ModernButton('Delete', icon='delete', on_click=self.delete_ledger, variant='error')
                
                ModernButton('Refresh', icon='refresh', on_click=self.refresh_table, variant='outline').classes('text-white border-white/20')

            with ui.column().classes('w-full gap-6'):
                # Top: List
                with ModernCard(glass=True).classes('w-full p-6'):
                    with ui.row().classes('w-full justify-between items-center mb-4'):
                        ui.label('Ledger Accounts').classes('text-xl font-black text-white')
                        self.search_input = ui.input(placeholder='Search ledger...').classes('w-64 glass-input text-white text-sm').props('dark rounded outlined dense')
                        self.search_input.on('input', lambda e: self.filter_rows(e.value))

                    column_defs = [
                        {'headerName': 'ID', 'field': 'Id', 'width': 80},
                        {'headerName': 'Account #', 'field': 'AccountNumber', 'width': 120},
                        {'headerName': 'Sub #', 'field': 'SubNumber', 'width': 100},
                        {'headerName': 'Name (EN)', 'field': 'Name_en', 'width': 200},
                        {'headerName': 'Status', 'field': 'Status', 'width': 100, 'cellRenderer': 'params => params.value == 1 ? "Active" : "Inactive"'},
                        {'headerName': 'Last Update', 'field': 'UpdateDate', 'width': 180}
                    ]

                    self.table = ui.aggrid({
                        'columnDefs': column_defs,
                        'rowData': [],
                        'defaultColDef': MDS.get_ag_grid_default_def(),
                        'rowSelection': 'single',
                    }).classes('w-full h-80 ag-theme-quartz-dark')
                    
                    async def on_row_click():
                        try:
                            selected_row = await self.table.get_selected_row()
                            if selected_row:
                                self.input_refs['id'].value = str(selected_row['Id'])
                                self.input_refs['account_number'].value = selected_row['AccountNumber']
                                self.input_refs['sub_number'].value = selected_row['SubNumber']
                                self.input_refs['parent_id'].value = str(selected_row['ParentId']) if selected_row['ParentId'] else ''
                                self.input_refs['name_en'].value = selected_row['Name_en']
                                self.input_refs['name_fr'].value = selected_row['Name_fr'] or ''
                                self.input_refs['name_ar'].value = selected_row['Name_ar'] or ''
                                self.input_refs['status'].value = selected_row['Status']
                                
                                self.initial_values = {
                                    'account_number': selected_row['AccountNumber'],
                                    'sub_number': selected_row['SubNumber'],
                                    'parent_id': str(selected_row['ParentId']) if selected_row['ParentId'] else '',
                                    'name_en': selected_row['Name_en'],
                                    'name_fr': selected_row['Name_fr'] or '',
                                    'name_ar': selected_row['Name_ar'] or '',
                                    'status': selected_row['Status'],
                                    'id': str(selected_row['Id'])
                                }
                                self.update_parent_options()
                                ui.notify(f'Selected: {selected_row["Name_en"]}', color='info')
                        except Exception as e:
                            ui.notify(f'Error selecting row: {str(e)}', color='negative')
                    
                    self.table.on('cellClicked', on_row_click)

                # Bottom: Details Form
                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Ledger Details').classes('text-lg font-black mb-6 text-white')
                    with ui.row().classes('w-full gap-6 items-center'):
                        self.input_refs['account_number'] = ui.input('Account Number').classes('w-48 glass-input text-white').props('dark rounded outlined')
                        self.input_refs['sub_number'] = ui.input('Sub Number').classes('w-32 glass-input text-white').props('dark rounded outlined')
                        self.input_refs['parent_id'] = ui.select({}, label='Parent Account').classes('w-64 glass-input text-white').props('dark rounded outlined')
                        self.input_refs['status'] = ui.select({1: 'Active', 0: 'Inactive'}, label='Status').classes('w-32 glass-input text-white').props('dark rounded outlined')
                        self.input_refs['id'] = ui.input('ID (Auto)').classes('w-32 glass-input text-white').props('dark rounded outlined readonly')

                    with ui.row().classes('w-full gap-6 mt-4'):
                        self.input_refs['name_en'] = ui.input('Name (English)').classes('flex-1 glass-input text-white').props('dark rounded outlined')
                        self.input_refs['name_fr'] = ui.input('Name (French)').classes('flex-1 glass-input text-white').props('dark rounded outlined')
                        self.input_refs['name_ar'] = ui.input('Name (Arabic)').classes('flex-1 glass-input text-white').props('dark rounded outlined')

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