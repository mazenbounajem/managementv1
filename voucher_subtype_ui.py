from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from modern_design_system import ModernDesignSystem as MDS

def voucher_subtype_content(standalone=False):
    """Content method for voucher subtypes that can be used in tabs"""
    if standalone:
        with ModernPageLayout("Voucher Subtype Management", standalone=standalone):
            VoucherSubtypeUI(standalone=False)
    else:
        VoucherSubtypeUI(standalone=False)

@ui.page('/voucher_subtype')
def voucher_subtype_page_route():
    voucher_subtype_content(standalone=True)

class VoucherSubtypeUI:
    def __init__(self, standalone=True):
        self.standalone = standalone
        self.input_refs = {}
        self.initial_values = {}
        self.row_data = []
        self.table = None
        self.search_input = None
        self.create_ui()

    def clear_input_fields(self):
        self.input_refs['code'].value = ''
        self.input_refs['name'].value = ''
        self.input_refs['sequence'].value = 0
        self.input_refs['id'].value = ''
        if self.table:
            self.table.classes(add='dimmed')
            self.table.run_method('deselectAll')
        ui.notify('Ready for new entry', color='info')

    def _load_last_row(self):
        """Load the first row (last record) into form fields and undim table"""
        if not self.row_data:
            return
        row = self.row_data[0]
        self.input_refs['id'].value = str(row['id'])
        self.input_refs['code'].value = row['code'] or ''
        self.input_refs['name'].value = row['name'] or ''
        self.input_refs['sequence'].value = row['sequence'] or 0
        self.initial_values = {
            'code': row['code'] or '',
            'name': row['name'] or '',
            'sequence': row['sequence'] or 0,
            'id': str(row['id'])
        }
        if self.table:
            self.table.classes(remove='dimmed')

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
            # Check if subtype is used in journal vouchers
            data = []
            connection.contogetrows("SELECT COUNT(*) FROM journal_voucher_header WHERE subtype_code=?", data, (self.input_refs['code'].value,))
            if data and data[0][0] > 0:
                ui.notify('Cannot delete: Subtype is used in journal vouchers', color='warning')
                return
                
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
                    'created_at': str(row[4]) if row[4] else ''
                })

            if self.table:
                self.table.options['rowData'] = new_row_data
                self.table.update()

            self.row_data = new_row_data
            # Load last entry into form and undim
            self._load_last_row()
        except Exception as e:
            ui.notify(f'Error refreshing table: {str(e)}', color='negative')

    def create_ui(self):
        # Wrap content in ModernPageLayout only if standalone, otherwise just render the content
        if self.standalone:
            layout_container = ModernPageLayout("Voucher Subtype Management", standalone=True)
            layout_container.__enter__()
        
        try:
            with ui.row().classes('w-full gap-6 items-start p-4 animate-fade-in'):
                # Left Column: Form
                with ui.column().classes('w-1/3 gap-6'):
                    with ModernCard(glass=True).classes('w-full p-6'):
                        ui.label('Subtype Details').classes('text-lg font-black mb-6 text-white')
                        with ui.column().classes('w-full gap-4'):
                            self.input_refs['code'] = ui.input('Code').classes('w-full glass-input text-white').props('dark rounded outlined')
                            self.input_refs['name'] = ui.input('Subtype Name').classes('w-full glass-input text-white').props('dark rounded outlined')
                            self.input_refs['sequence'] = ui.number('Sequence', value=0).classes('w-full glass-input text-white').props('dark rounded outlined')
                            self.input_refs['id'] = ui.input('ID (Internal)').classes('w-full glass-input text-white').props('dark rounded outlined readonly')

                # Middle Column: List
                with ui.column().classes('flex-1 gap-6'):
                    with ModernCard(glass=True).classes('w-full p-6'):
                        with ui.row().classes('w-full justify-between items-center mb-4'):
                            ui.label('Voucher Subtypes').classes('text-xl font-black text-white ml-2')
                            self.search_input = ui.input(placeholder='Search subtypes...').classes('w-64 glass-input text-white text-sm').props('dark rounded outlined dense')
                            self.search_input.on('input', lambda e: self.filter_rows(e.value))

                        column_defs = [
                            {'headerName': 'ID', 'field': 'id', 'width': 80},
                            {'headerName': 'Code', 'field': 'code', 'width': 120},
                            {'headerName': 'Name', 'field': 'name', 'width': 220, 'flex': 1},
                            {'headerName': 'Sequence', 'field': 'sequence', 'width': 100},
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
                                    self.input_refs['code'].value = selected_row['code'] or ''
                                    self.input_refs['name'].value = selected_row['name'] or ''
                                    self.input_refs['sequence'].value = selected_row['sequence'] or 0
                                    self.initial_values = {
                                        'code': selected_row['code'] or '',
                                        'name': selected_row['name'] or '',
                                        'sequence': selected_row['sequence'] or 0,
                                        'id': str(selected_row['id'])
                                    }
                                    if self.table:
                                        self.table.classes(remove='dimmed')
                            except Exception as e:
                                ui.notify(f'Error selecting row: {str(e)}', color='negative')

                        self.table.on('cellClicked', on_row_click)

                # Right Column: Action Bar
                with ui.column().classes('w-80px items-center'):
                    from modern_ui_components import ModernActionBar
                    ModernActionBar(
                        on_new=self.clear_input_fields,
                        on_save=self.save_voucher_subtype,
                        on_undo=self.undo_changes,
                        on_delete=self.delete_voucher_subtype,
                        on_refresh=self.refresh_table,
                        on_chatgpt=lambda: ui.run_javascript('window.open("https://chatgpt.com", "_blank");'),
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