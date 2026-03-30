from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from modern_design_system import ModernDesignSystem as MDS

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
        self.create_ui()

    def clear_input_fields(self):
        self.input_refs['aux_code'].value = None
        self.input_refs['account_name'].value = ''
        self.input_refs['number'].value = ''
        self.input_refs['status'].value = 1
        self.input_refs['id'].value = ''
        if self.table:
            self.table.classes('dimmed')
        ui.notify('Ready for new entry', color='info')

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
            connection.contogetrows("SELECT id, auxiliary_id, account_name, number, update_date, status FROM auxiliary WHERE auxiliary_id LIKE '62%' ORDER BY id DESC", data)

            new_row_data = []
            for row in data:
                new_row_data.append({
                    'id': row[0],
                    'auxiliary_id': row[1],
                    'account_name': row[2],
                    'number': row[3],
                    'update_date': str(row[4]),
                    'status': row[5]
                })

            if self.table:
                self.table.options['rowData'] = new_row_data
                self.table.update()
                self.table.classes(remove='dimmed')

            self.row_data = new_row_data
            self.clear_input_fields()
            self.update_code_options()
        except Exception as e:
            ui.notify(f'Error refreshing: {str(e)}', color='negative')

    def update_code_options(self):
        try:
            codes = sorted(list(set(row['auxiliary_id'] for row in self.row_data if row['auxiliary_id'])))
            self.input_refs['aux_code'].options = [None] + codes
            self.input_refs['aux_code'].update()
        except Exception as e:
            print(f"Error updating codes: {e}")

    def create_ui(self):
        # Action Bar
        with ui.row().classes('w-full justify-between items-center mb-6 p-4 rounded-2xl bg-white/5 glass border border-white/10'):
            with ui.row().classes('gap-3'):
                ModernButton('New Entry', icon='add', on_click=self.clear_input_fields, variant='primary')
                ModernButton('Save', icon='save', on_click=self.save_auxiliary, variant='success')
                ModernButton('Undo', icon='undo', on_click=self.undo_changes, variant='secondary')
                ModernButton('Delete', icon='delete', on_click=self.delete_auxiliary, variant='error')
            
            ModernButton('Refresh', icon='refresh', on_click=self.refresh_table, variant='outline').classes('text-white border-white/20')

        with ui.column().classes('w-full gap-6 p-4'):
            # Top: List
            with ModernCard(glass=True).classes('w-full p-6'):
                with ui.row().classes('w-full justify-between items-center mb-4'):
                    ui.label('Auxiliary List').classes('text-xl font-black text-white')
                    self.search_input = ui.input(placeholder='Search...').classes('w-64 glass-input text-white text-sm').props('dark rounded outlined dense')
                    self.search_input.on('input', lambda e: self.filter_rows(e.value))

                column_defs = [
                    {'headerName': 'Aux Code', 'field': 'auxiliary_id', 'width': 120},
                    {'headerName': 'Name', 'field': 'account_name', 'width': 220},
                    {'headerName': 'Number', 'field': 'number', 'width': 120},
                    {'headerName': 'Status', 'field': 'status', 'width': 100, 'cellRenderer': 'params => params.value == 1 ? "Active" : "Inactive"'},
                    {'headerName': 'Last Update', 'field': 'update_date', 'width': 180}
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
                            self.input_refs['id'].value = str(selected_row['id'])
                            self.input_refs['aux_code'].value = selected_row['auxiliary_id']
                            self.input_refs['account_name'].value = selected_row['account_name']
                            self.input_refs['number'].value = selected_row['number']
                            self.input_refs['status'].value = selected_row['status']
                            
                            self.initial_values = {
                                'aux_code': selected_row['auxiliary_id'],
                                'account_name': selected_row['account_name'],
                                'number': selected_row['number'],
                                'status': selected_row['status'],
                                'id': str(selected_row['id'])
                            }
                            ui.notify(f'Selected: {selected_row["account_name"]}', color='info')
                    except Exception as e:
                        ui.notify(f'Error selecting: {str(e)}', color='negative')
                
                self.table.on('cellClicked', on_row_click)

            # Bottom: Details
            with ModernCard(glass=True).classes('w-full p-6'):
                ui.label('Record Details').classes('text-lg font-black mb-6 text-white')
                with ui.row().classes('w-full gap-6 items-center'):
                    self.input_refs['aux_code'] = ui.select([None], label='Auxiliary Code').classes('w-48 glass-input text-white').props('dark rounded outlined')
                    self.input_refs['number'] = ui.input('Auxiliary Number').classes('w-48 glass-input text-white').props('dark rounded outlined')
                    self.input_refs['status'] = ui.select({1: 'Active', 0: 'Inactive'}, label='Status').classes('w-32 glass-input text-white').props('dark rounded outlined')
                    self.input_refs['id'] = ui.input('ID (Internal)').classes('w-32 glass-input text-white').props('dark rounded outlined readonly')

                with ui.row().classes('w-full gap-6 mt-4'):
                    self.input_refs['account_name'] = ui.input('Account Name').classes('flex-1 glass-input text-white').props('dark rounded outlined')

        ui.timer(0.1, self.refresh_table, once=True)

    def filter_rows(self, search_text):
        if not search_text:
            self.table.options['rowData'] = self.row_data
        else:
            search_text = search_text.lower()
            filtered = [row for row in self.row_data if any(search_text in str(v).lower() for v in row.values())]
            self.table.options['rowData'] = filtered
        self.table.update()