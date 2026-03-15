from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from modern_design_system import ModernDesignSystem as MDS

@ui.page('/voucher_subtype')
def voucher_subtype_page_route():
    with ModernPageLayout("Voucher Subtype Management"):
        VoucherSubtypeUI()

class VoucherSubtypeUI:
    def __init__(self):
        self.input_refs = {}
        self.initial_values = {}
        self.row_data = []
        self.table = None
        self.create_ui()

    def clear_input_fields(self):
        self.input_refs['code'].value = ''
        self.input_refs['name'].value = ''
        self.input_refs['sequence'].value = 0
        self.input_refs['id'].value = ''
        if self.table:
            self.table.classes('dimmed')
        ui.notify('Ready for new entry', color='info')

    def save_voucher_subtype(self):
        code = self.input_refs['code'].value.upper()
        name = self.input_refs['name'].value
        sequence = int(self.input_refs['sequence'].value or 0)
        id_value = self.input_refs['id'].value

        if not code or not name:
            ui.notify('Code and Name are required', color='warning')
            return

        try:
            if id_value:
                sql = "UPDATE subtype SET code=?, name=?, sequence=?, updated_at=GETDATE() WHERE id=?"
                values = (code, name, sequence, id_value)
            else:
                sql = "INSERT INTO subtype (code, name, sequence, created_at, updated_at) VALUES (?, ?, ?, GETDATE(), GETDATE())"
                values = (code, name, sequence)

            connection.insertingtodatabase(sql, values)
            ui.notify('Saved successfully', color='positive')
            if self.table:
                self.table.classes(remove='dimmed')
            self.refresh_table()
        except Exception as e:
            ui.notify(f'Error saving: {str(e)}', color='negative')

    def undo_changes(self):
        fields = ['code', 'name', 'sequence', 'id']
        for field in fields:
            if field in self.initial_values:
                self.input_refs[field].value = self.initial_values[field]
        if self.table:
            self.table.classes(remove='dimmed')
        ui.notify('Changes reverted', color='info')

    def delete_voucher_subtype(self):
        id_value = self.input_refs['id'].value
        if not id_value:
            ui.notify('Select a record to delete', color='warning')
            return

        try:
            sql = "DELETE FROM subtype WHERE id=?"
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
            connection.contogetrows("SELECT id, code, name, sequence, created_at FROM subtype ORDER BY sequence", data)

            new_row_data = []
            for row in data:
                new_row_data.append({
                    'id': row[0],
                    'code': row[1],
                    'name': row[2],
                    'sequence': row[3],
                    'created_at': str(row[4])
                })

            if self.table:
                self.table.options['rowData'] = new_row_data
                self.table.update()
                self.table.classes(remove='dimmed')

            self.row_data = new_row_data
            self.clear_input_fields()
        except Exception as e:
            ui.notify(f'Error refreshing table: {str(e)}', color='negative')

    def create_ui(self):
        # Action Bar
        with ui.row().classes('w-full justify-between items-center mb-6 p-4 rounded-2xl bg-white/5 glass border border-white/10'):
            with ui.row().classes('gap-3'):
                ModernButton('New Subtype', icon='add', on_click=self.clear_input_fields, variant='primary')
                ModernButton('Save', icon='save', on_click=self.save_voucher_subtype, variant='success')
                ModernButton('Undo', icon='undo', on_click=self.undo_changes, variant='secondary')
                ModernButton('Delete', icon='delete', on_click=self.delete_voucher_subtype, variant='error')
            
            ModernButton('Refresh', icon='refresh', on_click=self.refresh_table, variant='outline').classes('text-white border-white/20')

        with ui.column().classes('w-full gap-6'):
            # Top: List
            with ModernCard(glass=True).classes('w-full p-6'):
                with ui.row().classes('w-full justify-between items-center mb-4'):
                    ui.label('Voucher Subtypes').classes('text-xl font-black text-white')
                    self.search_input = ui.input(placeholder='Search subtypes...').classes('w-64 glass-input text-white text-sm').props('dark rounded outlined dense')
                    self.search_input.on('input', lambda e: self.filter_rows(e.value))

                column_defs = [
                    {'headerName': 'ID', 'field': 'id', 'width': 80},
                    {'headerName': 'Code', 'field': 'code', 'width': 120},
                    {'headerName': 'Name', 'field': 'name', 'width': 220},
                    {'headerName': 'Sequence', 'field': 'sequence', 'width': 100},
                    {'headerName': 'Created At', 'field': 'created_at', 'width': 180}
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
                            self.input_refs['code'].value = selected_row['code']
                            self.input_refs['name'].value = selected_row['name']
                            self.input_refs['sequence'].value = selected_row['sequence']
                            
                            self.initial_values = {
                                'code': selected_row['code'],
                                'name': selected_row['name'],
                                'sequence': selected_row['sequence'],
                                'id': str(selected_row['id'])
                            }
                            ui.notify(f'Selected: {selected_row["name"]}', color='info')
                    except Exception as e:
                        ui.notify(f'Error selecting row: {str(e)}', color='negative')
                
                self.table.on('cellClicked', on_row_click)

            # Bottom: Details
            with ModernCard(glass=True).classes('w-full p-6'):
                ui.label('Subtype Details').classes('text-lg font-black mb-6 text-white')
                with ui.row().classes('w-full gap-6 items-center'):
                    self.input_refs['code'] = ui.input('Code').classes('w-48 glass-input text-white').props('dark rounded outlined')
                    self.input_refs['sequence'] = ui.number('Sequence', value=0).classes('w-32 glass-input text-white').props('dark rounded outlined')
                    self.input_refs['id'] = ui.input('ID (Internal)').classes('w-32 glass-input text-white').props('dark rounded outlined readonly')

                with ui.row().classes('w-full gap-6 mt-4'):
                    self.input_refs['name'] = ui.input('Subtype Name').classes('flex-1 glass-input text-white').props('dark rounded outlined')

        ui.timer(0.1, self.refresh_table, once=True)

    def filter_rows(self, search_text):
        if not search_text:
            self.table.options['rowData'] = self.row_data
        else:
            search_text = search_text.lower()
            filtered = [row for row in self.row_data if any(search_text in str(v).lower() for v in row.values())]
            self.table.options['rowData'] = filtered
        self.table.update()
